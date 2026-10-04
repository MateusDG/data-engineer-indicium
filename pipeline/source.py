"""Read the legacy snapshot safely, preserving source values and provenance."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
import stat
import tempfile
import zipfile
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONTRACT = json.loads((PROJECT_ROOT / "config/data_contract.json").read_text())
TABLES = CONTRACT["tables"]
MAX_TOTAL_BYTES = 128 * 1024 * 1024


def run_key(run_id: str) -> str:
    return hashlib.sha256(run_id.encode()).hexdigest()[:24]


def content_digest(rows) -> str:
    """Order-independent digest that preserves every cell, duplicate and null."""
    digests = [hashlib.sha256(json.dumps(list(row), ensure_ascii=False,
               separators=(",", ":")).encode()).digest() for row in rows]
    return hashlib.sha256(b"".join(sorted(digests))).hexdigest()


def inspect_csv(data: bytes, table: str) -> tuple[dict, list[list[str]]]:
    spec = TABLES[table]
    reader = csv.reader(io.StringIO(data.decode("utf-8-sig"), newline=""), strict=True)
    columns = next(reader, None)
    if columns != spec["columns"]:
        raise ValueError(f"Schema mismatch: {table}; expected {spec['columns']}")
    rows, keys = [], set()
    indexes = {name: index for index, name in enumerate(columns)}
    for line, row in enumerate(reader, start=2):
        if len(row) != len(columns):
            raise ValueError(f"Invalid row width: {table}, line {line}")
        key = tuple(row[indexes[k]] for k in spec["keys"])
        if any(not value.strip() for value in key) or key in keys:
            raise ValueError(f"Missing or duplicate primary key: {table}, line {line}")
        keys.add(key)
        for column in spec.get("dates", []):
            value = row[indexes[column]]
            try:
                datetime.fromisoformat(value.replace(" UTC", "+00:00"))
            except ValueError as exc:
                raise ValueError(f"Invalid date: {table}.{column}, line {line}") from exc
        for column in spec.get("decimals", []) + spec.get("integers", []):
            try:
                value = Decimal(row[indexes[column]])
                if not value.is_finite() or (column in spec.get("integers", []) and value != value.to_integral()):
                    raise InvalidOperation
            except InvalidOperation as exc:
                raise ValueError(f"Invalid number: {table}.{column}, line {line}") from exc
        rows.append(row)
    if not rows:
        raise ValueError(f"Empty source table: {table}")
    return {"columns": columns, "rows": len(rows), "sha256": hashlib.sha256(data).hexdigest(),
            "content_sha256": content_digest(rows)}, rows


def inspect_zip(path: Path) -> tuple[dict, dict[str, bytes]]:
    payloads, summaries, all_rows = {}, {}, {}
    with zipfile.ZipFile(path) as archive:
        if sum(item.file_size for item in archive.infolist()) > MAX_TOTAL_BYTES:
            raise ValueError("ZIP exceeds the 128 MiB uncompressed size limit")
        for item in archive.infolist():
            name = PurePosixPath(item.filename.replace("\\", "/"))
            if name.is_absolute() or ".." in name.parts or ":" in item.filename:
                raise ValueError("Unsafe ZIP member path")
            if stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError("ZIP symbolic links are not accepted")
            if item.is_dir():
                continue
            if name.suffix.lower() != ".csv":
                raise ValueError(f"Unexpected ZIP member: {name.name}")
            table = name.stem
            if table not in TABLES or table in payloads:
                raise ValueError(f"Unexpected or duplicate source table: {table}")
            payloads[table] = archive.read(item)
            summaries[table], all_rows[table] = inspect_csv(payloads[table], table)
    if set(payloads) != set(TABLES):
        raise ValueError(f"Missing source tables: {sorted(set(TABLES) - set(payloads))}")
    relationships = []
    for source, column, target, key in CONTRACT["relationships"]:
        idx = TABLES[source]["columns"].index(column)
        target_idx = TABLES[target]["columns"].index(key)
        target_keys = {row[target_idx] for row in all_rows[target]}
        orphan_count = sum(row[idx] not in target_keys for row in all_rows[source])
        relationships.append({"source": source, "column": column, "target": target,
                              "key": key, "source_orphan_rows": orphan_count})
    return {"contract_version": CONTRACT["version"], "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "tables": summaries, "relationships": relationships}, payloads


def prepare_source(path: Path, work_root: Path, run_id: str) -> dict:
    """Freeze one immutable source per run. A retry reuses the original bytes."""
    destination = work_root / run_key(run_id)
    manifest_path = destination / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest["run_id"] != run_id:
            raise ValueError("Run identifier collision")
        for table, info in manifest["tables"].items():
            if hashlib.sha256((destination / f"{table}.csv").read_bytes()).hexdigest() != info["sha256"]:
                raise ValueError(f"Frozen source changed: {table}")
        return manifest
    work_root.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".prepare-", dir=work_root))
    try:
        # Copy first: validation and hashing must use the same immutable snapshot.
        frozen_zip = temporary / "source.zip"
        shutil.copyfile(path, frozen_zip)
        manifest, payloads = inspect_zip(frozen_zip)
        manifest.update(run_id=run_id, staging_schema=f"stg_{run_key(run_id)}")
        for table, data in payloads.items():
            (temporary / f"{table}.csv").write_bytes(data)
        (temporary / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        for child in temporary.iterdir():
            child.chmod(0o440)
        temporary.chmod(0o750)
        os.rename(temporary, destination)
        return manifest
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def read_manifest(work_root: Path, run_id: str) -> dict:
    manifest = json.loads((work_root / run_key(run_id) / "manifest.json").read_text())
    if manifest["run_id"] != run_id:
        raise ValueError("Manifest belongs to another run")
    return manifest

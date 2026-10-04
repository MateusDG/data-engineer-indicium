"""Commands executed by KubernetesPodOperator; logs contain metrics, not records."""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from psycopg import sql

from pipeline.database import connect, publish, record_failure, start_run, validate_stage
from pipeline.source import PROJECT_ROOT, TABLES, prepare_source, read_manifest, run_key

LOG = logging.getLogger("banvic")


def load_table(work_root: Path, run_id: str, table: str):
    manifest = read_manifest(work_root, run_id)
    frozen = work_root / run_key(run_id)
    if os.environ.get("SIMULATE_FAILURE_ALWAYS") == table:
        raise RuntimeError(f"Controlled permanent failure before loading {table}")
    if os.environ.get("SIMULATE_FAILURE_ONCE") == table:
        marker = work_root / f".fault-{run_key(run_id)}-{table}"
        try:
            with marker.open("x"):
                pass
        except FileExistsError:
            pass
        else:
            raise RuntimeError(f"Controlled transient failure before loading {table}")
    with connect() as conn:
        conn.execute(sql.SQL("DROP TABLE IF EXISTS {}.{}").format(sql.Identifier(manifest["staging_schema"]), sql.Identifier(table)))
    # Each pod gets isolated Meltano state/log files. Installed plugin venvs are read-only shared image content.
    with tempfile.TemporaryDirectory(prefix="banvic-meltano-") as temporary:
        project = Path(temporary)
        shutil.copy(PROJECT_ROOT / "meltano/meltano.yml", project / "meltano.yml")
        plugin_dir = project / ".meltano"
        plugin_dir.mkdir()
        (plugin_dir / "extractors").symlink_to(PROJECT_ROOT / "meltano/.meltano/extractors", target_is_directory=True)
        (plugin_dir / "loaders").symlink_to(PROJECT_ROOT / "meltano/.meltano/loaders", target_is_directory=True)
        env = os.environ.copy()
        env.update(TAP_CSV_FILES=json.dumps([{"entity": table, "path": str(frozen / f"{table}.csv"),
                   "keys": TABLES[table]["keys"], "encoding": "utf-8-sig", "strict": True}]),
                   TARGET_POSTGRES_HOST=env["PGHOST"], TARGET_POSTGRES_PORT=env.get("PGPORT", "5432"),
                   TARGET_POSTGRES_DATABASE=env["PGDATABASE"], TARGET_POSTGRES_USER=env["PGUSER"],
                   TARGET_POSTGRES_PASSWORD=env["PGPASSWORD"], TARGET_POSTGRES_DEFAULT_TARGET_SCHEMA=manifest["staging_schema"])
        subprocess.run(["meltano", "--log-level=info", "run", "--full-refresh", "--no-state-update",
                        "tap-csv", "target-postgres"], cwd=project, env=env, check=True, timeout=900)
    LOG.info(json.dumps({"event": "table_loaded", "table": table, "expected_rows": manifest["tables"][table]["rows"]}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "load", "validate", "publish", "failure"])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--table", choices=list(TABLES))
    parser.add_argument("--source", default="/data/input/banvic_data.zip")
    parser.add_argument("--work-root", type=Path, default=Path("/data/work"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        if args.command == "prepare":
            manifest = prepare_source(Path(args.source), args.work_root, args.run_id)
            with connect() as conn:
                start_run(conn, manifest)
            result = {"status": "prepared", "source_sha256": manifest["source_sha256"],
                      "rows": {table: info["rows"] for table, info in manifest["tables"].items()}}
        elif args.command == "load":
            if not args.table:
                parser.error("load requires --table")
            load_table(args.work_root, args.run_id, args.table)
            result = {"status": "loaded", "table": args.table}
        elif args.command == "failure":
            with connect() as conn:
                record_failure(conn, args.run_id)
            result = {"status": "failed", "run_id": args.run_id}
        else:
            manifest = read_manifest(args.work_root, args.run_id)
            with connect() as conn:
                result = validate_stage(conn, manifest) if args.command == "validate" else publish(conn, manifest)
            if args.command == "validate":
                report_path = args.work_root / run_key(args.run_id) / "validation.json"
                report_path.write_text(json.dumps(result, indent=2))
        LOG.info(json.dumps(result))
    except Exception:
        LOG.exception("Pipeline command failed: command=%s run_id=%s", args.command, args.run_id)
        raise


if __name__ == "__main__":
    main()

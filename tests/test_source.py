"""Meaningful safety and integrity tests for the untrusted legacy ZIP."""
import csv
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from pipeline.source import TABLES, content_digest, inspect_csv, inspect_zip, prepare_source, run_key


def synthetic_payloads():
    payloads = {}
    for table, spec in TABLES.items():
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer)
        writer.writerow(spec["columns"])
        row = ["1" for _ in spec["columns"]]
        for name in spec.get("dates", []):
            row[spec["columns"].index(name)] = "2022-12-30 00:00:00 UTC"
        writer.writerow(row)
        payloads[table] = buffer.getvalue().encode()
    return payloads


def write_zip(path, payloads, extra=None):
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in payloads.items():
            archive.writestr(f"{name}.csv", data)
        if extra:
            archive.writestr(*extra)


class SourceTests(unittest.TestCase):
    def test_digest_preserves_cells_and_duplicate_multiplicity(self):
        self.assertEqual(content_digest([["01", "ç"], ["2", ""]]), content_digest([["2", ""], ["01", "ç"]]))
        self.assertNotEqual(content_digest([["1"]]), content_digest([["1"], ["1"]]))
        self.assertNotEqual(content_digest([[""]]), content_digest([[None]]))

    def test_missing_table_blocks_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.zip"
            payloads = synthetic_payloads()
            del payloads["clientes"]
            write_zip(path, payloads)
            with self.assertRaisesRegex(ValueError, "Missing source"):
                inspect_zip(path)

    def test_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.zip"
            write_zip(path, synthetic_payloads(), ("../escape.csv", b"x\n1\n"))
            with self.assertRaisesRegex(ValueError, "Unsafe ZIP"):
                inspect_zip(path)
            self.assertFalse((Path(directory) / "escape.csv").exists())

    def test_duplicate_keys_and_changed_schema_are_rejected(self):
        payload = synthetic_payloads()["agencias"]
        duplicate = payload + payload.splitlines(keepends=True)[1]
        with self.assertRaisesRegex(ValueError, "duplicate primary"):
            inspect_csv(duplicate, "agencias")
        with self.assertRaisesRegex(ValueError, "Schema mismatch"):
            inspect_csv(payload.replace(b"cidade", b"municipio"), "agencias")

    def test_invalid_width_and_date_are_rejected(self):
        payload = synthetic_payloads()["agencias"]
        with self.assertRaisesRegex(ValueError, "Invalid row width"):
            inspect_csv(payload + b"1,2\n", "agencias")
        with self.assertRaisesRegex(ValueError, "Invalid date"):
            inspect_csv(payload.replace(b"2022-12-30", b"2022-99-99"), "agencias")

    def test_retry_freezes_original_source_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, work = root / "source.zip", root / "work"
            write_zip(path, synthetic_payloads())
            original = prepare_source(path, work, "run-1")
            path.write_bytes(b"replaced source")
            self.assertEqual(original, prepare_source(path, work, "run-1"))
            frozen = work / run_key("run-1") / "agencias.csv"
            frozen.chmod(0o640)
            frozen.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "Frozen source changed"):
                prepare_source(path, work, "run-1")

    def test_official_zip_contract(self):
        root = Path(__file__).resolve().parent.parent
        path = next((root / name for name in ("banvic_data.zip", "Dados Banvic.zip") if (root / name).exists()), None)
        if path is None:
            self.skipTest("Official dataset is intentionally excluded from Git")
        manifest, _ = inspect_zip(path)
        self.assertEqual(manifest["tables"]["clientes"]["rows"], 998)
        self.assertEqual(manifest["tables"]["transacoes"]["rows"], 71999)
        self.assertEqual(sum(item["source_orphan_rows"] for item in manifest["relationships"]), 5)


if __name__ == "__main__":
    unittest.main()

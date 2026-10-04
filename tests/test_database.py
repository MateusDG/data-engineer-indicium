"""Integration checks run against the isolated local BanVic warehouse."""
import json
import os
import unittest

from psycopg import sql
from psycopg.errors import CheckViolation

from pipeline.database import connect, publish, validate_stage
from pipeline.source import TABLES, content_digest


@unittest.skipUnless(os.environ.get("BANVIC_TEST_DATABASE") == "1", "Requires a deployed POC")
class DatabaseTests(unittest.TestCase):
    def setUp(self):
        with connect() as conn:
            current = conn.execute("SELECT r.manifest FROM audit.ingestion_runs r JOIN audit.current_snapshot s USING(run_id)").fetchone()
            self.assertIsNotNone(current, "Run a successful ingestion first")
            self.manifest = current[0]
            self.original_run = self.manifest["run_id"]
            self.fingerprints = self.raw_fingerprints(conn)

    def raw_fingerprints(self, conn):
        return {table: content_digest(conn.execute(sql.SQL("SELECT {} FROM raw.{}").format(
            sql.SQL(",").join(map(sql.Identifier, spec["columns"])), sql.Identifier(table))).fetchall())
            for table, spec in TABLES.items()}

    def test_already_published_run_is_a_noop(self):
        with connect() as conn:
            self.assertEqual(publish(conn, self.manifest)["status"], "already_published")
            self.assertEqual(self.raw_fingerprints(conn), self.fingerprints)

    def test_published_raw_matches_frozen_source(self):
        self.assertEqual(self.fingerprints, {
            table: info["content_sha256"] for table, info in self.manifest["tables"].items()
        })

    def test_changed_stage_cannot_pass_gate(self):
        with connect() as conn:
            conn.execute("SAVEPOINT test_scope")
            conn.execute(sql.SQL("UPDATE {}.agencias SET nome='INTEGRITY_TEST' WHERE cod_agencia=(SELECT min(cod_agencia) FROM {}.agencias)").format(
                sql.Identifier(self.manifest["staging_schema"]), sql.Identifier(self.manifest["staging_schema"])))
            with self.assertRaisesRegex(ValueError, "reconciliation failed"):
                validate_stage(conn, self.manifest)
            conn.execute("ROLLBACK TO SAVEPOINT test_scope")
            self.assertEqual(self.raw_fingerprints(conn), self.fingerprints)

    def test_publication_error_rolls_back_all_tables_and_marker(self):
        candidate = dict(self.manifest, run_id="integration_atomic_rollback")
        with connect() as conn:
            conn.execute("SAVEPOINT test_scope")
            conn.execute("INSERT INTO audit.ingestion_runs(run_id,status,source_sha256,staging_schema,manifest) VALUES (%s,'validated',%s,%s,%s::jsonb)",
                (candidate["run_id"], candidate["source_sha256"], candidate["staging_schema"], json.dumps(candidate)))
            # A late-table check forces failure after earlier DELETE/INSERT operations.
            conn.execute("ALTER TABLE raw.transacoes ADD CONSTRAINT integration_block CHECK (false) NOT VALID")
            with self.assertRaises(CheckViolation):
                publish(conn, candidate)
            conn.execute("ROLLBACK TO SAVEPOINT test_scope")
            self.assertEqual(conn.execute("SELECT run_id FROM audit.current_snapshot").fetchone()[0], self.original_run)
            self.assertEqual(self.raw_fingerprints(conn), self.fingerprints)
            self.assertIsNone(conn.execute("SELECT run_id FROM audit.ingestion_runs WHERE run_id=%s", (candidate["run_id"],)).fetchone())

    def test_source_orphans_are_reported_without_data_loss(self):
        with connect() as conn:
            report = validate_stage(conn, self.manifest)
            self.assertEqual(sum(item["loaded_orphan_rows"] for item in report["relationships"]), 5)
            self.assertEqual(report["tables"]["transacoes"]["rows"], 71999)


if __name__ == "__main__":
    unittest.main()

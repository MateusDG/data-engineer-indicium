"""Database operations. Credentials enter through Kubernetes Secret references."""
from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg
from psycopg import sql

from pipeline.source import TABLES, content_digest


def connect():
    return psycopg.connect(host=os.environ.get("PGHOST", "postgres"),
        port=int(os.environ.get("PGPORT", "5432")), dbname=os.environ.get("PGDATABASE", "banvic_dw"),
        user=os.environ["PGUSER"], password=os.environ["PGPASSWORD"], connect_timeout=10,
        application_name="banvic_pipeline")


def bootstrap(conn):
    conn.execute((Path(__file__).resolve().parent.parent / "sql/bootstrap.sql").read_text())
    conn.execute((Path(__file__).resolve().parent.parent / "sql/commercial.sql").read_text())


def start_run(conn, manifest):
    bootstrap(conn)
    conn.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(manifest["staging_schema"])))
    conn.execute("""INSERT INTO audit.ingestion_runs (run_id, source_sha256, staging_schema, status, manifest)
        VALUES (%s,%s,%s,'running',%s::jsonb)
        ON CONFLICT (run_id) DO UPDATE SET status=CASE WHEN audit.ingestion_runs.status='published'
        THEN 'published' ELSE 'running' END, error=NULL""",
        (manifest["run_id"], manifest["source_sha256"], manifest["staging_schema"], json.dumps(manifest)))


def validate_stage(conn, manifest):
    """Source-to-target full reconciliation, including values and orphan counts."""
    report = {"run_id": manifest["run_id"], "source_sha256": manifest["source_sha256"], "tables": {}, "relationships": []}
    schema = manifest["staging_schema"]
    for table, spec in TABLES.items():
        columns = sql.SQL(",").join(map(sql.Identifier, spec["columns"]))
        rows = conn.execute(sql.SQL("SELECT {} FROM {}.{}").format(columns, sql.Identifier(schema), sql.Identifier(table))).fetchall()
        expected = manifest["tables"][table]
        actual = content_digest(rows)
        if len(rows) != expected["rows"] or actual != expected["content_sha256"]:
            raise ValueError(f"Source-to-target reconciliation failed: {table}")
        keys = [tuple(row[spec["columns"].index(k)] for k in spec["keys"]) for row in rows]
        if any(any(value is None or value == "" for value in key) for key in keys) or len(set(keys)) != len(keys):
            raise ValueError(f"Invalid staging primary keys: {table}")
        report["tables"][table] = {"rows": len(rows), "content_sha256": actual, "status": "passed"}
    for relationship in manifest["relationships"]:
        source, column, target, key = (relationship[k] for k in ("source", "column", "target", "key"))
        count = conn.execute(sql.SQL("SELECT count(*) FROM {}.{} s LEFT JOIN {}.{} t ON s.{}=t.{} WHERE t.{} IS NULL").format(
            sql.Identifier(schema), sql.Identifier(source), sql.Identifier(schema), sql.Identifier(target),
            sql.Identifier(column), sql.Identifier(key), sql.Identifier(key))).fetchone()[0]
        if count != relationship["source_orphan_rows"]:
            raise ValueError(f"New referential integrity failures: {source}.{column}")
        report["relationships"].append({**relationship, "loaded_orphan_rows": count, "severity": "warning" if count else "passed"})
    conn.execute("UPDATE audit.ingestion_runs SET status='validated', validation=%s::jsonb WHERE run_id=%s AND status<>'published'",
                 (json.dumps(report), manifest["run_id"]))
    for table, info in report["tables"].items():
        conn.execute("""INSERT INTO audit.table_results (run_id, table_name, row_count, content_sha256)
            VALUES (%s,%s,%s,%s) ON CONFLICT(run_id,table_name) DO UPDATE
            SET row_count=excluded.row_count, content_sha256=excluded.content_sha256""",
            (manifest["run_id"], table, info["rows"], info["content_sha256"]))
    return report


def publish(conn, manifest):
    """All seven tables and the publication marker commit together, or roll back."""
    conn.execute("SELECT pg_advisory_xact_lock(78123109)")
    state = conn.execute("SELECT status FROM audit.ingestion_runs WHERE run_id=%s FOR UPDATE", (manifest["run_id"],)).fetchone()
    if state and state[0] == "published":
        return {"status": "already_published", "run_id": manifest["run_id"]}
    if not state or state[0] != "validated":
        raise ValueError("Publication requires a validated run")
    # Validate again inside this transaction so a changed staging table cannot bypass the gate.
    validate_stage(conn, manifest)
    for table, spec in TABLES.items():
        columns = sql.SQL(",").join(map(sql.Identifier, spec["columns"]))
        conn.execute(sql.SQL("DELETE FROM raw.{}").format(sql.Identifier(table)))
        conn.execute(sql.SQL("INSERT INTO raw.{} ({}) SELECT {} FROM {}.{}").format(
            sql.Identifier(table), columns, columns, sql.Identifier(manifest["staging_schema"]), sql.Identifier(table)))
    conn.execute("""INSERT INTO audit.current_snapshot (singleton, run_id, source_sha256, published_at)
        VALUES (true,%s,%s,clock_timestamp()) ON CONFLICT(singleton) DO UPDATE
        SET run_id=excluded.run_id, source_sha256=excluded.source_sha256, published_at=excluded.published_at""",
        (manifest["run_id"], manifest["source_sha256"]))
    conn.execute("UPDATE audit.ingestion_runs SET status='published', finished_at=clock_timestamp() WHERE run_id=%s", (manifest["run_id"],))
    return {"status": "published", "run_id": manifest["run_id"], "rows": sum(i["rows"] for i in manifest["tables"].values())}


def record_failure(conn, run_id):
    bootstrap(conn)
    conn.execute("""INSERT INTO audit.ingestion_runs(run_id,status,error,finished_at)
        VALUES (%s,'failed','Airflow task failure; inspect task logs',clock_timestamp())
        ON CONFLICT(run_id) DO UPDATE SET status='failed', error=excluded.error,
        finished_at=excluded.finished_at WHERE audit.ingestion_runs.status<>'published'""", (run_id,))

"""Export public aggregate evidence without credentials or customer records."""
import argparse
import json
import os
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--home", type=Path, default=Path.home() / "banvic-local")
args = parser.parse_args()
root = Path(__file__).resolve().parent.parent
output = root / "evidence"
output.mkdir(exist_ok=True)
os.environ["KUBECONFIG"] = str(args.home / "kubeconfig")

query = """
SELECT json_build_object(
 'collected_at',clock_timestamp(),
 'table_counts',json_build_object('agencias',(SELECT count(*) FROM raw.agencias),
 'clientes',(SELECT count(*) FROM raw.clientes),'colaborador_agencia',(SELECT count(*) FROM raw.colaborador_agencia),
 'colaboradores',(SELECT count(*) FROM raw.colaboradores),'contas',(SELECT count(*) FROM raw.contas),
 'propostas_credito',(SELECT count(*) FROM raw.propostas_credito),'transacoes',(SELECT count(*) FROM raw.transacoes)),
 'runs',(SELECT json_agg(json_build_object('run_id',run_id,'status',status,'source_sha256',source_sha256,
 'started_at',started_at,'finished_at',finished_at) ORDER BY started_at) FROM audit.ingestion_runs),
 'current_snapshot',(SELECT row_to_json(s) FROM audit.current_snapshot s),
 'table_results',(SELECT json_agg(t ORDER BY run_id,table_name) FROM audit.table_results t),
 'reprocessing_differences',(SELECT count(*) FROM audit.table_results a JOIN audit.table_results b USING(table_name)
 WHERE a.run_id='certification_initial' AND b.run_id='certification_retry'
 AND (a.row_count<>b.row_count OR a.content_sha256<>b.content_sha256)),
 'source_orphans',json_build_object('contas_cliente',(SELECT count(*) FROM raw.contas c LEFT JOIN raw.clientes l USING(cod_cliente) WHERE l.cod_cliente IS NULL),
 'propostas_cliente',(SELECT count(*) FROM raw.propostas_credito p LEFT JOIN raw.clientes l USING(cod_cliente) WHERE l.cod_cliente IS NULL)),
 'analyst_permissions',json_build_object('read_raw',has_table_privilege('banvic_analyst','raw.transacoes','SELECT'),
 'write_raw',has_table_privilege('banvic_analyst','raw.transacoes','INSERT'),
 'create_raw',has_schema_privilege('banvic_analyst','raw','CREATE')));
"""
result = subprocess.run(["kubectl", "-n", "banvic", "exec", "-i", "postgres-0", "--", "sh", "-c",
 'PGPASSWORD="$ETL_PASSWORD" psql -h 127.0.0.1 -U banvic_etl -d banvic_dw -A -t -v ON_ERROR_STOP=1'],
 input=query, text=True, capture_output=True, check=True)
evidence = json.loads(result.stdout)
assert sum(evidence["table_counts"].values()) == 76206
assert evidence["reprocessing_differences"] == 0
assert evidence["analyst_permissions"] == {"read_raw": True, "write_raw": False, "create_raw": False}
(output / "warehouse.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")
pods = subprocess.run(["kubectl", "-n", "banvic", "get", "pods", "-o", "json"],
                      capture_output=True, text=True, check=True)
items = json.loads(pods.stdout)["items"]
(output / "pods.json").write_text(json.dumps([{"name": p["metadata"]["name"],
 "phase":p["status"]["phase"], "containers":[{"name":c["name"],"ready":c["ready"],
 "restarts":c["restartCount"]} for c in p["status"].get("containerStatuses",[])]} for p in items], indent=2) + "\n")
for run_id in ["certification_initial", "certification_retry", "certification_failure", "certification_demo", "certification_video"]:
    result = subprocess.run(["python3", str(root / "scripts/airflow_api.py"), "tasks", "--home", str(args.home),
                             "--run-id", run_id], capture_output=True, text=True)
    if result.returncode == 0:
        tasks = json.loads(result.stdout)
        (output / f"{run_id}-tasks.json").write_text(json.dumps(tasks, indent=2) + "\n")
print(f"Aggregate evidence exported to {output}; total rows: 76206")

"""Generate once, preserve on redeploy, and send Secrets via stdin, outside Terraform."""
import argparse
import base64
import json
import os
import secrets
import subprocess
from pathlib import Path
from urllib.parse import quote

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--home", type=Path, required=True)
args = parser.parse_args()
directory = args.home / "secrets"
directory.mkdir(mode=0o700, exist_ok=True)
path = directory / "credentials.json"
if path.exists():
    credentials = json.loads(path.read_text())
else:
    credentials = {name: secrets.token_urlsafe(32) for name in
                   ["postgres", "etl", "airflow", "analyst", "airflow_admin", "api_key", "jwt_key"]}
    credentials["fernet_key"] = base64.urlsafe_b64encode(os.urandom(32)).decode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as file:
        json.dump(credentials, file, indent=2)
os.chmod(path, 0o600)
secrets_data = {
    "banvic-postgres-admin": {"POSTGRES_USER": "postgres", "POSTGRES_DB": "postgres",
        "POSTGRES_PASSWORD": credentials["postgres"], "ETL_PASSWORD": credentials["etl"],
        "AIRFLOW_PASSWORD": credentials["airflow"], "ANALYST_PASSWORD": credentials["analyst"]},
    "banvic-warehouse": {"PGHOST": "postgres", "PGPORT": "5432", "PGDATABASE": "banvic_dw",
        "PGUSER": "banvic_etl", "PGPASSWORD": credentials["etl"]},
    "banvic-airflow-metadata": {"connection": f"postgresql://airflow:{quote(credentials['airflow'], safe='')}@postgres:5432/airflow_metadata"},
    "banvic-airflow-fernet": {"fernet-key": credentials["fernet_key"]},
    "banvic-airflow-api": {"api-secret-key": credentials["api_key"]},
    "banvic-airflow-jwt": {"jwt-secret": credentials["jwt_key"]},
    "banvic-airflow-auth": {"passwords.json": json.dumps({"admin": credentials["airflow_admin"]})},
}
items = [{"apiVersion": "v1", "kind": "Secret", "metadata": {"name": name, "namespace": "banvic"},
          "type": "Opaque", "stringData": values} for name, values in secrets_data.items()]
result = subprocess.run(["kubectl", "apply", "--server-side", "--field-manager=banvic-secrets", "-f", "-"],
                        input=json.dumps({"apiVersion": "v1", "kind": "List", "items": items}), text=True,
                        capture_output=True)
if result.returncode:
    raise RuntimeError("Secret installation failed; verify Kubernetes context and namespace")
print("Seven Kubernetes Secrets configured. Credentials remain in the private WSL directory.")

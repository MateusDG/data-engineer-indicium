"""Trigger and inspect Airflow 3 through its authenticated public API."""
import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("command", choices=["trigger", "status", "wait", "tasks"])
parser.add_argument("--home", type=Path, required=True)
parser.add_argument("--run-id", required=True)
parser.add_argument("--fail-once", default="")
parser.add_argument("--fail-always", default="")
parser.add_argument("--url", default="http://127.0.0.1:8080")
args = parser.parse_args()
credentials = json.loads((args.home / "secrets/credentials.json").read_text())

def request(path, method="GET", body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(args.url + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

token = request("/auth/token", "POST", {"username": "admin", "password": credentials["airflow_admin"]})["access_token"]
from urllib.parse import quote
base = "/api/v2/dags/banvic_ingestion"
run_path = f"{base}/dagRuns/{quote(args.run_id, safe='')}"
if args.command == "trigger":
    request(base, "PATCH", {"is_paused": False}, token)
    result = request(base + "/dagRuns", "POST", {"dag_run_id": args.run_id,
        "logical_date": None, "conf": {"simulate_failure_once": args.fail_once,
                                     "simulate_failure_always": args.fail_always}}, token)
    print(json.dumps({"run_id": result["dag_run_id"], "state": result["state"]}))
elif args.command == "tasks":
    result = request(run_path + "/taskInstances", token=token)
    print(json.dumps([{key: item.get(key) for key in ["task_id", "state", "try_number"]} for item in result["task_instances"]], indent=2))
else:
    started = time.monotonic()
    while True:
        result = request(run_path, token=token)
        print(json.dumps({"run_id": result["dag_run_id"], "state": result["state"]}), flush=True)
        if args.command == "status" or result["state"] in ["success", "failed"]:
            break
        if time.monotonic() - started > 2700:
            raise TimeoutError("DAG did not finish in 45 minutes")
        time.sleep(15)
    if args.command == "wait" and result["state"] != "success":
        raise SystemExit(1)

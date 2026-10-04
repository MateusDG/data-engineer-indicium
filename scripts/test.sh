#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
cd "$BANVIC_REPO"
banvic_python=$(uv python find 3.12.15)
"$banvic_python" -m unittest discover -s tests -p test_source.py -v
terraform fmt -recursive -check infra
for script in scripts/*.sh infra/postgres-init.sh; do bash -n "$script"; done
docker run --rm --entrypoint python banvic-airflow:1.0.0 -c \
  'from airflow.dag_processing.dagbag import DagBag; b=DagBag("/opt/airflow/dags", include_examples=False); assert not b.import_errors, b.import_errors; d=b.dags["banvic_ingestion"]; assert len(d.tasks)==13; print("DAG import, task count and cycle checks passed")'
if [[ ${1:-} == --integration ]]; then
  banvic_require_cluster
  # Use a short-lived pod with the ETL Secret, without exposing credentials to the shell.
  kubectl -n banvic delete pod banvic-integration-tests --ignore-not-found >/dev/null
  kubectl -n banvic create configmap banvic-integration-tests --from-file=tests/test_database.py --dry-run=client -o yaml | kubectl apply -f - >/dev/null
  python3 - <<'PY' | kubectl -n banvic apply -f - >/dev/null
import json
print(json.dumps({'apiVersion':'v1','kind':'Pod','metadata':{'name':'banvic-integration-tests','namespace':'banvic'},
 'spec':{'restartPolicy':'Never','serviceAccountName':'banvic-pipeline','containers':[{
 'name':'tests','image':'banvic-pipeline:1.0.0','imagePullPolicy':'Never',
 'command':['python','/tests/test_database.py'], 'env':[{'name':'BANVIC_TEST_DATABASE','value':'1'}],
 'envFrom':[{'secretRef':{'name':'banvic-warehouse'}}],
 'volumeMounts':[{'name':'tests','mountPath':'/tests','readOnly':True}]}],
 'volumes':[{'name':'tests','configMap':{'name':'banvic-integration-tests'}}]}}))
PY
  kubectl -n banvic wait --for=jsonpath='{.status.phase}'=Succeeded pod/banvic-integration-tests --timeout=180s || { kubectl -n banvic logs banvic-integration-tests; exit 1; }
  kubectl -n banvic logs banvic-integration-tests
  kubectl -n banvic delete pod banvic-integration-tests >/dev/null
fi

#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
cd "$BANVIC_REPO"
banvic_require_cluster
commercial_exists=false
if kubectl -n banvic get deployment banvic-commercial >/dev/null 2>&1; then commercial_exists=true; fi
[[ -f commercial/static/vendor/echarts.min.js ]] || { echo 'Execute npm ci e npm run vendor na pasta commercial antes do build.' >&2; exit 1; }
python3 scripts/bootstrap_secrets.py --home "$BANVIC_HOME"
kubectl -n banvic exec -i postgres-0 -- sh -c 'export PGPASSWORD="$ETL_PASSWORD"; exec psql -h 127.0.0.1 -U banvic_etl -d banvic_dw -v ON_ERROR_STOP=1' < sql/commercial.sql
docker build -f docker/commercial.Dockerfile -t banvic-commercial:1.0.0 .
kind load docker-image --name banvic banvic-commercial:1.0.0
mkdir -p "$BANVIC_HOME/terraform/commercial"
export TF_DATA_DIR="$BANVIC_HOME/terraform/commercial/provider-cache"
terraform -chdir=infra/commercial init -input=false -reconfigure -backend-config="path=$BANVIC_HOME/terraform/commercial/terraform.tfstate"
terraform -chdir=infra/commercial apply -input=false -auto-approve
if "$commercial_exists"; then kubectl -n banvic rollout restart deployment/banvic-commercial; fi
kubectl -n banvic rollout status deployment/banvic-commercial --timeout=300s
echo 'Dashboard implantado. Execute bash scripts/access.sh. Acesso: http://localhost:8090'

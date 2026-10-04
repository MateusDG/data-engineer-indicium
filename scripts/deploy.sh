#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
cd "$BANVIC_REPO"
banvic_source=${1:-"$BANVIC_REPO/Dados Banvic.zip"}
[[ -f "$banvic_source" ]] || { echo 'Informe o caminho do ZIP oficial como primeiro argumento.' >&2; exit 1; }
docker info >/dev/null
mkdir -p "$BANVIC_HOME/data/input" "$BANVIC_HOME/data/work" "$BANVIC_HOME/postgres" "$BANVIC_HOME/logs" "$BANVIC_HOME/terraform/platform" "$BANVIC_HOME/terraform/airflow"
chmod 750 "$BANVIC_HOME/data" "$BANVIC_HOME/data/work"
chmod 755 "$BANVIC_HOME/data/input"
cp -- "$banvic_source" "$BANVIC_HOME/data/input/.banvic_data.zip.tmp"
chmod 444 "$BANVIC_HOME/data/input/.banvic_data.zip.tmp"
mv -- "$BANVIC_HOME/data/input/.banvic_data.zip.tmp" "$BANVIC_HOME/data/input/banvic_data.zip"

if ! kind get clusters | grep -qx banvic; then
  python3 - "$BANVIC_HOME" <<'PY' > "$BANVIC_HOME/kind.yaml"
import json, sys
from pathlib import Path
home = Path(sys.argv[1]).resolve()
print(json.dumps({'kind':'Cluster','apiVersion':'kind.x-k8s.io/v1alpha4','name':'banvic',
 'nodes':[{'role':'control-plane','extraMounts':[
 {'hostPath':str(home/'data'),'containerPath':'/banvic/data'},
 {'hostPath':str(home/'postgres'),'containerPath':'/banvic/postgres'},
 {'hostPath':str(home/'logs'),'containerPath':'/banvic/logs'}]}]}))
PY
  kind create cluster --name banvic --config "$BANVIC_HOME/kind.yaml" \
    --image 'kindest/node:v1.35.8@sha256:07b2536e30b803ed61d1677a79df6115f798ce64c80f9e22f6ed45afd09323c0' \
    --kubeconfig "$KUBECONFIG" --wait 180s
else
  kind export kubeconfig --name banvic --kubeconfig "$KUBECONFIG"
fi
banvic_require_cluster

# Assign only this project's new volume roots to the container UIDs.
docker run --rm --user 0 --entrypoint sh \
  -v "$BANVIC_HOME/postgres:/banvic-postgres" -v "$BANVIC_HOME/logs:/banvic-logs" \
  'postgres:16@sha256:71e27bf60b70bded003791b5573f8b808365613f341df20ffcf0c1ed7bc13ddf' \
  -c 'chown 999:999 /banvic-postgres; chmod 700 /banvic-postgres; chown 50000:0 /banvic-logs; chmod 770 /banvic-logs'

bash scripts/build_images.sh
export TF_DATA_DIR="$BANVIC_HOME/terraform/platform/provider-cache"
terraform -chdir=infra/platform init -input=false -reconfigure -backend-config="path=$BANVIC_HOME/terraform/platform/terraform.tfstate"
terraform -chdir=infra/platform apply -input=false -auto-approve
python3 scripts/bootstrap_secrets.py --home "$BANVIC_HOME"
kubectl -n banvic rollout status statefulset/postgres --timeout=240s

export TF_DATA_DIR="$BANVIC_HOME/terraform/airflow/provider-cache"
terraform -chdir=infra/airflow init -input=false -reconfigure -backend-config="path=$BANVIC_HOME/terraform/airflow/terraform.tfstate"
terraform -chdir=infra/airflow apply -input=false -auto-approve
kubectl -n banvic get pods
echo 'Ambiente pronto. Execute bash scripts/access.sh para abrir as portas locais.'

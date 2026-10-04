#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
banvic_require_cluster
export TF_DATA_DIR="$BANVIC_HOME/terraform/airflow/provider-cache"
terraform -chdir="$BANVIC_REPO/infra/airflow" init -input=false -reconfigure \
  -backend-config="path=$BANVIC_HOME/terraform/airflow/terraform.tfstate"
terraform -chdir="$BANVIC_REPO/infra/airflow" apply -input=false -auto-approve

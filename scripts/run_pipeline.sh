#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
banvic_run_id=${1:-"manual_$(date -u +%Y%m%dT%H%M%SZ)"}
python3 "$BANVIC_REPO/scripts/airflow_api.py" trigger --home "$BANVIC_HOME" --run-id "$banvic_run_id" "${@:2}"
python3 "$BANVIC_REPO/scripts/airflow_api.py" wait --home "$BANVIC_HOME" --run-id "$banvic_run_id"
bash "$BANVIC_REPO/scripts/verify.sh"

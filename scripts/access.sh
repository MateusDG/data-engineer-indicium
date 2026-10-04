#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
banvic_require_cluster
start_forward() {
  local name=$1 service=$2 ports=$3
  local pid_file="$BANVIC_REPO/.runtime/$name.pid"
  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null && \
     [[ $(awk '{print $3}' "/proc/$(cat "$pid_file")/stat" 2>/dev/null) != Z ]]; then
    echo "$name já está ativo."
    return
  fi
  nohup kubectl -n banvic port-forward --address 127.0.0.1 "$service" "$ports" > "$BANVIC_REPO/.runtime/$name.log" 2>&1 < /dev/null &
  echo $! > "$pid_file"
}
start_forward airflow svc/airflow-api-server 8080:8080
start_forward postgres svc/postgres 5433:5432
for attempt in {1..30}; do
  if curl --fail --silent http://127.0.0.1:8080/api/v2/monitor/health >/dev/null; then break; fi
  sleep 1
done
curl --fail --silent http://127.0.0.1:8080/api/v2/monitor/health >/dev/null
echo 'Airflow: http://localhost:8080 | PostgreSQL: localhost:5433 / banvic_dw'
echo "Credenciais privadas: $BANVIC_HOME/secrets/credentials.json"

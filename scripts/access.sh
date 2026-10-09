#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
banvic_require_cluster
banvic_reattach_volumes
start_forward() {
  local name=$1 service=$2 ports=$3 health_url=${4:-}
  local pid_file="$BANVIC_REPO/.runtime/$name.pid"
  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null && \
     [[ $(awk '{print $3}' "/proc/$(cat "$pid_file")/stat" 2>/dev/null) != Z ]]; then
    local forward_pid forward_command
    forward_pid=$(cat "$pid_file")
    forward_command=$(tr '\0' ' ' < "/proc/$forward_pid/cmdline")
    if [[ "$forward_command" == *kubectl*port-forward*"$service"*"$ports"* ]]; then
      if [[ -z "$health_url" ]] || curl --fail --silent --max-time 2 "$health_url" >/dev/null; then
        echo "$name já está ativo."
        return
      fi
      kill "$forward_pid"
      wait "$forward_pid" 2>/dev/null || true
    fi
  fi
  nohup kubectl -n banvic port-forward --address 127.0.0.1 "$service" "$ports" > "$BANVIC_REPO/.runtime/$name.log" 2>&1 < /dev/null &
  echo $! > "$pid_file"
}
start_forward airflow svc/airflow-api-server 8080:8080 http://127.0.0.1:8080/api/v2/monitor/health
start_forward postgres svc/postgres 5433:5432
if kubectl -n banvic get service banvic-commercial >/dev/null 2>&1; then
  start_forward commercial svc/banvic-commercial 8090:8090 http://127.0.0.1:8090/health/live
fi
for attempt in {1..30}; do
  if curl --fail --silent http://127.0.0.1:8080/api/v2/monitor/health >/dev/null; then break; fi
  sleep 1
done
curl --fail --silent http://127.0.0.1:8080/api/v2/monitor/health >/dev/null
echo 'Airflow: http://localhost:8080 | PostgreSQL: localhost:5433 / banvic_dw'
if kubectl -n banvic get service banvic-commercial >/dev/null 2>&1; then
  for commercial_attempt in {1..30}; do
    if curl --fail --silent --max-time 2 http://127.0.0.1:8090/health/live >/dev/null; then break; fi
    sleep 1
  done
  curl --fail --silent --max-time 2 http://127.0.0.1:8090/health/live >/dev/null
  echo 'Dashboard comercial: http://localhost:8090 | usuário comercial'
fi
echo "Credenciais privadas: $BANVIC_HOME/secrets/credentials.json"

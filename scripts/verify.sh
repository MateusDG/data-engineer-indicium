#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
banvic_require_cluster
kubectl -n banvic exec -i postgres-0 -- sh -c 'export PGPASSWORD="$ETL_PASSWORD"; exec psql -h 127.0.0.1 -U banvic_etl -d banvic_dw -v ON_ERROR_STOP=1' < "$BANVIC_REPO/sql/verify.sql"

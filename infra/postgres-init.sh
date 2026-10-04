#!/usr/bin/env bash
set -euo pipefail
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=etl_password="$ETL_PASSWORD" --set=airflow_password="$AIRFLOW_PASSWORD" \
  --set=analyst_password="$ANALYST_PASSWORD" <<'SQL'
SELECT format('CREATE ROLE banvic_etl LOGIN PASSWORD %L', :'etl_password') \gexec
SELECT format('CREATE ROLE airflow LOGIN PASSWORD %L', :'airflow_password') \gexec
SELECT format('CREATE ROLE banvic_analyst LOGIN PASSWORD %L', :'analyst_password') \gexec
CREATE DATABASE banvic_dw OWNER banvic_etl;
CREATE DATABASE airflow_metadata OWNER airflow;
REVOKE ALL ON DATABASE banvic_dw FROM PUBLIC;
GRANT CONNECT ON DATABASE banvic_dw TO banvic_etl, banvic_analyst;
REVOKE ALL ON DATABASE airflow_metadata FROM PUBLIC;
GRANT CONNECT ON DATABASE airflow_metadata TO airflow;
\connect banvic_dw
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
SQL

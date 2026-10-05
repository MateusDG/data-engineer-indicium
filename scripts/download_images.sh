#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"

docker version >/dev/null
docker pull apache/airflow:3.2.2-python3.12@sha256:bbe58e3204d550ab98dbf738a42c0e6663c455357ecd0e2d1440ef9cb6a75f00
docker pull meltano/meltano:v4.4.0-python3.12-slim@sha256:dc5421533a91de964a5bc21adf12339f74466a5eb564568bd7592a0bd3b23db7
docker pull postgres:16@sha256:71e27bf60b70bded003791b5573f8b808365613f341df20ffcf0c1ed7bc13ddf
docker pull kindest/node:v1.35.8@sha256:07b2536e30b803ed61d1677a79df6115f798ce64c80f9e22f6ed45afd09323c0

helm repo add apache-airflow https://airflow.apache.org
helm repo update apache-airflow
mkdir -p "$BANVIC_HOME/downloads"
helm pull apache-airflow/airflow --version 1.22.0 --destination "$BANVIC_HOME/downloads"

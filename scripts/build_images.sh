#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
cd "$BANVIC_REPO"
docker build -f docker/pipeline.Dockerfile -t banvic-pipeline:1.0.0 .
docker build -f docker/airflow.Dockerfile -t banvic-airflow:1.0.0 .
banvic_require_cluster
kind load docker-image --name banvic banvic-pipeline:1.0.0 banvic-airflow:1.0.0

#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
cd "$BANVIC_REPO"
docker run --rm --entrypoint python -v "$BANVIC_REPO/tests:/tests:ro" banvic-commercial:1.0.0 \
  -m unittest discover -s /tests -p test_commercial.py -v
terraform fmt -recursive -check infra
for banvic_script in scripts/*.sh; do bash -n "$banvic_script"; done
echo 'Commercial unit tests, Terraform formatting and shell syntax passed.'

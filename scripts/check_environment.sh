#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"

for banvic_command in docker git kind kubectl terraform helm uv meltano; do
  if ! command -v "$banvic_command" >/dev/null; then
    echo "Ferramenta ausente: $banvic_command" >&2
    exit 1
  fi
done

docker version --format 'Docker cliente={{.Client.Version}} servidor={{.Server.Version}}'
git --version
kind version
kubectl version --client
terraform version
helm version --short
uv --version
banvic_python=$(uv python find 3.12.15)
"$banvic_python" --version
meltano --version

docker run --rm apache/airflow:3.2.2-python3.12@sha256:bbe58e3204d550ab98dbf738a42c0e6663c455357ecd0e2d1440ef9cb6a75f00 version
docker run --rm meltano/meltano:v4.4.0-python3.12-slim@sha256:dc5421533a91de964a5bc21adf12339f74466a5eb564568bd7592a0bd3b23db7 --version
docker run --rm --entrypoint postgres postgres:16@sha256:71e27bf60b70bded003791b5573f8b808365613f341df20ffcf0c1ed7bc13ddf --version
docker image inspect kindest/node@sha256:07b2536e30b803ed61d1677a79df6115f798ce64c80f9e22f6ed45afd09323c0 --format '{{json .RepoDigests}}'

banvic_plugin_project="$HOME/.local/share/banvic-tools/meltano-check"
if [[ ! -f "$banvic_plugin_project/meltano.yml" ]]; then
  echo 'Projeto local de verificacao dos conectores ausente.' >&2
  exit 1
fi
cd "$banvic_plugin_project"
meltano invoke tap-csv --version
meltano invoke target-postgres --version
test -f "$BANVIC_HOME/downloads/airflow-1.22.0.tgz"
echo 'Verificacao do ambiente concluida.'

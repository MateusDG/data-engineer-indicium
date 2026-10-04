#!/usr/bin/env bash
# Install and verify the connectors in a local setup project, without source data.
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"

if [[ $(id -u) -eq 0 ]]; then
  echo 'Execute como o usuario normal do Ubuntu, sem sudo.' >&2
  exit 1
fi

banvic_plugin_project="$HOME/.local/share/banvic-tools/meltano-check"
if [[ ! -f "$banvic_plugin_project/meltano.yml" ]]; then
  meltano init "$banvic_plugin_project" --no-usage-stats
fi
cd "$banvic_plugin_project"
mkdir -p plugin-definitions
banvic_hub_commit=daacdaf9ab3a2de7532c473c2a75d613aa080893
curl -fsSL --retry 3 -o plugin-definitions/tap-csv.yml \
  "https://raw.githubusercontent.com/meltano/hub/$banvic_hub_commit/_data/meltano/extractors/tap-csv/meltanolabs.yml"
curl -fsSL --retry 3 -o plugin-definitions/target-postgres.yml \
  "https://raw.githubusercontent.com/meltano/hub/$banvic_hub_commit/_data/meltano/loaders/target-postgres/meltanolabs.yml"

python3 - <<'PY'
from pathlib import Path
import re

pins = {
    'tap-csv': 'git+https://github.com/MeltanoLabs/tap-csv.git@0c84ec05266b5924134c0e0c2bb5e764475d845b',
    'target-postgres': 'meltanolabs-target-postgres==0.8.0',
}
for name, pin in pins.items():
    path = Path('plugin-definitions') / f'{name}.yml'
    text = path.read_text(encoding='utf-8')
    text, count = re.subn(r'^pip_url:.*$', f'pip_url: {pin}', text, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f'Formato inesperado de pip_url em {name}')
    path.write_text(text, encoding='utf-8')
PY

printf '%s\n' "$banvic_hub_commit" > plugin-definitions/hub-commit.txt
meltano add tap-csv --from-ref plugin-definitions/tap-csv.yml --no-install
meltano add target-postgres --from-ref plugin-definitions/target-postgres.yml --no-install
meltano install
meltano invoke tap-csv --version
meltano invoke target-postgres --version

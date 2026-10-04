#!/usr/bin/env bash
# Run as the regular Ubuntu/WSL user, not root.
set -euo pipefail

if [[ $(id -u) -eq 0 ]]; then
  echo 'Execute como o usuario normal do Ubuntu, sem sudo.' >&2
  exit 1
fi

banvic_tools_dir="$HOME/.local/share/banvic-tools"
mkdir -p "$banvic_tools_dir" "$HOME/.local/bin"
python3 -m venv "$banvic_tools_dir/uv"
"$banvic_tools_dir/uv/bin/python" -m pip install --disable-pip-version-check 'uv==0.12.22'
if [[ -e "$HOME/.local/bin/uv" || -L "$HOME/.local/bin/uv" ]]; then
  if [[ $(readlink -f "$HOME/.local/bin/uv") != "$banvic_tools_dir/uv/bin/uv" ]]; then
    echo 'Ja existe outro uv em ~/.local/bin; a instalacao existente foi preservada.' >&2
    exit 1
  fi
else
  ln -s "$banvic_tools_dir/uv/bin/uv" "$HOME/.local/bin/uv"
fi
export PATH="$HOME/.local/bin:$PATH"

uv python install 3.12.15
uv tool install --python 3.12.15 'meltano==4.4.0'
uv --version
uv python find 3.12
meltano --version

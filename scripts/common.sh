#!/usr/bin/env bash
# Source from WSL/Linux scripts. Keep data, credentials and Terraform state off Git.
set -euo pipefail
BANVIC_REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BANVIC_HOME=${BANVIC_HOME:-"$HOME/banvic-local"}
export KUBECONFIG="$BANVIC_HOME/kubeconfig"
export TF_VAR_kubeconfig_path="$KUBECONFIG"
export PATH="$HOME/.local/bin:$PATH"
mkdir -p "$BANVIC_HOME" "$BANVIC_REPO/.runtime"
banvic_require_cluster() {
  [[ -f "$KUBECONFIG" ]] || { echo 'Execute scripts/deploy.sh primeiro.' >&2; exit 1; }
  [[ $(kubectl config current-context) == kind-banvic ]] || { echo 'Contexto Kubernetes incorreto.' >&2; exit 1; }
}

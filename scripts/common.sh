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
# After a Windows/Docker restart the Kind node can start before Ubuntu shares its files and
# then sees empty volume directories (PostgreSQL enters CrashLoopBackOff). Restarting the node
# re-attaches the real data, which is never touched while the mounts are empty.
banvic_reattach_volumes() {
  [[ -f "$BANVIC_HOME/data/input/banvic_data.zip" ]] || return 0
  docker exec banvic-control-plane test -f /banvic/data/input/banvic_data.zip && return 0
  echo 'Reconectando os volumes do cluster após reinício do Docker...'
  docker restart banvic-control-plane >/dev/null
  for _ in {1..60}; do kubectl get --raw /readyz >/dev/null 2>&1 && break; sleep 2; done
  sleep 15  # let the kubelet replace the pod states recorded before the restart
  kubectl -n banvic wait --for=condition=Ready pod --all --field-selector=status.phase!=Succeeded --timeout=300s
}

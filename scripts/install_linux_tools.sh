#!/usr/bin/env bash
# Run in Ubuntu/WSL as root: sudo bash scripts/install_linux_tools.sh
set -euo pipefail

if [[ $(id -u) -ne 0 ]]; then
  echo 'Execute como root no Ubuntu: sudo bash scripts/install_linux_tools.sh' >&2
  exit 1
fi
if [[ $(uname -m) != x86_64 ]]; then
  echo 'Este instalador foi preparado para Linux x86_64.' >&2
  exit 1
fi

banvic_missing_packages=()
for banvic_package in ca-certificates curl unzip python3-venv make git; do
  if ! dpkg -s "$banvic_package" >/dev/null 2>&1; then
    banvic_missing_packages+=("$banvic_package")
  fi
done
if (( ${#banvic_missing_packages[@]} )); then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get -o DPkg::Lock::Timeout=120 install -y -qq \
    "${banvic_missing_packages[@]}"
fi

banvic_cache=/var/cache/banvic-tools
mkdir -p "$banvic_cache"
cd "$banvic_cache"

download() {
  curl --fail --silent --show-error --location --retry 3 --connect-timeout 20 \
    --output "$2" "$1"
}

echo 'Baixando e verificando Kind 0.33.0...'
download https://github.com/kubernetes-sigs/kind/releases/download/v0.33.0/kind-linux-amd64 kind-linux-amd64
download https://github.com/kubernetes-sigs/kind/releases/download/v0.33.0/kind-linux-amd64.sha256sum kind-linux-amd64.sha256sum
sha256sum --check kind-linux-amd64.sha256sum
install -m 0755 kind-linux-amd64 /usr/local/bin/kind

echo 'Baixando e verificando kubectl 1.35.8...'
download https://dl.k8s.io/release/v1.35.8/bin/linux/amd64/kubectl kubectl
download https://dl.k8s.io/release/v1.35.8/bin/linux/amd64/kubectl.sha256 kubectl.sha256
printf '%s  kubectl\n' "$(cat kubectl.sha256)" | sha256sum --check
install -m 0755 kubectl /usr/local/bin/kubectl

echo 'Baixando e verificando Terraform 1.16.4...'
download https://releases.hashicorp.com/terraform/1.16.4/terraform_1.16.4_linux_amd64.zip terraform_1.16.4_linux_amd64.zip
download https://releases.hashicorp.com/terraform/1.16.4/terraform_1.16.4_SHA256SUMS terraform_1.16.4_SHA256SUMS
sha256sum --check --ignore-missing terraform_1.16.4_SHA256SUMS
mkdir -p terraform-1.16.4
unzip -qo terraform_1.16.4_linux_amd64.zip -d terraform-1.16.4
install -m 0755 terraform-1.16.4/terraform /usr/local/bin/terraform

echo 'Baixando e verificando Helm 3.21.4...'
download https://get.helm.sh/helm-v3.21.4-linux-amd64.tar.gz helm-v3.21.4-linux-amd64.tar.gz
printf '%s  helm-v3.21.4-linux-amd64.tar.gz\n' \
  61f88ab166748cb19604d7884cb100ae9ccb13804ddeb98e08af167eacbb6a14 | sha256sum --check
mkdir -p helm-3.21.4
tar -xzf helm-v3.21.4-linux-amd64.tar.gz -C helm-3.21.4
install -m 0755 helm-3.21.4/linux-amd64/helm /usr/local/bin/helm

kind version
kubectl version --client
terraform version
helm version --short

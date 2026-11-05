#!/usr/bin/env bash
# Run in the macOS Terminal as the regular user, without sudo: bash scripts/install_mac_tools.sh
# Installs the same pinned Kind, kubectl, Terraform and Helm versions as install_linux_tools.sh
# into ~/.local/bin (or BANVIC_BIN_DIR). The checksums match the official release files.
set -euo pipefail

if [[ $(uname -s) != Darwin ]]; then
  echo 'Este instalador é para macOS. No Ubuntu/WSL use scripts/install_linux_tools.sh.' >&2
  exit 1
fi
if [[ $(id -u) -eq 0 ]]; then
  echo 'Execute como o usuário normal do macOS, sem sudo.' >&2
  exit 1
fi

# Prefer native binaries on Apple Silicon even when the terminal runs under Rosetta.
if [[ $(sysctl -in hw.optional.arm64) == 1 ]]; then
  banvic_arch=arm64
  banvic_kind_sha=0c8c7dbe5e23594a198b786c4bc13dacc101fa6196b0cb0b23a1ca44e61f4b4f
  banvic_kubectl_sha=b8be50ae0c6665b646fb009f904a52cad30806deee19ab3b4fe5af2d68bd82eb
  banvic_terraform_sha=42cfdf97ad722f79085fe2279b06d4b8680172de3534b22eeddd9a0fbbe7b8f1
  banvic_helm_sha=6e0bf5eb6daafc2b1ec34bb5ba04ef103f3afc16192fb19805c2924d7ea1033f
elif [[ $(uname -m) == x86_64 ]]; then
  banvic_arch=amd64
  banvic_kind_sha=5a99f26f57246dc9319dd294803313197a0f34d33c525b3ea8b655db5916ece0
  banvic_kubectl_sha=35c964c16432ea65eda6600d6ff4fea040d5eafcb6ad410297ba67d49b618148
  banvic_terraform_sha=2ee4b62064086e4b24b0d6cf2e61718fbaf0556feba990f708a5e32557554b3b
  banvic_helm_sha=9173d05edf9592c6be1d0412ffafd935448dfc7a63c2bc732b8c67e55503e8a8
else
  echo "Arquitetura não suportada: $(uname -m)" >&2
  exit 1
fi

banvic_bin_dir=${BANVIC_BIN_DIR:-"$HOME/.local/bin"}
mkdir -p "$banvic_bin_dir"
banvic_work=$(mktemp -d "${TMPDIR:-/tmp}/banvic-tools.XXXXXX")
trap 'rm -rf "$banvic_work"' EXIT
cd "$banvic_work"

download() {
  curl --fail --silent --show-error --location --retry 3 --connect-timeout 20 \
    --output "$2" "$1"
}

verify() {
  local banvic_actual
  banvic_actual=$(shasum -a 256 "$1" | awk '{print $1}')
  if [[ $banvic_actual != "$2" ]]; then
    echo "Checksum inválido para $1: esperado $2, obtido $banvic_actual" >&2
    exit 1
  fi
  echo "$1: OK"
}

echo 'Baixando e verificando Kind 0.33.0...'
download "https://github.com/kubernetes-sigs/kind/releases/download/v0.33.0/kind-darwin-$banvic_arch" kind
verify kind "$banvic_kind_sha"
install -m 0755 kind "$banvic_bin_dir/kind"

echo 'Baixando e verificando kubectl 1.35.8...'
download "https://dl.k8s.io/release/v1.35.8/bin/darwin/$banvic_arch/kubectl" kubectl
verify kubectl "$banvic_kubectl_sha"
install -m 0755 kubectl "$banvic_bin_dir/kubectl"

echo 'Baixando e verificando Terraform 1.16.4...'
download "https://releases.hashicorp.com/terraform/1.16.4/terraform_1.16.4_darwin_$banvic_arch.zip" terraform.zip
verify terraform.zip "$banvic_terraform_sha"
unzip -qo terraform.zip terraform -d terraform-1.16.4
install -m 0755 terraform-1.16.4/terraform "$banvic_bin_dir/terraform"

echo 'Baixando e verificando Helm 3.21.4...'
download "https://get.helm.sh/helm-v3.21.4-darwin-$banvic_arch.tar.gz" helm.tar.gz
verify helm.tar.gz "$banvic_helm_sha"
mkdir -p helm-3.21.4
tar -xzf helm.tar.gz -C helm-3.21.4
install -m 0755 "helm-3.21.4/darwin-$banvic_arch/helm" "$banvic_bin_dir/helm"

"$banvic_bin_dir/kind" version
"$banvic_bin_dir/kubectl" version --client
CHECKPOINT_DISABLE=1 "$banvic_bin_dir/terraform" version  # the project requires 1.16.x
"$banvic_bin_dir/helm" version --short

# OrbStack and Docker Desktop ship an older kubectl in /usr/local/bin. The project scripts put
# ~/.local/bin first on their own PATH; interactive shells need the same order.
for banvic_tool in kind kubectl terraform helm; do
  if [[ $(command -v "$banvic_tool" || true) != "$banvic_bin_dir/$banvic_tool" ]]; then
    echo "Aviso: no seu terminal, '$banvic_tool' não aponta para $banvic_bin_dir." >&2
    echo "Adicione ao ~/.zshrc: export PATH=\"$banvic_bin_dir:\$PATH\"" >&2
    break
  fi
done

if ! docker info >/dev/null 2>&1; then
  echo 'Aviso: Docker não está respondendo. Abra o OrbStack ou o Docker Desktop antes do deploy.' >&2
fi

echo 'Ferramentas instaladas. Próximo passo: bash scripts/install_python_tools.sh'

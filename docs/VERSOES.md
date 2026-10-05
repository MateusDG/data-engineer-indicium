# Versões e reprodução

Ambiente implantado e validado em **4 de outubro de 2026**, usando Ubuntu 22.04 no WSL 2 e Docker Desktop.

| Componente | Versão |
|---|---|
| Ubuntu | 22.04.5 LTS |
| Docker Desktop / Engine | 4.45.0 / 28.3.3 |
| Kind / Kubernetes | 0.33.0 / 1.35.8 |
| kubectl | 1.35.8 |
| Terraform | 1.16.4 |
| Kubernetes provider | 2.38.0 |
| Helm CLI / provider | 3.21.4 / 2.17.0 |
| Chart Airflow | 1.22.0 |
| Apache Airflow | 3.2.2, Python 3.12 |
| Meltano | 4.4.0 |
| Python da imagem Meltano | 3.12.14 |
| Python dos testes locais | 3.12.15, via uv 0.12.22 |
| PostgreSQL | 16.13 |
| psycopg da aplicação | 3.2.12 |
| target-postgres | 0.8.0 |
| tap-csv | Commit 0c84ec05266b5924134c0e0c2bb5e764475d845b |
| Python da imagem comercial | 3.12.14 |
| FastAPI / Uvicorn | 0.142.2 / 0.54.0 |
| pandas / NumPy / SciPy | 3.0.6 / 2.5.3 / 1.18.1 |
| scikit-learn | 1.9.1 |
| psycopg da camada comercial | 3.3.6 |
| Apache ECharts | 6.1.0 |

O commit do tap corresponde à tag Git v1.3.2; o executável reporta v1.2.0. A referência de reprodução é o commit. As dependências transitivas dos dois conectores estão fixadas em `meltano/constraints-tap.txt` e `meltano/constraints-target.txt`. Os providers estão registrados nos arquivos `.terraform.lock.hcl` versionados.

## Imagens base

| Imagem | Digest |
|---|---|
| apache/airflow:3.2.2-python3.12 | sha256:bbe58e3204d550ab98dbf738a42c0e6663c455357ecd0e2d1440ef9cb6a75f00 |
| meltano/meltano:v4.4.0-python3.12-slim | sha256:dc5421533a91de964a5bc21adf12339f74466a5eb564568bd7592a0bd3b23db7 |
| postgres:16 | sha256:71e27bf60b70bded003791b5573f8b808365613f341df20ffcf0c1ed7bc13ddf |
| kindest/node:v1.35.8 | sha256:07b2536e30b803ed61d1677a79df6115f798ce64c80f9e22f6ed45afd09323c0 |

Imagens próprias: `banvic-pipeline:1.0.0` e `banvic-airflow:1.0.0`, construídas pelos Dockerfiles. Bibliotecas pré-instaladas no Airflow são fixadas pelo digest da imagem. Pacotes do sistema instalados por apt continuam sujeitos ao repositório da distribuição; não se afirma reprodução binária bit a bit.

A extensão validada em 05/10/2026 UTC acrescenta `banvic-commercial:1.0.0`, base `python:3.12.14-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f`. As 26 dependências Python estão fixadas com hashes em `commercial/requirements.lock`; a dependência de gráficos está em `commercial/package-lock.json`, com distribuição e licença incluídas em `static/vendor`. O terceiro provider lock fica em `infra/commercial/.terraform.lock.hcl`.

SHA-256 do chart oficial baixado e inspecionado: `1f7d1dfe3d58e2c54899950aba907a43625a18c8b6fb3c54760c21592129a5b6`.

## Diretórios no Ubuntu

- `/usr/local/bin`: Kind, kubectl, Terraform e Helm.
- `~/.local/bin`: uv e Meltano locais.
- `~/banvic-local/data/input`: ZIP oficial de entrada.
- `~/banvic-local/data/work`: snapshots e validações por execução.
- `~/banvic-local/postgres`: volume persistente do banco.
- `~/banvic-local/logs`: logs Airflow.
- `~/banvic-local/secrets`: credenciais privadas.
- `~/banvic-local/terraform`: estados e caches dos providers.

O fluxo do pipeline roda dentro das imagens. O Meltano instalado no usuário local é útil para diagnóstico, mas não fornece dependências aos pods. Para preparar outro computador, siga o README; para evidências da execução, consulte `docs/VALIDACAO.md`.

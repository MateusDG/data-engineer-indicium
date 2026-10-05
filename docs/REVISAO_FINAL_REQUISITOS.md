# Conferência final dos requisitos — BanVic

Revisão de **05/10/2026**, no ambiente Windows/WSL 2, Docker e Kind do projeto. Evidências atuais em `evidence/review3/` e verificações comerciais em `evidence/commercial/`.

## Resultado

**Os requisitos técnicos de engenharia e os arquivos de código, README e apresentação estão atendidos na POC local verificada.** Foram repetidos 30 testes e cinco cenários reais no Airflow. A execução final `review3_20261005_final` terminou com sucesso em **55,826 segundos**: 12 tarefas bem-sucedidas na primeira tentativa e `record_failure` corretamente ignorada. Todos os valores das **76.206 linhas** das sete tabelas coincidem com a fonte oficial.

O dashboard funciona sobre o warehouse publicado. A exigência de um ranking de investimentos com **efeito causal e retorno garantido** não pode ser declarada atendida com este ERP: faltam registros de intervenção, atribuição, custos, margem e confundidores relevantes. A aplicação entrega ranking exploratório de validação, incerteza, diagnósticos e planejamento de piloto; a lista de efeitos causais identificados permanece vazia.

**Vídeo excluído desta revisão por solicitação do usuário.** Não houve gravação, narração, edição, geração ou verificação de vídeo. O enunciado original ainda o lista como entregável. Esta conferência não afirma que a inscrição foi enviada ou que a banca concederá uma nota específica.

## Matriz de conformidade técnica

Os caminhos de evidência abaixo partem de `evidence/review3/`, salvo indicação contrária.

| Requisito | Implementação e comprovação | Situação |
|---|---|---|
| Kubernetes local | Kind, um nó Ready, namespace `banvic`; `persistence-and-node.json` | Atendido |
| Docker | Imagens próprias para Airflow, Meltano/pipeline e aplicação comercial; Dockerfiles e pods reais | Atendido |
| Terraform / IaC | Três módulos válidos, três planos com zero alterações; configuração Kind gerada pelo deploy; `terraform.json` | Atendido |
| Airflow e armazenamento no Kubernetes | Airflow e PostgreSQL com bancos/usuários distintos para metadados e warehouse; seis componentes Running/Ready em `pods.json` | Atendido |
| Persistência | Três PVCs Bound para dados, banco e logs; `persistence-and-node.json` | Atendido |
| ZIP oficial | `Dados Banvic.zip` montado como `banvic_data.zip`, conteúdo intacto; `source-and-scope.json` | Atendido |
| Sete cópias do ERP | Sete tabelas do contrato, sem substituição por dbt/Kaggle; todos os valores reconciliados em `warehouse-validation.json` | Atendido |
| Meltano ou Embulk | Meltano executa `tap-csv` → `target-postgres` nas sete tarefas reais de carga; configuração em `meltano/meltano.yml` | Atendido |
| Taps e targets | Commit/versões fixados, chaves declaradas, CSV estrito, UTF-8/BOM, COPY/upsert em staging; reconciliação integral e testes | Atendido |
| Integridade | Colunas, tipos, datas, chaves, contagens, hashes e vínculos; corrupção bloqueia publicação e inconsistências da origem são preservadas | Atendido |
| DAGs e tarefas | `dags/banvic_ingestion.py`, 13 tarefas; importação sem erros/ciclos; `dag-policy.json` | Atendido |
| Dependências | Sensor → preparação → sete cargas → validação → publicação → conclusão; tratamento de falha separado; grafo conferido na imagem e no navegador | Atendido |
| Agendamento | Diário às 06:00 em America/Sao_Paulo, sem catchup, uma execução ativa e até quatro tarefas simultâneas; `dag-policy.json` | Atendido |
| Sensor | Reschedule/timeout; arquivo ausente bloqueou preparação e restauração liberou execução; `sensor-waiting.json` e execução `_sensor` | Atendido |
| Monitoramento básico | Estados, duração, tentativas e logs no Airflow; logs persistentes, StatsD e auditoria SQL; `airflow-health.json` | Atendido |
| Retries e falhas | Duas tentativas adicionais com espera crescente; `contas` recuperou na tentativa 2 e falha permanente esgotou 3 tentativas | Atendido |
| Falha sem perda do destino | Tabelas e marcador iguais antes/depois de falha e ZIP inválido; `permanent-failure-preservation.json`, `invalid-zip-preservation.json` | Atendido |
| Idempotência | Snapshot congelado por execução, nova carga sem duplicação e republicação noop; `idempotency.json` e teste de banco | Atendido |
| Atomicidade | Transação para sete tabelas e marcador, lock e revalidação; erro em tabela tardia confirmou rollback integral | Atendido |
| Código modular e erros | Fonte, banco, comandos, DAG, SQL, infra e análise separados; testes de fonte, banco, entrega e análise passaram | Atendido |
| Credenciais fora do código | Secrets gerados no diretório privado; zero valores reais no projeto, histórico Git e três estados Terraform; `security.json` | Atendido |
| Privilégios mínimos | Ingestão sem privilégios/token; dashboard somente leitura e sem acesso a Secrets/criação de pods; `runtime-security.json`, `analyst-access.json` | Atendido |
| Consumo centralizado | Views `analytics`, PostgreSQL e dashboard; leitura real de analista, escrita e acesso ao banco de metadados negados | Atendido |
| README / diagrama | Mermaid, escolhas e arquitetura em README e `docs/ARQUITETURA.md` | Atendido |
| README / execução | Ferramentas, fonte, deploy, acesso, primeira carga, dashboard, operação e testes; comandos conferidos com scripts | Atendido |
| Estratégia documentada | Snapshot completo, staging, validação, publicação transacional, falhas e limites da POC | Atendido |
| Repositório ou ZIP | `delivery/banvic-projeto.zip` com infra, conectores, `dags/`, SQL, aplicação, testes, docs e evidências; CRC, conteúdo e segredos conferidos | Atendido |
| Apresentação final | `delivery/BanVic-Apresentacao-Certificacao.pptx`, dez slides revisados, quatro tabelas nativas e diagrama editável; `presentation-validation.json` | Atendido |
| Vídeo de 3–5 minutos | Entregável do enunciado | Fora desta revisão, conforme solicitado |

PostgreSQL satisfaz a alternativa de armazenamento; MinIO não precisa coexistir. Meltano satisfaz a alternativa de ingestão; Embulk não é obrigatório. Power BI e Databricks são exemplos no contexto, sem exigência de produto específico. O dashboard entregue é uma aplicação web própria conectada ao destino centralizado.

## Execuções e testes repetidos

| Execução | Resultado observado |
|---|---|
| `review3_20261005_retry` | Success; `load_contas` recuperou na tentativa 2; mesmos dados de negócio |
| `review3_20261005_failure` | Failed; `load_contas` falhou na tentativa 3; tratamento de falha funcionou; snapshot anterior intacto |
| `review3_20261005_sensor` | Sensor em reschedule com ZIP ausente, preparação não iniciada; fonte restaurada e execução concluída |
| `review3_20261005_invalid_zip` | Preparação rejeitou o arquivo em três tentativas, nenhuma carga iniciada; snapshot anterior intacto |
| `review3_20261005_final` | Success em 55,826 s, sem retries; fonte original restaurada e publicação validada |

Dois estados failed são resultados deliberados dos testes de resiliência. O ambiente terminou com a execução final bem-sucedida e a fonte oficial intacta.

| Verificação | Resultado |
|---|---|
| `bash scripts/test.sh --integration` | 7 testes de fonte + 3 de entrega + 5 de banco aprovados |
| `bash scripts/test_commercial.sh` | 15 testes comerciais, estatísticos e de sessão aprovados |
| Total de testes | **30 aprovados**, em `test-summary.json` |
| `python3 scripts/verify_commercial.py` | **10 grupos HTTP aprovados**, quatro exportações CSV com rastreabilidade, sem identificadores individuais |
| Configuração e código | DAG/ciclos/dependências, formatação Terraform, sintaxe shell/JavaScript e três planos sem diferenças aprovados |

## Reconciliação da fonte

| Tabela | Linhas na fonte e no destino | Todos os valores iguais |
|---|---:|---|
| agencias | 10 | Sim |
| clientes | 998 | Sim |
| colaborador_agencia | 100 | Sim |
| colaboradores | 100 | Sim |
| contas | 999 | Sim |
| propostas_credito | 2.000 | Sim |
| transacoes | 71.999 | Sim |
| **Total** | **76.206** | **Sim** |

SHA-256 da fonte: `646aada76645cab694741fa730d9792b40840c41823abb60bd7547a2038ba790`. Uma conta e quatro propostas sem cadastro de cliente são preservadas conforme a origem. As 78 transações ligadas à conta sem cadastro permanecem nos totais financeiros e são excluídas dos denominadores de clientes identificados.

## Contexto comercial

| Pedido de negócio | Situação |
|---|---|
| Dashboard comercial | Implementado: visão executiva, atividade/retenção, rede, crédito, alavancas e critérios/qualidade |
| Transações por cliente e atividade | Implementado; Q4/2022: 28.532 transações, 700 ativos de 998 elegíveis e 40,76 transações por ativo |
| Retenção, reativação e risco de churn | Continuidade e recência implementadas; inatividade não é apresentada como churn confirmado |
| Rede e crédito | Filtros, busca, comparações com denominadores e limites sobre status de proposta/desembolso |
| Ranking quantitativo | Prioridade de validação com estimativas ajustadas, intervalos, Holm, suporte, balanceamento e sensibilidade |
| Ranking causal / ROI garantido | **Não identificado pela fonte disponível**; API confirma zero efeitos identificados e lista causal vazia |
| Próximo trimestre | Protocolo com controle e planejador amostral; requer elegibilidade e dados atuais antes de executar o piloto |

Cartão, Pix e diversidade recebem prioridades exploratórias 1, 2 e 3; seus intervalos individuais de frequência incluem zero. Canal digital não recebe posição porque falha nos critérios de comparabilidade. Custos/margem não estão na fonte; movimentação bancária não equivale a receita ou ROI. Dezembro/2022 tem volume atípico de causa desconhecida e janeiro/2023 é parcial. Ver [METODOLOGIA_CAUSAL.md](METODOLOGIA_CAUSAL.md) e [RESULTADOS_COMERCIAIS.md](RESULTADOS_COMERCIAIS.md).

A revisão visual das seis telas e do login em desktop/celular foi realizada em 05/10 e está em `evidence/commercial/frontend-validation.json`. O frontend permaneceu igual nesta conferência, portanto essa evidência foi preservada. Nesta etapa, o navegador reconfirmou o sucesso da DAG, o novo snapshot consumido pelo painel e a rastreabilidade em Critérios e qualidade; ver `browser-check.json`.

## Ajustes e limites

A apresentação antiga citava 12 testes e tratava o dashboard como uma próxima etapa. A nova versão de dez slides atualiza testes, resultados comerciais e limites da inferência. Seu slide de Airflow identifica a captura anterior de 04/10 e apresenta separadamente a duração atual de 05/10. O README aponta para esta matriz; as revisões anteriores são identificadas como histórico.

O deploy a partir de ZIP extraído foi executado anteriormente; seus registros estão em `evidence/review/redeploy-clean-package.txt` e `clean-package-tests.txt`. Nesta etapa foram repetidos execução, testes, reconciliação e planos Terraform. Não houve reinstalação do Windows ou teste em outro computador, ensaio de produção/alta disponibilidade ou varredura completa de vulnerabilidades. Os slides foram renderizados e conferidos no runtime, sem teste de edição no PowerPoint. O grafo auxiliar antigo serviu somente para localizar arquivos; as conclusões vêm do código e das verificações atuais.

Os arquivos estão preparados para avaliação local. A submissão na plataforma e seus prazos dependem da inscrição do participante. Não houve processo de vídeo nesta revisão.

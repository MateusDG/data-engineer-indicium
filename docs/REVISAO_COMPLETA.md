# Revisão completa — BanVic

Revisão realizada em 04/10/2026, a pedido do usuário, confrontando a implementação e os arquivos de entrega com as etapas, critérios e entregáveis do enunciado. As conclusões abaixo se apoiam em inspeção de código, comandos executados no ambiente e novas execuções reais do Airflow.

## Conclusão

Os requisitos explícitos de infraestrutura, ingestão, orquestração, monitoramento básico, segurança, documentação e apresentação estão atendidos na POC local. O destino contém as sete tabelas e **76.206 registros**, reconciliados com a fonte oficial. **14 testes passaram**: sete de fonte, cinco de banco e dois de empacotamento. Não ficou pendência funcional identificada nesta revisão.

O contexto também descreve objetivos de dashboard comercial e ranking de impacto de investimentos. Esses produtos analíticos ainda não foram implementados; as etapas e entregas de engenharia listadas no enunciado exigem a plataforma e a ingestão. Existem três views para iniciar esse trabalho. Não foi produzido um ranking causal nem uma promessa de retorno estatisticamente garantido.

## Matriz de conformidade

| Requisito do enunciado | Implementação verificada | Resultado e evidência |
|---|---|---|
| Docker e containers | Duas imagens próprias, bases fixadas por digest, plugins dentro da imagem de ingestão | Atendido; Dockerfiles em `docker/`, construção e carga no Kind executadas no redeploy |
| Kubernetes local | Cluster Kind `banvic`, nó Ready, namespace, recursos e três PVCs Bound | Atendido; `evidence/pods.json` e saída do redeploy |
| Terraform / IaC | Etapas platform e airflow, provider lockfiles, chart Airflow fixado | Atendido; configurações válidas e reaplicação sem alterações nas duas etapas |
| Airflow e armazenamento no cluster | API, scheduler, dag processor e StatsD; PostgreSQL 16 com persistência | Atendido; pods prontos, sem reinicializações; `review/airflow-health.json` |
| ZIP oficial com sete tabelas | Contrato de arquivos, cabeçalhos, chaves, datas e números; snapshot congelado por execução | Atendido; SHA-256 original preservado, sete testes de fonte e teste real com ZIP inválido |
| Extração e carga com Meltano/Embulk | Meltano, tap-csv e target-postgres; sete tarefas em pods independentes | Atendido; carga real completa. Python valida e publica; a extração/carga usa os conectores exigidos |
| Configuração de taps e targets | Chaves declaradas, strings preservadas, upsert, full refresh, COPY e versões fixadas | Atendido; hashes de todos os valores e contagens conferem com a fonte |
| DAG, operadores e dependências | 13 tarefas, KubernetesPodOperator, sete loads antes da validação/publicação | Atendido; importação sem erros/ciclos, dependências conferidas e execuções reais |
| Agendamento e sensor | Diário às 06:00 em America/Sao_Paulo, catchup desativado, sensor reschedule | Atendido; sensor impediu cargas enquanto o ZIP estava ausente e retomou após sua chegada |
| Monitoramento básico | Interface e logs persistentes do Airflow, health endpoint, StatsD e audit no banco | Atendido; saúde de metadata, scheduler e dag processor; estados e tentativas registrados |
| Retries e tratamento de falhas | Duas tentativas adicionais, backoff, tarefa record_failure e folha de sucesso dependente da publicação | Atendido; falha transitória recuperada na tentativa 2; falha permanente após 3 tentativas manteve DAG failed |
| Idempotência e atomicidade | Staging por execução, publicação transacional de sete tabelas e marcador; republicação é noop | Atendido; hashes sem diferenças e rollback de todas as tabelas após erro na última tabela |
| Código limpo, modular e erros tratados | Módulos source/database/cli, contrato separado, DAG e infraestrutura separados | Atendido; testes de ZIP inseguro, schema, corrupção, retry, reconciliação e rollback |
| Segredos fora do código | Geração privada 700/600, Kubernetes Secrets via stdin, referências no IaC | Atendido; varredura das credenciais reais nos arquivos, no histórico Git e nos dois estados Terraform |
| Acesso de analistas | Conta própria de leitura, raw, analytics e indicadores de auditoria | Atendido; login e consultas reais; INSERT, CREATE em raw e acesso a airflow_metadata negados |
| Isolamento | UID não privilegiado, capabilities removidas, SA sem token, RBAC restrito e serviços ClusterIP | Atendido para a POC; scheduler cria pods, sem ler Secrets pela API; pipeline não cria pods |
| Repositório/ZIP com infraestrutura, ingestão e dags | Arquivos presentes no pacote; caches, fonte e arquivos sensíveis excluídos | Atendido; extração limpa usada para executar deploy e testes; dois testes de prevenção de vazamento |
| README com diagrama e execução | Mermaid, justificativas, fonte, instalação, deploy, execução, verificação e testes | Atendido; sequência de preparação corrigida durante esta revisão |
| Apresentação final | PPTX com oito slides, arquitetura, resultado, testes, segurança e reprodução | Atendido; hash igual ao arquivo final validado, XML/ZIP íntegros e renderização revisada |
| Vídeo de 3 a 5 minutos | 294,092 segundos, H.264/AAC, 1920×1080; deploy, Airflow Running/Success e consulta PostgreSQL | Atendido em conteúdo e duração; capturas reais editadas com narração sintética, formato explicado nos materiais |

Os caminhos de evidência `review/...` acima são relativos a `evidence/`.

## Novas execuções reais

| Execução | Resultado esperado e observado |
|---|---|
| `audit_20261004_success` | Sucesso; sete tabelas carregadas e publicadas |
| `audit_20261004_retry` | Sucesso; `load_contas` recuperou na tentativa 2 |
| `audit_20261004_failure` | Falha esperada após três tentativas; auditoria registrou falha e todas as tabelas e o marcador permaneceram iguais aos anteriores |
| `audit_20261004_sensor` | Sem ZIP, sensor ficou up_for_reschedule e a preparação não começou; com o ZIP restaurado, concluiu com sucesso |
| `audit_20261004_invalid_zip` | Falha esperada na preparação; nenhuma carga foi iniciada, auditoria registrou falha e o snapshot anterior permaneceu igual |
| `audit_20261004_final` | Sucesso sem retries; snapshot atual publicado, 76.206 linhas e os mesmos valores da fonte |

As duas falhas acima são testes controlados. Não foram apagadas do histórico. O arquivo original foi restaurado e seu SHA-256 permaneceu `646aada76645cab694741fa730d9792b40840c41823abb60bd7547a2038ba790`.

## Correções realizadas

1. O README chamava a checagem do ambiente sem listar a instalação dos conectores de diagnóstico e o download das imagens/chart usados por essa checagem. Os dois comandos foram acrescentados na ordem correta.
2. O empacotador foi restringido por tipos de arquivo e nomes sensíveis. Agora rejeita também `.env`, JSONs de credenciais, estados/planos Terraform com sufixos adicionais, dados CSV, ZIPs, symlinks e diretórios privados. Dois testes verificam que esses arquivos não entram e que o código e os lockfiles continuam presentes.

Nenhuma alteração no fluxo de ingestão foi necessária para os cenários funcionais desta revisão.

## Evidências da revisão

- `evidence/review-tests.txt`: 14 testes aprovados no projeto.
- `evidence/review/clean-package-tests.txt`: testes executados a partir da cópia extraída do ZIP, com a fonte oficial disponibilizada separadamente.
- `evidence/review/redeploy-clean-package.txt`: redeploy usando o código extraído do pacote, com zero alterações nas duas etapas Terraform.
- `evidence/review/dag-contract.txt`: dependências, agendamento, timezone, folha de erro/sucesso e segurança dos pods conferidos na imagem real do Airflow.
- `evidence/review/audit_20261004_*.json`: estados, tentativas e datas obtidos da API autenticada.
- `evidence/review/permanent-failure-preservation.json` e `invalid-zip-preservation.json`: contagens, hashes e marcador antes/depois, com igualdade integral.
- `evidence/review/sensor-waiting.json`: estado real enquanto a fonte estava ausente.
- `evidence/review/final-snapshot.json`: contagens e hashes do snapshot final.
- `evidence/review/analyst-access.json`: consultas e negações de acesso reais.
- `evidence/review/security.json`: varredura das credenciais reais, histórico Git, estados Terraform e RBAC.
- `evidence/review/source-restored.json`: hash original restaurado e permissões privadas.
- `evidence/review/artifacts.json`: hashes do PPTX/MP4, duração real e decodificação integral do vídeo.
- `evidence/review/airflow-final.png`: interface do Airflow mostrando a execução final desta revisão.

## Limites e contexto de negócio

- O teste de reprodução reaplicou o ZIP em um ambiente com WSL/Docker e ferramentas já instalados. Não corresponde a uma reinstalação completa do Windows, nem a um segundo cluster em outra máquina.
- A fonte contém cinco vínculos com cliente ausente: uma conta e quatro propostas. São avisos documentados, preservados sem perda de linhas; inconsistências introduzidas pela ingestão bloqueiam a publicação.
- A POC usa um nó, volumes locais, autenticação de desenvolvimento e monitoramento básico. Não foi validada como solução de produção, alta disponibilidade ou recuperação de desastre. As métricas internas não incluem alertas externos/Grafana.
- O vídeo é uma apresentação editada com capturas reais e voz sintética. O enunciado fornecido não determina voz própria nem gravação contínua. Caso existam regras adicionais na plataforma de envio, elas precisam ser consideradas na entrega.
- O PPTX foi verificado estruturalmente e por renderização; não houve teste de edição dentro do aplicativo Microsoft PowerPoint.
- O mapeamento auxiliar Graphify foi feito sobre uma cópia dos arquivos anteriores às correções. Possui referências externas/não resolvidas e agrupamentos de arestas; não foi usado como prova de funcionamento. As conclusões técnicas se apoiam no código e nas verificações executadas diretamente.
- A certificação e sua nota são avaliadas pela instituição. Esta matriz registra conformidade técnica observada, sem atribuir uma nota.

## Referências técnicas consultadas

[Estados de DAG Runs no Airflow](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dag-run.html), [sensores no Airflow](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/sensors.html) e [Meltano CLI/run](https://docs.meltano.com/reference/command-line-interface/#run). A inspeção local e os testes usaram as versões fixadas em `VERSOES.md`.

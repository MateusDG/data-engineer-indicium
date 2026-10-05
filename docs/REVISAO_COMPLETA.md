# Revisão completa — BanVic

**Conferência mais recente:** [REVISAO_FINAL_REQUISITOS.md](REVISAO_FINAL_REQUISITOS.md), realizada em 05/10/2026, com cinco cenários reais repetidos e apresentação atualizada. Este documento preserva a segunda revisão e seus números históricos.

**Atualização comercial em 05/10/2026 UTC:** dashboard, estimador de contrastes e ranking de prioridade foram implementados e implantados após esta revisão de engenharia. A validação atual passou em 30 testes e dez grupos de verificações da API, com nova ingestão `commercial_validation_20261005`. Consulte [DASHBOARD_COMERCIAL.md](DASHBOARD_COMERCIAL.md) e `evidence/commercial/`. Os resultados abaixo registram a revisão anterior, mantendo suas datas e contagens originais.

Segunda revisão realizada em **04/10/2026, à noite, em America/Sao_Paulo** (05/10/2026 UTC), confrontando código, documentação, pacote e ambiente real com os requisitos fornecidos. Conforme solicitado pelo usuário, **não houve gravação, narração, edição ou geração de vídeo nesta revisão**. Os materiais anteriores foram preservados.

## Conclusão

Os requisitos técnicos explícitos de infraestrutura, ingestão, orquestração, monitoramento básico, idempotência, segurança, código e documentação estão atendidos na **POC local verificada**. Uma nova execução completa do Airflow terminou com sucesso em **53,992 segundos**, sem retries. O destino contém as sete tabelas e **76.206 registros**, com todos os valores reconciliados novamente com o ZIP oficial. **14 testes passaram**: sete de fonte, cinco de banco e dois de empacotamento. As duas configurações Terraform são válidas e seus planos retornaram **zero diferenças** em relação ao ambiente.

A apresentação de oito slides já existe e sua integridade foi conferida novamente. O vídeo de três a cinco minutos continua exigido pelo enunciado, mas foi excluído da execução e da revalidação nesta etapa por solicitação do usuário. Portanto, esta conclusão de conformidade técnica não equivale a afirmar que o envio integral da certificação foi concluído.

Na data desta revisão anterior, o consumo analítico estava limitado a três views. A extensão posterior entregou o dashboard e o ranking quantitativo de prioridade para testes, com identificação causal explicitamente bloqueada pela ausência de intervenções e confundidores relevantes. Não há promessa de retorno estatisticamente garantido. A metodologia e os dados necessários para medir impacto estão em [METODOLOGIA_CAUSAL.md](METODOLOGIA_CAUSAL.md).

## Matriz de conformidade

| Requisito do enunciado | Implementação verificada | Resultado |
|---|---|---|
| Docker e containers | Duas imagens próprias; bases e dependências fixadas; conectores na imagem de ingestão | Atendido; imagens executadas e DAG importada na imagem real |
| Kubernetes local | Kind `banvic`, namespace e três volumes persistentes | Atendido; nó Ready, cinco componentes Running/Ready, zero reinicializações e três PVCs Bound |
| Terraform / IaC | Módulos platform e airflow, lockfiles, chart fixado | Atendido; validate aprovado e plan sem diferenças nos dois módulos |
| Airflow e armazenamento no cluster | API, scheduler, dag processor, StatsD e PostgreSQL 16 | Atendido; componentes e health endpoint saudáveis |
| Fonte oficial com sete tabelas | ZIP oficial, contrato de arquivos/colunas/chaves/tipos, snapshot por execução | Atendido; SHA-256 preservado, sete tabelas, testes de fonte aprovados |
| Extração e carga com Meltano ou Embulk | Meltano, tap-csv e target-postgres em sete tarefas independentes | Atendido; nova extração/carga real concluída. Python prepara, valida e publica |
| Configuração dos taps e targets | Chaves declaradas, strings preservadas, full refresh, upsert e COPY | Atendido; contagens e SHA-256 de todos os valores do destino iguais à fonte |
| DAG, operadores e dependências | 13 tarefas, KubernetesPodOperator, cargas antes da validação/publicação | Atendido; importação, dependências e execução real conferidas |
| Agendamento e sensor | Diário às 06:00 em America/Sao_Paulo, sem catchup, sensor reschedule | Atendido; configuração reconferida; teste real de arquivo ausente registrado na primeira revisão |
| Monitoramento básico | Interface/logs persistentes do Airflow, health endpoint, StatsD e audit no banco | Atendido; saúde, estados, tentativas e último snapshot consultados novamente |
| Retries e falhas | Duas tentativas adicionais, backoff, record_failure e folha de sucesso dependente da publicação | Atendido; código conferido e evidências anteriores de retry/falha permanente verificadas |
| Idempotência e atomicidade | Staging por execução, publicação transacional das sete tabelas e marcador; republicação noop | Atendido; testes de reconciliação, noop e rollback aprovados novamente; nova carga preservou todos os valores |
| Código modular e tratamento de erros | source/database/cli, contrato, SQL, DAG e infraestrutura separados | Atendido; testes de fonte, corrupção e publicação aprovados |
| Segredos fora do código | Credenciais privadas 700/600, Kubernetes Secrets via stdin, referências no IaC | Atendido; varredura das credenciais reais em arquivos, objetos Git e dois estados Terraform |
| Acesso centralizado para analistas | Usuário próprio de leitura, raw, analytics e indicadores audit | Atendido; login e três views consultados; INSERT, CREATE em raw e acesso ao metadata negados |
| Isolamento da POC | Pods sem privilégios, SA de ingestão sem token, RBAC restrito e serviços ClusterIP | Atendido; permissões e serviços verificados novamente; limites de rede documentados |
| Repositório ou ZIP com infra, ingestão e dags | Código, configurações, documentação e evidências públicas | Atendido; pacote atualizado e conferido, sem fonte, credenciais ou estado privado |
| README com diagrama, execução e estratégia | Mermaid, escolhas, preparação, deploy, execução, validação e testes | Atendido; scripts de preparação corrigidos para respeitar BANVIC_HOME |
| Apresentação final | PPTX existente com oito slides | Arquivo presente e íntegro; conteúdo/renderização revisados anteriormente, sem nova edição |
| Vídeo de três a cinco minutos | Requisito explícito da entrega da certificação | Fora desta revisão, conforme solicitado; nenhum processo de gravação ou geração executado |

Os caminhos de evidência abaixo são relativos à raiz do projeto. A avaliação e a nota pertencem à instituição; esta matriz não atribui nem garante uma nota.

## Verificações novas desta revisão

| Verificação | Resultado observado | Evidência |
|---|---|---|
| `bash scripts/test.sh --integration` | 7 + 2 + 5 testes aprovados; importação da DAG sem erros | `evidence/review2/tests.txt` |
| DAG `audit_20261004_second_review` | Success em 53,992 s; 12 tarefas concluídas na tentativa 1 e record_failure skipped | `evidence/review2/airflow-run.json` |
| Fonte versus raw | Todos os valores iguais em sete tabelas; 76.206 linhas | `evidence/review2/warehouse.json` |
| Fonte montada e permissões | SHA-256 igual ao ZIP original; credenciais 600 e diretório 700 | `evidence/review2/source-and-permissions.json` |
| Contrato da DAG na imagem | Dependências, horário/timezone, retries, folha de falha/sucesso e segurança conferidos | `evidence/review2/dag-contract.txt` |
| Terraform | Dois validate aprovados e dois plan com No changes | `evidence/review2/terraform-plan.txt` |
| Preparação em diretório alternativo | Download do chart e checagem respeitaram BANVIC_HOME; sintaxe Bash válida | `evidence/review2/environment.txt` |
| Saúde e persistência | Health saudável, nó Ready, cinco componentes prontos e três PVCs Bound | `evidence/review2/airflow-health.json`, `nodes.json`, `pods.json` e `pvc.json` |
| Acesso de analista | Views retornaram 71.999 transações e 2.000 propostas; operações proibidas negadas | `evidence/review2/analyst-access.json` |
| Segurança | Nenhuma credencial real nos arquivos, histórico Git ou estados Terraform; RBAC restrito | `evidence/review2/security.json` |
| Apresentação existente | ZIP/XML íntegros, oito slides, SHA-256 preservado | `evidence/review2/presentation-integrity.json` |
| Escopo da revisão | Nenhuma gravação ou geração de mídia executada | `evidence/review2/review-scope.json` |

## Evidências de resiliência da primeira revisão

Os cenários abaixo já foram executados no mesmo ambiente e código de ingestão. Suas evidências foram conferidas nesta revisão; **não foram provocadas novamente**. A correção atual afeta somente dois scripts de preparação, sem alterar imagens, DAG ou pipeline.

| Execução | Resultado registrado |
|---|---|
| `audit_20261004_success` | Sucesso, sete tabelas carregadas e publicadas |
| `audit_20261004_retry` | Sucesso, load_contas recuperou na tentativa 2 |
| `audit_20261004_failure` | Falha esperada após três tentativas; auditoria de falha; todas as tabelas e o marcador preservados |
| `audit_20261004_sensor` | Sem arquivo, sensor up_for_reschedule e preparação não iniciada; com o arquivo restaurado, sucesso |
| `audit_20261004_invalid_zip` | Preparação falhou; nenhuma carga iniciada; snapshot anterior preservado |
| `audit_20261004_final` | Sucesso; 76.206 linhas reconciliadas |

Estados e tentativas estão em `evidence/review/audit_20261004_*.json`. `permanent-failure-preservation.json` e `invalid-zip-preservation.json` registram contagens, hashes e marcador integralmente iguais antes/depois. `sensor-waiting.json` registra o sensor aguardando a fonte. A primeira revisão também executou deploy e testes a partir do ZIP extraído: `redeploy-clean-package.txt` e `clean-package-tests.txt`.

As falhas controladas e uma falha inicial de desenvolvimento permanecem no histórico do Airflow e da auditoria, com sua sequência registrada. O snapshot atual corresponde à nova execução bem-sucedida desta segunda revisão.

## Correções realizadas

1. **Nesta revisão:** `download_images.sh` e `check_environment.sh` usavam um caminho fixo para downloads, apesar de o README permitir BANVIC_HOME. Ambos passaram a carregar `common.sh` e respeitar o diretório configurado. A sequência foi executada com um diretório alternativo e concluiu corretamente.
2. **Nesta revisão:** README e matriz passaram a distinguir conformidade técnica, material de apresentação existente e vídeo excluído da atividade atual, sem eliminar o requisito do enunciado.
3. **Na revisão anterior:** o README recebeu os comandos de instalação dos conectores de diagnóstico e download usados pela checagem do ambiente.
4. **Na revisão anterior:** o empacotador foi restringido por tipos de arquivo e nomes sensíveis, com dois testes de prevenção de vazamento de credenciais, estado e fonte.

## Limites e contexto de negócio

- A fonte oficial contém cinco vínculos com cliente ausente: uma conta e quatro propostas. São avisos documentados, preservados sem perda de linhas; inconsistências introduzidas pela ingestão bloqueiam a publicação.
- A reprodução anterior usou WSL/Docker e ferramentas já instalados, no mesmo cluster. Não foi uma reinstalação completa do Windows nem um teste em outra máquina. A verificação atual reconfirmou o ambiente e os planos sem diferenças.
- A POC usa um nó, volumes locais, autenticação de desenvolvimento e monitoramento básico. Não foi validada como produção, alta disponibilidade ou recuperação de desastre. StatsD interno não inclui Grafana nem alertas externos.
- O código executa com Python 3.12 fixado nas imagens e nos testes. O Python 3.10 padrão do Ubuntu não é o runtime de validação da fonte; formatos de datas aceitos pelo Python 3.12 podem diferir.
- A apresentação foi conferida estruturalmente e renderizada anteriormente; não houve teste de edição no Microsoft PowerPoint. O vídeo existente não foi revalidado nesta etapa.
- A extensão posterior implementou o dashboard e o ranking de prioridade para validação. Inatividade é uma aproximação operacional; a fonte não confirma churn. Investimentos não têm efeito causal identificado, pois faltam registros de intervenção e confundidores relevantes.
- O mapeamento auxiliar Graphify registra arquivos anteriores às correções, com referências não resolvidas. Não é prova de funcionamento; as conclusões se apoiam no código, nas verificações atuais e nas evidências executadas.

## Referências técnicas consultadas anteriormente

[Estados de DAG Runs no Airflow](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dag-run.html), [sensores no Airflow](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/sensors.html) e [Meltano CLI/run](https://docs.meltano.com/reference/command-line-interface/#run). As verificações locais usaram as versões fixadas em `VERSOES.md`.

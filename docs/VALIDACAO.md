# Validação da solução

Validação inicial realizada em 04/10/2026 no ambiente local do usuário. A [revisão completa posterior](REVISAO_COMPLETA.md) acrescenta dois testes de empacotamento, novos cenários de execução e reprodução do deploy a partir do ZIP de entrega. Os arquivos em `evidence/` contêm contagens, hashes, estados e capturas reais, sem registros de clientes ou credenciais.

## Resultado

As sete tabelas do ZIP oficial chegaram ao schema raw com **76.206 linhas**. A reconciliação conferiu todos os valores de cada tabela, além de contagens e unicidade das chaves. A origem contém cinco vínculos com cliente ausente: uma conta e quatro propostas. O destino preserva esses registros e a auditoria sinaliza o problema da fonte.

| Verificação | Resultado |
|---|---|
| Fonte oficial e segurança do ZIP | 7 testes aprovados |
| Banco, reconciliação e atomicidade | 5 testes aprovados |
| Importação da DAG e suas dependências | 13 tarefas, sem erros de importação/ciclos |
| Terraform fmt e sintaxe Bash | Aprovados |
| Terraform redeploy | Sem alterações nas duas etapas |
| certification_demo | DAG success, 12 tarefas success, record_failure skipped |
| Primeira tentativa na execução final | Todas as tarefas executadas com try_number 1 |
| Duração observada da execução demo | 49,023 segundos |
| certification_retry | load_contas recuperou na segunda tentativa |
| certification_failure | DAG failed, load_contas falhou após 3 tentativas |
| Tratamento da falha permanente | Auditoria failed, pipeline_complete upstream_failed |
| Snapshot após a falha permanente | Permaneceu certification_retry |
| Reprocessamento do mesmo ZIP | Zero diferenças em contagens e hashes |
| Permissões do analista | SELECT permitido, INSERT e CREATE no raw negados |

O tempo medido é uma observação neste computador com imagens já carregadas. Não é um benchmark nem uma garantia de desempenho em outro ambiente.

## Testes de banco

1. Republicação de uma execução já publicada retorna `already_published` e não altera os dados.
2. O hash de cada tabela raw corresponde ao snapshot congelado da fonte.
3. Alterar um valor no staging impede passar pela validação.
4. Uma restrição de teste força erro na última tabela, depois de operações nas anteriores. O rollback preserva todas as tabelas e o marcador de snapshot.
5. As cinco relações ausentes são reportadas e todas as 71.999 transações permanecem no destino.

Os testes de corrupção e rollback usam SAVEPOINT. Suas alterações não permanecem no warehouse.

## Evidências

- `warehouse.json`: contagens, execuções, resultados por tabela e permissões.
- `warehouse-after-failure.json`: marcador e auditoria capturados depois da falha permanente, antes da execução final.
- `certification_*-tasks.json`: estados e números de tentativa obtidos pela API autenticada do Airflow.
- `deploy.txt`: saída do redeploy completo, com Terraform sem alterações e pods prontos.
- `verification.txt`: consulta real das contagens e auditoria.
- `airflow-running.png` e `airflow-video-success.png`: a mesma execução `certification_video` em andamento e concluída.
- `airflow-success-overview.png`: execução `certification_demo` com duração e estado final.

A auditoria também preserva a execução inicial de desenvolvimento que falhou antes de concluir o ajuste do ambiente Meltano. As execuções finais comprovam a configuração corrigida. Não foram apagadas falhas para produzir um histórico artificialmente perfeito.

## Limites da verificação

Os testes ocorreram neste cluster Kind e nesta versão da fonte. Não houve teste em nuvem, alta disponibilidade, recuperação de desastre ou volume de produção. O dashboard e a análise causal mencionados no contexto de negócio não integram os entregáveis de engenharia listados no desafio.

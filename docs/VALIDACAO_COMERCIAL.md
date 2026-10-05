# Validação da extensão comercial

Verificações realizadas em **05/10/2026 UTC**, no ambiente WSL/Docker/Kind da POC. A aplicação foi implantada com o Dockerfile e os módulos Terraform entregues. As evidências estão em `evidence/commercial/`.

| Verificação | Resultado | Evidência |
|---|---|---|
| Nova ingestão completa | `commercial_validation_20261005` com sucesso em 54,516 s; 12 tarefas de negócio na primeira tentativa | `airflow-run.json` |
| Reconciliação integral | 76.206 linhas das sete tabelas, com todos os digests de valores iguais à fonte | `warehouse-validation.json` |
| Atualização agendada | Execução diária posterior concluída; marcador e painel passaram para o novo run ID, com a mesma fonte | `latest-airflow-run.json`, `metadata.json` |
| Views comerciais | 999 contas, 71.999 transações, 2.000 propostas, soma mensal de 71.999 transações | `commercial-views.json` |
| Fonte | Sete testes aprovados: contrato, tipos, datas, chaves, snapshot e segurança do ZIP | `test-summary.json` |
| Banco | Cinco testes de integração aprovados, incluindo republicação e rollback | `test-summary.json` |
| Entrega | Três testes aprovados, incluindo distribuição dos assets e exclusão de segredos, estado, fonte e node_modules | `test-summary.json` |
| Regras comerciais e inferência | 15 testes aprovados dentro da imagem com dependências fixadas | `test-summary.json` |
| Serviço HTTP | Dez grupos de verificações aprovados: autenticação, cobertura, reconciliação, filtros, escopos inválidos, identificação, planejamento, exportação e logout | `api-validation.json` |
| Infraestrutura | Seis componentes em execução, prontos; três módulos Terraform válidos e sem diferenças | `pods.json`, `terraform.json` |
| Segredos e permissões | Valores reais ausentes do projeto, histórico Git e três estados Terraform; serviço sem acesso a Secrets ou criação de pods | `security.json` |

**Total: 30 testes**, além das verificações HTTP, importação/ciclos da DAG, formatação Terraform, sintaxe de shell, reconciliação e revisão visual. Os resultados validam esta POC e esta fonte; não substituem ensaio de produção ou instalação em outro computador.

## Verificação no navegador

As seis áreas foram abertas na aplicação conectada ao warehouse. Foram conferidos busca e recorte de Recife, restauração dos filtros, crédito, coortes com células futuras ausentes, rastreabilidade, detalhes de balanceamento e sensibilidade e planejamento de piloto. O planejador exibiu 321 clientes por grupo para +20% em transações e 1.259 por grupo para +5 p.p. de atividade, conforme o cálculo da API.

O layout foi inspecionado em 1440 × 1000 e 390 × 844, com navegação móvel, tabelas contidas em áreas de rolagem e adaptação do gráfico de intervalos. As capturas são telas reais; não são imagens geradas ou simulações de interface. Não houve gravação de vídeo.

O teste HTTP conferiu conteúdo UTF-8/BOM, separador, quatro tipos de CSV, agregados, identificador de execução, ausência de identificadores de clientes e colunas de incerteza. A revisão de navegador é registrada em `browser-validation.json`, inclusive o resultado do download no navegador usado para o teste.

## Correções verificadas

- A cobertura histórica passou a considerar propostas e contas, além de transações: as 26 propostas anteriores à primeira transação não ficam fora de “Todo o histórico”.
- O planejamento respeita o mesmo canal/agência do estudo. Atividade de 100% não gera tamanho amostral para um ganho impossível.
- O rodapé usa o snapshot da resposta e a tela de qualidade renova seus metadados.
- A exportação identifica os p-valores de transações e atividade separadamente e inclui intervalos simultâneos e diagnósticos.
- O acesso local verifica os endpoints e restabelece encaminhamentos ainda vivos para pods antigos, sem encerrar processos alheios.
- Terraform ignora somente a anotação operacional `kubectl.kubernetes.io/restartedAt`; reiniciar o serviço não gera uma diferença permanente nesse campo.

O grafo auxiliar anterior foi usado apenas para localizar o vínculo entre views e publicação. Vocabulário da consulta: `analytics, views, warehouse, publication, credentials`; limite da consulta: 1.700 tokens. O custo real em tokens não foi disponibilizado. O grafo é parcial e anterior à extensão; as conclusões de funcionamento se apoiam nas verificações atuais.

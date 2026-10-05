# Leitura comercial da carteira

Referência: **1 de outubro a 31 de dezembro de 2022**, último trimestre completo do ERP. Os resultados são históricos. A carga do projeto não atualiza a situação comercial do banco para 2026.

## Atividade e continuidade

| Indicador | Resultado |
|---|---:|
| Transações | 28.532 |
| Clientes ativos | 700 |
| Clientes elegíveis | 998 |
| Transações por cliente ativo no trimestre | 40,76 |
| Atividade da carteira | 70,1% |
| Movimentação bruta | R$ 20.124.786,83 |
| Continuidade dos ativos do período anterior | 427 de 467; 91,4% |
| Clientes reativados | 232 |
| Contas abertas no recorte | 43 |
| Inativos há mais de 90 dias, com conta madura | 291 |
| Clientes em atenção/risco, 31–90 dias | 32 |
| Clientes sem transação observada | 8 |

A frequência subiu no trimestre, mas **25.319 das 28.532 transações ocorreram em dezembro**. Esse mês registra 21,87 vezes a mediana dos seis anteriores. O ERP não informa se houve campanha, mudança operacional ou diferença de cobertura. A elevação não pode ser atribuída a uma ação comercial. Janeiro/2023 termina no dia 15 e não oferece comparação mensal completa.

Movimentação bruta mede fluxo e pode contar os dois lados de operações. Não é receita nem retorno de investimento. Continuidade mede atividade observada, não permanência contratual. Inatividade orienta investigação; não confirma churn.

## Agenda comercial proposta

| Frente | Evidência disponível | Próxima decisão |
|---|---|---|
| Ativação do cartão | Primeira prioridade exploratória; diferença ajustada de +1,13 transações/cliente/mês, com IC incluindo zero | Verificar elegibilidade e disponibilidade; desenhar piloto com controle |
| Onboarding do Pix | Segunda prioridade; +0,92, com IC incluindo zero | Testar orientação de uso para não usuários elegíveis |
| Ampliação do relacionamento | Terceira prioridade; +0,40, com IC incluindo zero | Investigar quais serviços atendem à necessidade real do cliente antes de definir a oferta |
| Recuperação de atividade | 32 clientes entre 31–90 dias e 291 inativos em contas maduras | Separar segmentos, atualizar os dados e testar contatos com controle e custo registrado |
| Comparação digital/físico | Uma agência digital, sobreposição insuficiente e desequilíbrio de perfis | Não usar a diferença como justificativa causal para migrar clientes ou orçamento |
| Crédito e marketing | Datas de desembolso, intervenção, custos e margem ausentes | Incorporar esses registros antes de medir impacto ou ROI |

A ordem de cartão, Pix e diversidade é uma ordem de **validação** baseada em critérios declarados. Não equivale a três investimentos aprovados. As ações sugeridas ainda precisam de um tratamento definido e de elegibilidade atual; a presença de um comportamento passado não estima automaticamente o efeito de promovê-lo.

## Uso pela diretoria

Use a visão executiva para acompanhar atividade e verificar a concentração do volume. Na rede, compare frequência e atividade com seus denominadores; valores absolutos favorecem agências com carteiras maiores. Na área de retenção, escolha um segmento para um piloto mensurável. Na área de crédito, leia o status das propostas recebidas sem tratá-lo como um funil acompanhado ou como carteira desembolsada.

Na tela de alavancas, abra as evidências de cada contraste antes de priorizar o piloto. O planejador mostra se a amostra histórica comporta o efeito mínimo escolhido. A decisão final deve incorporar custo, margem, capacidade de execução e dados recentes. A [metodologia](METODOLOGIA_CAUSAL.md) explicita as hipóteses, os intervalos e os dados adicionais necessários.

## Rastreabilidade

Os JSONs em `evidence/commercial/` foram obtidos pela API do serviço implantado. `metadata.json` identifica execução, SHA-256 da fonte e cobertura; `dashboard-default.json` contém os indicadores deste recorte; `ranking.json` inclui diagnósticos e intervalos; `api-validation.json` registra as verificações. O verificador `scripts/verify_commercial.py` permite repetir a conferência com a mesma fonte oficial.

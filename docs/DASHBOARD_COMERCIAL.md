# Dashboard comercial BanVic

Aplicação conectada ao PostgreSQL da POC, com seis áreas de análise e exportação de agregados. A interface funciona no navegador e não exige licença de BI. Os arquivos de gráficos, estilos e fontes do sistema são servidos localmente. O warehouse continua disponível para Power BI e clientes SQL.

## Implantação

Execute no Ubuntu/WSL, a partir da raiz do projeto. Docker deve estar aberto e integrado ao Ubuntu. Em outro computador, primeiro siga a instalação do README e disponibilize o ZIP oficial.

```bash
bash scripts/deploy.sh
bash scripts/access.sh
bash scripts/run_pipeline.sh
bash scripts/deploy_commercial.sh
bash scripts/access.sh
```

A ingestão precisa publicar um snapshot antes da implantação comercial. A readiness do serviço verifica essa disponibilidade; uma fonte ausente não é substituída por dados de demonstração. O deploy comercial cria as views, constrói a imagem, carrega-a no Kind e aplica o terceiro módulo Terraform. Repetir o comando conserva as credenciais, atualiza a imagem e reinicia o Deployment.

Abra **http://localhost:8090**, com usuário **`comercial`**. A senha fica no campo **`dashboard_admin`** de `~/banvic-local/secrets/credentials.json`. Consulte esse arquivo somente localmente; ele não acompanha o código. As sessões duram oito horas, com cookie assinado, HttpOnly e SameSite Strict. O acesso é local por port-forward em 127.0.0.1. A configuração `DASHBOARD_SECURE_COOKIE=true` é destinada a um futuro acesso por HTTPS.

Se utilizar `BANVIC_HOME`, mantenha a mesma variável em todos os comandos. Não mova os diretórios montados depois de criar o cluster.

## Áreas de análise

| Área | Pergunta atendida | Conteúdo |
|---|---|---|
| Visão executiva | Como está a movimentação da carteira? | Clientes ativos, frequência, volume bruto, evolução mensal, modalidades e continuidade |
| Atividade e retenção | Onde concentrar atenção comercial? | Recência, inatividade, reativação, novos clientes, coortes M0–M6 e segmentos para pilotos |
| Rede de agências | Como comparar canais e unidades? | Frequência por cliente elegível, tabela das dez agências, busca e navegação para uma unidade |
| Crédito | Como se distribuem as propostas recebidas? | Quantidade, valores solicitados e status atual das propostas que entraram no período |
| Alavancas comerciais | Quais hipóteses merecem validação? | Contrastes ajustados, intervalos, diagnósticos, prioridade exploratória e dimensionamento de experimento |
| Critérios e qualidade | De onde vêm os números? | Dicionário de indicadores, cobertura, inconsistências e identificador/hash do snapshot |

Filtros de canal e agência se aplicam a toda a análise. Períodos disponíveis: último trimestre completo, último mês completo, últimos doze meses completos, todo o histórico e datas personalizadas. As alavancas usam os oito últimos trimestres completos, com janelas anteriores para ajuste e exposição. **Aplicar filtros** executa o recorte; **Limpar** restaura o padrão. A busca da rede procura nome, cidade e estado na tabela do recorte.

O botão **Exportar CSV** fornece evolução mensal, agências, status de crédito ou evidências, conforme a tela. O arquivo usa UTF-8 com BOM, separador `;` e ponto decimal nos campos numéricos, com período e execução de origem. Textos que poderiam iniciar fórmulas de planilha são escapados. As exportações contêm agregados; não contêm nomes, documentos ou identificadores individuais.

## Definições de negócio

| Indicador | Regra |
|---|---|
| Cliente elegível | Cadastro identificado e conta aberta até o final do recorte |
| Cliente ativo | Cliente identificado com ao menos uma transação no recorte |
| Transações por ativo | Transações de clientes identificados ÷ clientes ativos no mesmo recorte |
| Atividade da carteira | Clientes ativos ÷ elegíveis |
| Movimentação bruta | Soma dos valores absolutos das transações; não é receita, margem ou patrimônio |
| Movimentação líquida | Soma dos valores com seus sinais; não é lucro |
| Comparação anterior | Intervalo imediatamente anterior com a mesma quantidade de dias |
| Continuidade | Ativos em ambos os períodos ÷ ativos no período anterior |
| Ativo em 90 dias | Transação em `(fim − 90 dias, fim]` |
| Segmento de recência | Sem transação; 0–30, 31–60, 61–90 ou mais de 90 dias desde a última transação |
| Inatividade de 90 dias | Conta aberta há pelo menos 90 dias, com cadastro identificado e sem transação ou última transação há mais de 90 dias |
| Reativado | Ativo no recorte, com histórico anterior e nenhuma transação nos 90 dias imediatamente anteriores ao início |
| Novo cliente | Abertura de conta dentro do recorte |
| Coorte | Mês da primeira transação observada no histórico; não necessariamente mês de aquisição |
| Retenção da coorte | Membros com transação em M0…M6 ÷ membros da coorte; meses futuros vazios, parciais marcados |
| Crédito | Status atual das propostas cuja data de entrada está no recorte; não mede desembolso ou tempo de aprovação |

As datas de transação são normalizadas em UTC. A data de referência é o final do recorte histórico. A fonte termina em 15/01/2023: o padrão é outubro–dezembro de 2022, e a interface identifica janeiro como parcial. Data de publicação em 2026 não transforma esses registros em uma carteira atual.

A conta sem cliente correspondente e suas 78 transações permanecem nos totais de movimentação. São excluídas das métricas que exigem cliente identificado. As quatro propostas sem cadastro permanecem no total geral de crédito; recortes de agência/canal usam o vínculo da conta quando disponível. Não se criam cadastros para preencher a fonte.

## Consumo, atualização e manutenção

O backend lê `audit.current_snapshot` e as views `analytics.commercial_accounts`, `commercial_transactions` e `commercial_credit` dentro de uma transação **REPEATABLE READ, READ ONLY**. A view `commercial_monthly` também oferece agregados para SQL/BI. O cliente PostgreSQL usa a conta `banvic_analyst`, sem permissão de escrita. Dados individuais usados no cálculo ficam no servidor.

O serviço verifica o marcador a cada 30 segundos e recarrega o conjunto quando o run ID muda. O cache de análises inclui esse identificador. Ao aplicar filtros ou trocar de tela após uma nova publicação, o rodapé identifica a execução efetivamente usada na resposta. A tela de qualidade consulta novamente os metadados. Não há atualização automática de uma tela deixada aberta.

Para atualizar a aplicação, execute `bash scripts/deploy_commercial.sh` e depois `bash scripts/access.sh`. O script de acesso restabelece o port-forward quando o pod anterior encerra. Atualize o navegador para carregar os novos arquivos estáticos.

As dependências Python estão fixadas com hashes em `commercial/requirements.lock`. ECharts está incluído em `static/vendor`, com licença. Node não é necessário para executar o pacote entregue. Para atualizar deliberadamente o gráfico, use Node/npm na pasta `commercial`:

```bash
npm ci
npm run vendor
```

Preserve e revise os arquivos de lock. O container usa usuário 1000, filesystem somente de leitura, capabilities removidas, limites de recursos e service account sem token. O serviço não recebe permissões de administração do Kubernetes.

## Verificação

```bash
bash scripts/test.sh --integration
bash scripts/test_commercial.sh
python3 scripts/verify_commercial.py --evidence-dir evidence/commercial
```

O verificador HTTP exige a fonte oficial desta certificação: reconcilia totais, identifica propostas anteriores à primeira transação, valida filtros, autenticação, datas inválidas, ausência de identificadores individuais, quatro exportações, ranking e planejamento. Ele lê a senha do diretório privado e não a imprime. As evidências públicas registram agregados e o run ID.

Para indisponibilidade, consulte `kubectl -n banvic get pods`, `kubectl -n banvic logs deployment/banvic-commercial` e `/health/ready`. Confirme primeiro o último snapshot publicado e a disponibilidade do PostgreSQL. A ausência de dados gera erro de disponibilidade, sem números fictícios.

Os resultados e as decisões comerciais estão em [RESULTADOS_COMERCIAIS.md](RESULTADOS_COMERCIAIS.md); a interpretação estatística e o desenho de validação estão em [METODOLOGIA_CAUSAL.md](METODOLOGIA_CAUSAL.md).

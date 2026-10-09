# Roteiro de gravação — vídeo de demonstração BanVic

Meta: **entre 4min30 e 5min**, gravado com a sua voz, mostrando o pipeline rodando de verdade. A banca avalia infraestrutura, ingestão, orquestração, qualidade do código, segurança e a clareza da apresentação. O roteiro cobre todos esses pontos, na ordem.

O roteiro tem três partes:

1. **Preparação**, sem gravar, cerca de 40 minutos antes.
2. **Gravação**, cena por cena: o que abrir, o que fazer e o que falar.
3. **Depois de gravar**: edição, entrega e o que fazer se algo der errado.

---

## Parte 1 — Preparação (não gravar)

Se ainda não sabe operar a plataforma, pratique antes com o [guia prático de uso](GUIA_DE_USO.md). Ele explica cada peça e cada tela.

### 1.1 Subir o ambiente

Abra o Docker Desktop e espere ficar "Running". Depois abra o **Ubuntu (WSL)** e rode:

```bash
cd /mnt/c/Users/mateu/Desktop/data-engineer-indicium
export KUBECONFIG="$HOME/banvic-local/kubeconfig"
bash scripts/access.sh
```

- `access.sh` abre as portas locais: Airflow em `localhost:8080`, dashboard em `localhost:8090` e PostgreSQL em `localhost:5433`.
- Se o computador foi reiniciado, ele primeiro reconecta os volumes do cluster. Isso leva 1–2 minutos.
- Só rode `bash scripts/deploy.sh` (pipeline/Airflow) ou `bash scripts/deploy_commercial.sh` (dashboard) se o código correspondente tiver mudado.

Confira se todos os pods estão `Running` e prontos:

```bash
kubectl -n banvic get pods
```

### 1.2 Rodar antes o cenário de falha e retry

Rode este cenário antes da gravação. Assim, no vídeo você só mostra o resultado, sem esperar.

```bash
bash scripts/run_pipeline.sh video_retry --fail-once contas
```

- A carga de `contas` falha de propósito na 1ª tentativa e conclui na 2ª.
- Ao final, o script já roda o `verify.sh`.
- Se repetir o ensaio, use outro nome (`video_retry2`), porque cada run ID só pode ser usado uma vez.

Opcional: rode também uma execução normal de ensaio, para medir o tempo:

```bash
bash scripts/run_pipeline.sh ensaio_1
```

### 1.3 Testar o comando do Terraform (opcional, mas recomendado)

Se este teste mostrar **"No changes"**, use-o na Cena 3. Ele é a melhor prova de infraestrutura como código.

```bash
export TF_VAR_kubeconfig_path="$KUBECONFIG"
export TF_DATA_DIR="$HOME/banvic-local/terraform/platform/provider-cache"
terraform -chdir=infra/platform plan
```

Se der erro ou mostrar alterações, não use na gravação. O slide 3 já mostra o "No changes" do deploy.

### 1.4 Pegar as senhas e fazer login (fora da gravação)

```bash
python3 -c "import json,os; d=json.load(open(os.path.expanduser('~/banvic-local/secrets/credentials.json'))); print('Airflow:', d['airflow_admin']); print('Dashboard:', d['dashboard_admin'])"
```

1. Faça login no **Airflow**: http://localhost:8080, usuário `admin`.
2. Faça login no **dashboard**: http://localhost:8090, usuário `comercial`.
3. Rode `clear` no terminal. **As senhas não podem aparecer no vídeo.**

### 1.5 Deixar as janelas prontas, nesta ordem

| # | Janela | Como deixar |
|---|---|---|
| 1 | PowerPoint | `delivery/BanVic-Apresentacao-Certificacao.pptx` em modo apresentação, no slide 1 |
| 2 | Navegador, aba **GitHub** | README do repositório (o diagrama Mermaid aparece renderizado) |
| 3 | Terminal Ubuntu | Fonte grande (16+), `KUBECONFIG` exportado, tela limpa |
| 4 | VS Code | Abas abertas: `dags/banvic_ingestion.py` e `meltano/meltano.yml` |
| 5 | Navegador, aba **Airflow** | Página da DAG `banvic_ingestion`, já logado |
| 6 | Navegador, aba **Dashboard** | Tela "Visão executiva", já logado |

### 1.6 Checklist antes de apertar REC

- [ ] Resolução 1920×1080. Zoom do navegador em 100–110%.
- [ ] Modo "Não perturbe" do Windows ligado. Slack, e-mail e WhatsApp fechados.
- [ ] Nenhuma janela mostrando `credentials.json`, senhas ou `kubectl get secret`.
- [ ] Microfone testado: grave 10 segundos e ouça.
- [ ] Gravador pronto: **OBS Studio** (grátis) ou **Win + Alt + R** (Xbox Game Bar).
- [ ] Um ensaio completo feito com cronômetro.

---

## Parte 2 — Gravação, cena por cena

Os textos entre aspas são sugestões de fala. Leia em voz alta no ensaio e adapte ao seu jeito de falar. Não precisa decorar.

### Cena 1 — Abertura · 0:00–0:25

**Tela:** PowerPoint, slide 1.

**Fala:**
> "Olá, eu sou [seu nome]. Este é o meu projeto da certificação Data Engineer da Indicium: uma prova de conceito para o BanVic, o Banco Vitória. Hoje as análises do banco são feitas em planilhas. O objetivo é centralizar os dados do ERP com uma ingestão automatizada, orquestrada e reprodutível. Vou mostrar a arquitetura, o código e o pipeline rodando de verdade."

### Cena 2 — Arquitetura e estratégia · 0:25–1:10

**Tela:** slide 2 (diagrama da arquitetura). Aponte as etapas com o mouse enquanto fala.

**Fala:**
> "A fonte é o arquivo banvic_data.zip, com as sete tabelas do ERP, simulando um sistema legado. Como ele é uma exportação completa, sem data de alteração, a estratégia é snapshot completo, ou full refresh, e não carga incremental.
>
> Tudo roda num Kubernetes local, com Kind. O Terraform cria o namespace, os volumes, o PostgreSQL e as permissões, e também instala o Airflow pelo chart oficial do Helm.
>
> O fluxo: um sensor do Airflow espera o ZIP. A preparação congela uma cópia imutável para cada execução e valida colunas, tipos e chaves. Depois, sete cargas do Meltano, com tap-csv e target-postgres, rodam em pods separados e gravam num schema de staging exclusivo daquela execução. A validação compara contagens e hashes de todos os valores com a origem. Só então uma única transação publica as sete tabelas. Os analistas consomem views prontas, com um usuário somente leitura."

### Cena 3 — Infraestrutura rodando · 1:10–1:40

**Tela:** terminal.

**Ação:** digite

```bash
kubectl -n banvic get pods
kubectl -n banvic get pvc
```

Se o teste da etapa 1.3 deu certo, rode também `terraform -chdir=infra/platform plan` e mostre o "No changes".

**Fala:**
> "Este é o ambiente no ar. No namespace banvic estão o PostgreSQL, os componentes do Airflow — API, scheduler e processador de DAGs —, o StatsD para métricas e o dashboard. Os dados ficam em três volumes persistentes: dados, banco e logs. Tudo sobe com um comando, o deploy.sh, que cria o cluster, constrói as imagens Docker e aplica o Terraform. Rodar de novo não recria nada: o Terraform responde 'No changes'."

### Cena 4 — Código da DAG e do Meltano · 1:40–2:25

**Tela:** VS Code, `dags/banvic_ingestion.py`.

**Ação:** role devagar e pare nestes trechos:

1. Linhas 24–31: `schedule`, `catchup`, `max_active_runs` e `retries`.
2. Linha 38: o sensor com `mode="reschedule"`.
3. Linhas 45 e 55: o `KubernetesPodOperator` e o `env_from` com o Secret.
4. Linhas 82–83: as dependências.

**Fala:**
> "Esta é a DAG. Ela roda todo dia às seis da manhã, no horário de São Paulo, sem catchup e com uma execução por vez. Cada tarefa tem duas novas tentativas, com espera crescente. O sensor verifica o ZIP em modo reschedule, então não prende um worker enquanto espera.
>
> Cada etapa usa o KubernetesPodOperator: sobe um container isolado com o Meltano, e as credenciais entram por um Secret do Kubernetes. Não há nenhuma senha no código.
>
> Aqui embaixo, as dependências: sensor, preparação, as sete cargas em paralelo, validação e publicação. A tarefa record_failure só dispara se algo falhar, e registra a falha na auditoria."

**Ação:** troque para a aba `meltano/meltano.yml`.

**Fala:**
> "E esta é a configuração do Meltano: extractor tap-csv e loader target-postgres, com versões fixadas. A senha é marcada como sensível e só é injetada em tempo de execução."

### Cena 5 — Pipeline rodando ao vivo · 2:25–3:15

**Tela:** navegador, aba Airflow, página da DAG `banvic_ingestion`.

**Ação:**

1. Clique em **Trigger**. Deixe os parâmetros vazios e confirme.
2. Abra a execução que apareceu e mude para a visão **Graph** (grafo).
3. Fale enquanto as tarefas mudam de cor.

**Fala, durante a execução:**
> "Agora, o pipeline rodando de verdade. Disparei a DAG manualmente. O sensor encontrou o arquivo, a preparação congelou o snapshot e as cargas começam, até quatro ao mesmo tempo. Cada uma dessas tarefas é um pod no Kubernetes executando o Meltano."

**CORTE:** pare de gravar, ou corte na edição, até a execução terminar. Isso leva cerca de 1 minuto.

**Ação depois do corte:** mostre todas as tarefas verdes. Clique em `load_transacoes` e depois em **Logs**.

**Fala:**
> "Execução concluída com sucesso, em menos de um minuto. A record_failure ficou como skipped, porque não houve erro. No log da carga de transações dá para ver o Meltano rodando o tap-csv e o target-postgres."

### Cena 6 — Resiliência · 3:15–3:40

**Tela:** Airflow. Abra a execução `video_retry`, que você rodou na preparação, e clique na tarefa `load_contas` para mostrar as 2 tentativas.

**Fala:**
> "Este é um teste de resiliência que rodei antes. Simulei uma falha na carga de contas: a tarefa falhou na primeira tentativa, o Airflow aplicou o retry e ela concluiu na segunda, sem duplicar dados. Também testei uma falha permanente. Nesse caso a DAG termina como failed, e os dados publicados antes continuam intactos, porque a publicação é atômica."

### Cena 7 — Dados no PostgreSQL · 3:40–4:05

**Tela:** terminal.

**Ação:** digite o comando abaixo e role até o início da saída, onde está a tabela de contagens.

```bash
bash scripts/verify.sh
```

**Fala:**
> "Conferindo no PostgreSQL: as sete tabelas somam 76.206 linhas, exatamente as da origem. Na auditoria, cada execução registra o status e o hash do arquivo, e o snapshot atual aponta para a última publicação. Rodar de novo o mesmo ZIP não duplica nada: o processo é idempotente."

### Cena 8 — Consumo pela área comercial · 4:05–4:35

**Tela:** navegador, aba Dashboard, tela **Visão executiva**.

**Fala:**
> "Com os dados centralizados, a área comercial consome tudo por este dashboard. Ele lê o banco com usuário somente leitura e não envia dados pessoais ao navegador. Aqui estão os clientes ativos e as transações por cliente, que são o objetivo da diretoria comercial."

**Ação:** clique em **Alavancas comerciais** no menu lateral. Mostre o bloco "Onde testar primeiro".

**Fala:**
> "E aqui a resposta para a CEO: o uso de cartão de crédito, de Pix e o relacionamento com várias modalidades são o que mais acompanha clientes ativos. Os dados do ERP mostram associação, não causa. Por isso o painel já dimensiona um piloto com grupo de controle para o próximo trimestre."

### Cena 9 — Encerramento · 4:35–5:00

**Tela:** navegador, aba GitHub, com o README e o diagrama. Role devagar até "Subir o ambiente".

**Fala:**
> "Toda a documentação está no README: o diagrama, o passo a passo para subir o ambiente e a estratégia de ingestão. Resumindo: infraestrutura como código em Kubernetes, ingestão com Meltano, orquestração com retries e idempotência, credenciais apenas em Secrets e tudo reprodutível. Para produção, os próximos passos seriam login corporativo, TLS, backup e alertas. Obrigado!"

---

## Parte 3 — Depois de gravar

### Edição

- Corte as esperas: o pipeline rodando e trocas lentas de janela. Para ser transparente, escreva "tempo acelerado" na tela durante o corte.
- Se passou de 5 minutos, encurte primeiro a Cena 6, depois a parte do Meltano na Cena 4.
- Exporte em MP4, 1080p.

### O que nunca pode aparecer

- O arquivo `~/banvic-local/secrets/credentials.json` ou qualquer senha.
- `kubectl get secret ... -o yaml` ou `env` dentro de pods.
- Consultas em `raw.clientes` ou `raw.colaboradores`, que têm nomes, CPF e e-mail. O `verify.sh` mostra só contagens e é seguro.

### Se algo der errado durante a gravação

| Problema | O que fazer |
|---|---|
| Airflow ou dashboard não abre | `bash scripts/access.sh` |
| Pod fora de `Running` | `kubectl -n banvic get pods -w` e espere ficar pronto |
| Execução falhou ao vivo | Pare, veja o log da tarefa vermelha, corrija e grave a cena de novo com nova execução |
| Botão Trigger não executa | Confirme que a DAG não está pausada (botão de ativar ao lado do nome) |

### Entrega

1. Faça commit e push das alterações. O README do GitHub é o que a banca vê.
2. Gere o pacote de código: `python3 scripts/package_delivery.py`.
3. Envie na plataforma:
   - o link do repositório ou `delivery/banvic-projeto.zip`;
   - `delivery/BanVic-Apresentacao-Certificacao.pptx`;
   - o vídeo.

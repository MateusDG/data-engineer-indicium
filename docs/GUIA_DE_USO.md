# Guia prático de uso da plataforma BanVic

Este guia mostra, do zero, como **ligar, operar e demonstrar** a plataforma. Ele cobre Docker, Kubernetes, Terraform, Airflow, DAG, Meltano, PostgreSQL e o dashboard. Siga na ordem na primeira vez. Depois, a [seção 9](#9-cola-para-a-demonstração) serve de resumo rápido.

> Todos os comandos são digitados no **terminal do Ubuntu**. Para colar um comando no terminal, clique com o botão direito do mouse ou use **Ctrl + Shift + V**.

---

## 1. Entenda as peças

| Peça | O que é, em uma frase | Onde você vê |
|---|---|---|
| **Docker Desktop** | Motor que executa os containers, como pequenos computadores isolados | Ícone da baleia no Windows |
| **Ubuntu (WSL)** | Linux dentro do Windows; é onde você digita os comandos | Menu Iniciar → "Ubuntu 22.04" |
| **Kubernetes (Kind)** | Um mini data center local. Cada serviço roda em um **pod** | Comando `kubectl` |
| **Terraform** | Cria a infraestrutura a partir de código (pasta `infra/`) | Executado pelo `deploy.sh` |
| **PostgreSQL** | O banco central (data warehouse) | Pod `postgres-0`, porta 5433 |
| **Meltano** | Ferramenta de ingestão: o `tap-csv` lê os CSVs do ZIP e o `target-postgres` grava no banco | Arquivo `meltano/meltano.yml` e logs das tarefas `load_*` |
| **Airflow** | Orquestrador: executa as etapas na ordem certa, com tentativas automáticas | http://localhost:8080 |
| **DAG** | O "fluxograma" do Airflow, escrito em Python | `dags/banvic_ingestion.py` |
| **Dashboard** | Painel da área comercial, que lê o banco | http://localhost:8090 |

**O caminho do dado:**

```
banvic_data.zip → Airflow (DAG) → pods com Meltano → PostgreSQL (staging → validação → raw) → views analytics → dashboard
```

---

## 2. Ligar tudo (toda vez que ligar o computador)

1. Abra o **Docker Desktop** e espere aparecer **"Engine running"**, embaixo à esquerda.
2. Abra o **Ubuntu**: Menu Iniciar → digite `Ubuntu` → **Ubuntu 22.04**. A janela preta é o terminal.
3. Entre na pasta do projeto:

   ```bash
   cd /mnt/c/Users/mateu/Desktop/data-engineer-indicium
   ```

4. Conecte os serviços:

   ```bash
   bash scripts/access.sh
   ```

   - Se o computador foi reiniciado, o script primeiro **reconecta os volumes do cluster** e espera tudo ficar pronto. Isso leva 1–2 minutos.
   - No final ele mostra os endereços: Airflow `http://localhost:8080`, PostgreSQL `localhost:5433` e Dashboard `http://localhost:8090`.

5. Diga ao `kubectl` qual cluster usar. Faça isso em cada janela nova do terminal:

   ```bash
   export KUBECONFIG="$HOME/banvic-local/kubeconfig"
   ```

   Para não precisar repetir, rode **uma única vez**:

   ```bash
   echo 'export KUBECONFIG="$HOME/banvic-local/kubeconfig"' >> ~/.bashrc
   ```

> O `bash scripts/deploy.sh` (que cria o cluster, constrói as imagens e aplica o Terraform) só é necessário na **primeira instalação** ou quando o código do pipeline muda. No dia a dia, basta o `access.sh`.

---

## 3. Kubernetes: ver a infraestrutura rodando

### Ver os serviços (pods)

```bash
kubectl -n banvic get pods
```

Como ler: `-n banvic` significa "no namespace banvic", que é a "pasta" do projeto no cluster. Cada linha é um serviço:

| Pod | Função |
|---|---|
| `postgres-0` | Banco de dados (warehouse e metadados do Airflow) |
| `airflow-api-server-…` | Interface web e API do Airflow |
| `airflow-scheduler-0` | Decide quando cada tarefa roda e executa as tarefas |
| `airflow-dag-processor-…` | Lê o arquivo Python da DAG |
| `airflow-statsd-…` | Coleta métricas do Airflow |
| `banvic-commercial-…` | Dashboard comercial |

- **READY `1/1`** ou **`2/2`** significa pronto.
- **STATUS `Running`** significa rodando.

Se algo estiver diferente, veja a [seção 8](#8-problemas-comuns).

### Ver os volumes (onde os dados ficam guardados)

```bash
kubectl -n banvic get pvc
```

Os três volumes (`banvic-data`, `banvic-postgres` e `banvic-logs`) devem estar `Bound`. Eles ficam em `~/banvic-local`, fora do repositório, e **sobrevivem** a desligar o computador.

### Ver os pods do Meltano nascendo durante uma carga (ótimo para demonstrar)

Deixe este comando rodando em um terminal e dispare a DAG (seção 4):

```bash
kubectl -n banvic get pods -w
```

Aparecem pods como `banvic-load-transacoes-…`, um por tabela. Eles ficam `Running` e são apagados ao terminar: cada etapa é um container isolado. Aperte **Ctrl + C** para sair.

### Terraform: provar a infraestrutura como código

O código fica em `infra/platform/main.tf` (namespace, volumes, PostgreSQL e permissões) e `infra/airflow/` (instalação do Airflow pelo Helm). Para conferir que o ambiente bate com o código:

```bash
export TF_VAR_kubeconfig_path="$KUBECONFIG"
export TF_DATA_DIR="$HOME/banvic-local/terraform/platform/provider-cache"
terraform -chdir=infra/platform plan
```

A resposta esperada é **"No changes. Your infrastructure matches the configuration."**

---

## 4. Airflow e a DAG: executar o pipeline

### Entrar no Airflow

1. **Fora da gravação**, veja a senha:

   ```bash
   python3 -c "import json,os; print(json.load(open(os.path.expanduser('~/banvic-local/secrets/credentials.json')))['airflow_admin'])"
   ```

2. Abra **http://localhost:8080** no navegador. Usuário: `admin`. Senha: a do passo anterior. Depois rode `clear` no terminal para apagar a senha da tela.

### Encontrar a DAG

1. No menu da esquerda, clique em **Dags**.
2. Clique em **`banvic_ingestion`**.

O que tem na tela:

- **Chave azul ao lado do nome**: DAG ativa. Se estiver cinza, a DAG está pausada; clique para ativar.
- **Dois ícones no canto superior esquerdo do painel**: visão **Grid** (histórico de execuções em barras) e visão **Graph** (o fluxograma).
- **Botão `Trigger`** (canto superior direito): executa a DAG agora.

### O fluxograma (visão Graph)

```
wait_for_zip → prepare_snapshot → load_agencias … load_transacoes (7 em paralelo) → validate_all_tables → publish_snapshot → pipeline_complete
                                                                                       (se algo falhar) → record_failure
```

| Tarefa | O que faz |
|---|---|
| `wait_for_zip` | **Sensor**: espera o arquivo `banvic_data.zip` existir |
| `prepare_snapshot` | Congela uma cópia do ZIP e valida colunas, tipos e chaves |
| `load_<tabela>` (7) | Cada uma sobe um pod que roda o **Meltano** para uma tabela |
| `validate_all_tables` | Compara contagens e hashes de todos os valores com a origem |
| `publish_snapshot` | Publica as 7 tabelas em uma única transação |
| `pipeline_complete` | Marca o fim com sucesso |
| `record_failure` | Só roda se algo falhar; registra a falha na auditoria |

Cores:

- verde: sucesso;
- verde-claro: rodando;
- amarelo/laranja: vai tentar de novo (retry);
- vermelho: falhou;
- rosa: pulada (`skipped`). É normal o `record_failure` ficar rosa quando tudo dá certo.

### Executar

1. Clique em **Trigger**.
2. Abre uma janela de confirmação com os parâmetros da DAG (`simulate_failure_once` e `simulate_failure_always`). Eles podem estar dentro de uma seção recolhida. **Deixe os dois vazios** e clique em **Trigger** na janela.
3. Na visão **Grid**, clique na barra nova à direita (a execução que acabou de começar).
4. Mude para a visão **Graph** e acompanhe as caixas mudando de cor. Leva cerca de 1 minuto.

### Ver o log (onde o Meltano aparece)

1. Clique na tarefa **`load_transacoes`**.
2. Abra a aba **Logs**.

Você verá o Meltano executando `tap-csv` → `target-postgres` e, no final, a linha `table_loaded` com a quantidade esperada de linhas.

### Ver o código da DAG pela interface

Na página da DAG, aba **Code**, aparece o mesmo arquivo `dags/banvic_ingestion.py`.

### Simular uma falha (para mostrar o retry)

1. Clique em **Trigger**.
2. Em `simulate_failure_once`, escolha **`contas`** e confirme.

A tarefa `load_contas` falha na 1ª tentativa, fica amarela e, cerca de 20 segundos depois, conclui na 2ª. Nenhum dado é duplicado.

### Alternativa pelo terminal

Faz o mesmo que o botão Trigger, espera terminar e já confere o banco:

```bash
bash scripts/run_pipeline.sh minha_execucao_1
bash scripts/run_pipeline.sh teste_retry_1 --fail-once contas
```

Cada execução precisa de um **nome novo**: `minha_execucao_2`, `minha_execucao_3`…

### Agendamento

A DAG roda sozinha **todo dia às 06:00 (horário de São Paulo)** enquanto estiver ativa. Para parar o agendamento, clique na chave azul ao lado do nome da DAG.

---

## 5. Meltano: a ferramenta de ingestão

**Onde está configurado:** `meltano/meltano.yml`.

- `extractors → tap-csv`: lê o CSV.
- `loaders → target-postgres`: grava no PostgreSQL. A senha é marcada como `sensitive` e não fica no arquivo.

**Como ele roda:**

1. Cada tarefa `load_<tabela>` do Airflow cria um pod com a imagem `banvic-pipeline`.
2. Dentro do pod, o programa `pipeline/cli.py` executa `meltano run tap-csv target-postgres` para aquela tabela (linhas 51–52).
3. O resultado é gravado em um schema de staging exclusivo da execução.

As credenciais chegam ao pod pelo Secret `banvic-warehouse` do Kubernetes.

**Como mostrar o Meltano funcionando:**

1. No log de uma tarefa `load_*` no Airflow (seção 4).
2. Com o `kubectl get pods -w` durante a carga (seção 3).
3. Listando os plugins instalados na imagem:

   ```bash
   docker run --rm --user root --entrypoint meltano -w /opt/banvic/meltano banvic-pipeline:1.0.0 plugin list
   ```

---

## 6. PostgreSQL: ver os dados

### Conferência rápida

```bash
bash scripts/verify.sh
```

A saída tem quatro blocos:

1. **Contagem das 7 tabelas**. O total é 76.206 linhas: agencias 10, clientes 998, colaborador_agencia 100, colaboradores 100, contas 999, propostas_credito 2.000 e transacoes 71.999.
2. **`audit.ingestion_runs`**: cada execução com status (`published`, `failed`…) e o hash do ZIP.
3. **`audit.current_snapshot`**: qual execução está publicada agora.
4. **`analytics.credito_por_status`**: um exemplo de view para analistas.

### Consultar como analista (usuário somente leitura)

```bash
kubectl -n banvic exec -it postgres-0 -- sh -c 'PGPASSWORD="$ANALYST_PASSWORD" psql -h 127.0.0.1 -U banvic_analyst -d banvic_dw'
```

A senha não aparece na tela. Dentro do console do banco (`banvic_dw=>`), experimente:

```sql
\dv analytics.*
SELECT mes, agencia, quantidade_transacoes FROM analytics.transacoes_mensais ORDER BY mes DESC LIMIT 5;
SELECT * FROM analytics.credito_por_status;
CREATE TABLE raw.teste (id int);
```

- O comando `\dv analytics.*` lista as views prontas para análise.
- O último comando deve dar **"permission denied"**. Isso prova que o analista só lê.

Para sair, digite `\q`.

> Evite `SELECT * FROM raw.clientes` em gravação: essa tabela tem nomes, CPF e e-mail.

**Ferramentas gráficas** (Power BI, DBeaver): conecte em `localhost:5433`, banco `banvic_dw`, usuário `banvic_analyst`. A senha é o campo `analyst` do arquivo de credenciais.

---

## 7. Dashboard comercial

1. Veja a senha, fora da gravação:

   ```bash
   python3 -c "import json,os; print(json.load(open(os.path.expanduser('~/banvic-local/secrets/credentials.json')))['dashboard_admin'])"
   ```

2. Abra **http://localhost:8090**. Usuário: `comercial`.
3. Navegue pelo menu da esquerda:

   | Tela | Conteúdo |
   |---|---|
   | **Visão executiva** | Clientes ativos, transações por cliente e agências |
   | **Atividade e retenção** | Clientes ativos, em risco e inativos |
   | **Rede de agências** | Comparação entre agências |
   | **Crédito** | Propostas por status |
   | **Alavancas comerciais** | O que mais acompanha clientes ativos e o planejamento de um piloto |
   | **Critérios e qualidade** | Definições e rastreabilidade do snapshot |

4. Os filtros do topo (período, canal, agência) só valem depois de clicar em **Aplicar filtros**.

Se você mudou arquivos do dashboard, publique a nova versão:

```bash
bash scripts/deploy_commercial.sh
bash scripts/access.sh
```

---

## 8. Problemas comuns

| Sintoma | Solução |
|---|---|
| `postgres-0` em `CrashLoopBackOff` ou pods do Airflow em `Unknown` depois de reiniciar o PC | `bash scripts/access.sh` (reconecta os volumes sozinho) |
| Navegador não abre `localhost:8080` ou `8090` | `bash scripts/access.sh` |
| `kubectl`: "connection refused" ou "contexto incorreto" | `export KUBECONFIG="$HOME/banvic-local/kubeconfig"` e confira se o Docker Desktop está ligado |
| Botão Trigger não faz nada ou a execução fica parada | A DAG está pausada: ative a chave ao lado do nome |
| `run_pipeline.sh` diz que a execução já existe | Use outro nome de execução |
| Tarefa vermelha | Clique nela → **Logs** e leia a última mensagem de erro |
| Pod parado em `Pending` | Falta memória: feche programas pesados e aumente a memória do Docker/WSL |

---

## 9. Cola para a demonstração

```bash
# 1. Ligar (Docker Desktop aberto antes)
cd /mnt/c/Users/mateu/Desktop/data-engineer-indicium
bash scripts/access.sh
export KUBECONFIG="$HOME/banvic-local/kubeconfig"

# 2. Infraestrutura
kubectl -n banvic get pods
kubectl -n banvic get pvc

# 3. Pipeline (ou botão Trigger no Airflow)
bash scripts/run_pipeline.sh demo_1

# 4. Dados
bash scripts/verify.sh
```

Endereços:

- Airflow: http://localhost:8080 (usuário `admin`)
- Dashboard: http://localhost:8090 (usuário `comercial`)

Senhas em `~/banvic-local/secrets/credentials.json`. **Nunca mostre esse arquivo no vídeo.**

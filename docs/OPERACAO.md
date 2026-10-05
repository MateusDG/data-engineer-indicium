# Operação da POC

## Acesso e credenciais

Execute `bash scripts/access.sh` após iniciar o Docker e após trocar/reiniciar o pod da API. O script reutiliza port-forwards válidos, ignora processos zumbis e testa os endpoints HTTP de Airflow e dashboard. Se um processo continuar ativo apontando para um pod antigo, o script reinicia somente aquele encaminhamento identificado. Espere a atualização terminar antes de executar novamente.

Credenciais ficam em `~/banvic-local/secrets/credentials.json`, com permissão 600. Não altere esse arquivo isoladamente: o PostgreSQL inicializa usuários apenas na primeira criação do volume. Rotação exige alterar os usuários no banco e atualizar os Secrets coordenadamente.

## Diagnóstico

O dashboard fica em http://localhost:8090, usuário `comercial`, senha no campo `dashboard_admin` do arquivo privado. Para atualizar essa camada, use `bash scripts/deploy_commercial.sh` e depois `bash scripts/access.sh`. Não é necessário reiniciar o Airflow quando somente a interface comercial muda. `/health/ready` verifica o snapshot; logs ficam disponíveis em `kubectl -n banvic logs deployment/banvic-commercial`. Consulte [DASHBOARD_COMERCIAL.md](DASHBOARD_COMERCIAL.md).

1. Confirme `docker info` e `kind get clusters` no Ubuntu.
2. Defina `export KUBECONFIG="$HOME/banvic-local/kubeconfig"`.
3. Consulte `kubectl -n banvic get pods` e `kubectl -n banvic describe pod NOME`.
4. Veja a task e a tentativa com erro na interface do Airflow. O pipeline não imprime dados pessoais; conectores e bibliotecas devem permanecer com log INFO.
5. Consulte `audit.ingestion_runs` e `audit.current_snapshot` para distinguir execução malsucedida de snapshot publicado.

`Pending` pode indicar falta de recursos ou PVC não ligado. `ImagePullBackOff` em pod de ingestão indica que as imagens locais não foram carregadas: execute `bash scripts/build_images.sh`. `CrashLoopBackOff` exige inspeção de `kubectl logs --previous`; não apague volumes como solução genérica.

O ZIP deve conter somente as sete tabelas do contrato. Se o fornecedor mudar o schema, revise explicitamente `config/data_contract.json`, SQL e testes antes de aceitar a nova fonte.

## Atualizar código

```bash
bash scripts/build_images.sh
export KUBECONFIG="$HOME/banvic-local/kubeconfig"
kubectl -n banvic rollout restart deployment/airflow-api-server deployment/airflow-dag-processor
kubectl -n banvic rollout restart statefulset/airflow-scheduler
kubectl -n banvic rollout status deployment/airflow-api-server --timeout=300s
bash scripts/access.sh
```

Faça atualizações quando não houver execução ativa. As DAGs são incorporadas à imagem; não há Git Sync. Para mudanças na configuração Helm, use `bash scripts/reconcile_airflow.sh`. O deploy completo também aplica a configuração.

## Persistência, backup e retenção

Volumes: `~/banvic-local/data`, `~/banvic-local/postgres` e `~/banvic-local/logs`. Desligar Docker/WSL não remove os volumes. Excluir o cluster remove objetos Kubernetes, mas os diretórios externos continuam existindo. Reutilizar um banco existente exige preservar as credenciais originais.

Para backup consistente, use `pg_dump` do warehouse e do banco de metadados, armazene a cópia de forma privada e valide uma restauração em outro ambiente. Copiar o diretório do PostgreSQL enquanto o servidor está escrevendo não é um backup consistente.

Snapshots e staging ficam preservados durante a certificação. Em operação recorrente, defina prazo de retenção e faça limpeza somente de execuções encerradas, após backup, preservando a execução referida em `audit.current_snapshot`. Este projeto não executa limpeza destrutiva automática.

## Pausar agendamento

Pause a DAG na interface. A pausa impede novas execuções agendadas; não interrompe tarefas em andamento. O comando `run_pipeline.sh` reativa a DAG para a demonstração. Para liberar memória, encerre o Docker Desktop após terminar; os dados locais permanecem nos volumes.

## Limites

Kind é um cluster de um único nó. Não há alta disponibilidade, autoscaling, CDC ou isolamento de rede por NetworkPolicy neste CNI. StatsD está disponível internamente; não foram instalados Grafana/Prometheus nem alertas externos. O SimpleAuthManager é destinado a desenvolvimento e teste. A publicação é atômica; consumidores que precisam da mesma fotografia entre várias consultas devem usar REPEATABLE READ.

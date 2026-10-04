"""Daily full snapshot: immutable ZIP -> Meltano pods -> validation -> atomic raw."""
from datetime import timedelta
from pathlib import Path

import pendulum
from airflow.sdk import DAG, Param, BaseSensorOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from kubernetes.client import models as k8s

TABLES = ["agencias", "clientes", "colaborador_agencia", "colaboradores", "contas", "propostas_credito", "transacoes"]


class SnapshotSensor(BaseSensorOperator):
    """Wait for an atomically delivered ZIP; reschedule releases executor slots."""
    def poke(self, context):
        path = Path("/data/input/banvic_data.zip")
        return path.is_file() and path.stat().st_size > 0


with DAG(
    dag_id="banvic_ingestion",
    description="Ingestão íntegra das sete tabelas do ERP BanVic",
    start_date=pendulum.datetime(2026, 10, 1, tz="America/Sao_Paulo"),
    schedule="0 6 * * *",
    catchup=False,
    max_active_runs=1,
    max_active_tasks=4,
    dagrun_timeout=timedelta(minutes=45),
    default_args={"owner": "banvic-data", "retries": 2, "retry_delay": timedelta(seconds=20),
                  "retry_exponential_backoff": True, "max_retry_delay": timedelta(minutes=2)},
    params={"simulate_failure_once": Param("", type="string", enum=["", *TABLES],
             description="Demonstração opcional: falha transitória antes da carga de uma tabela"),
            "simulate_failure_always": Param("", type="string", enum=["", *TABLES],
             description="Teste opcional de falha definitiva; preserva o snapshot publicado")},
    tags=["banvic", "elt", "meltano", "snapshot"],
) as dag:
    wait = SnapshotSensor(task_id="wait_for_zip", mode="reschedule", poke_interval=30,
                          timeout=600, retries=0)

    def pod(task_id, command, table=None, **kwargs):
        arguments = [command, "--run-id", "{{ run_id }}"]
        if table:
            arguments += ["--table", table]
        return KubernetesPodOperator(
            task_id=task_id,
            namespace="banvic",
            name=f"banvic-{task_id.replace('_', '-')}",
            image="banvic-pipeline:1.0.0",
            image_pull_policy="Never",
            cmds=["python", "-m", "pipeline.cli"],
            arguments=arguments,
            in_cluster=True,
            service_account_name="banvic-pipeline",
            env_from=[k8s.V1EnvFromSource(secret_ref=k8s.V1SecretEnvSource(name="banvic-warehouse"))],
            env_vars={"SIMULATE_FAILURE_ONCE": "{{ params.simulate_failure_once }}",
                      "SIMULATE_FAILURE_ALWAYS": "{{ params.simulate_failure_always }}"},
            volumes=[k8s.V1Volume(name="data", persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(claim_name="banvic-data"))],
            volume_mounts=[k8s.V1VolumeMount(name="data", mount_path="/data/input", sub_path="input", read_only=True),
                           k8s.V1VolumeMount(name="data", mount_path="/data/work", sub_path="work")],
            security_context={"runAsUser": 1000, "runAsGroup": 1000, "fsGroup": 1000},
            container_security_context={"allowPrivilegeEscalation": False, "capabilities": {"drop": ["ALL"]}},
            container_resources=k8s.V1ResourceRequirements(requests={"cpu": "100m", "memory": "256Mi"},
                                                         limits={"cpu": "2", "memory": "1Gi"}),
            labels={"app": "banvic-pipeline"},
            get_logs=True,
            log_events_on_failure=False,
            log_pod_spec_on_failure=False,
            on_finish_action="delete_pod",
            startup_timeout_seconds=180,
            execution_timeout=timedelta(minutes=20),
            do_xcom_push=False,
            **kwargs,
        )

    prepare = pod("prepare_snapshot", "prepare")
    loads = [pod(f"load_{table}", "load", table) for table in TABLES]
    validate = pod("validate_all_tables", "validate")
    publication = pod("publish_snapshot", "publish")
    complete = EmptyOperator(task_id="pipeline_complete")
    failure = pod("record_failure", "failure", trigger_rule="one_failed", retries=1)
    wait >> prepare >> loads >> validate >> publication >> complete
    [wait, prepare, *loads, validate, publication] >> failure

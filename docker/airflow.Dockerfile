FROM apache/airflow:3.2.2-python3.12@sha256:bbe58e3204d550ab98dbf738a42c0e6663c455357ecd0e2d1440ef9cb6a75f00
COPY --chown=airflow:root dags/ /opt/airflow/dags/
ENV AIRFLOW__CORE__LOAD_EXAMPLES=false

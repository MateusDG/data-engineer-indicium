FROM python:3.12.14-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
WORKDIR /opt/banvic
COPY commercial/requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock && \
    groupadd --gid 1000 banvic && useradd --uid 1000 --gid 1000 --create-home banvic
COPY commercial/ commercial/
USER 1000:1000
EXPOSE 8090
CMD ["uvicorn","commercial.app:app","--host","0.0.0.0","--port","8090","--no-access-log"]

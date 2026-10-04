FROM meltano/meltano:v4.4.0-python3.12-slim@sha256:dc5421533a91de964a5bc21adf12339f74466a5eb564568bd7592a0bd3b23db7
USER root
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/banvic
COPY meltano/ meltano/
RUN cd meltano && meltano install && pip install --no-cache-dir 'psycopg[binary]==3.2.12'
COPY config/ config/
COPY pipeline/ pipeline/
COPY sql/ sql/
RUN groupadd --gid 1000 banvic && useradd --uid 1000 --gid 1000 --create-home banvic && chmod -R a+rX /opt/banvic
ENV PYTHONPATH=/opt/banvic PYTHONUNBUFFERED=1 MELTANO_SEND_ANONYMOUS_USAGE_STATS=false
USER 1000:1000
ENTRYPOINT ["python", "-m", "pipeline.cli"]

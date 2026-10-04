CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS audit.ingestion_runs (
    run_id text PRIMARY KEY,
    source_sha256 text,
    staging_schema text,
    status text NOT NULL CHECK (status IN ('running', 'validated', 'published', 'failed')),
    started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    finished_at timestamptz,
    error text,
    manifest jsonb,
    validation jsonb
);
CREATE TABLE IF NOT EXISTS audit.table_results (
    run_id text REFERENCES audit.ingestion_runs(run_id),
    table_name text,
    row_count bigint NOT NULL,
    content_sha256 text NOT NULL,
    PRIMARY KEY (run_id, table_name)
);
CREATE TABLE IF NOT EXISTS audit.current_snapshot (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    run_id text NOT NULL REFERENCES audit.ingestion_runs(run_id),
    source_sha256 text NOT NULL,
    published_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.agencias (
    cod_agencia text PRIMARY KEY, nome text, endereco text, cidade text,
    uf text, data_abertura text, tipo_agencia text
);
CREATE TABLE IF NOT EXISTS raw.clientes (
    cod_cliente text PRIMARY KEY, primeiro_nome text, ultimo_nome text,
    email text, tipo_cliente text, data_inclusao text, cpfcnpj text,
    data_nascimento text, endereco text, cep text
);
CREATE TABLE IF NOT EXISTS raw.colaborador_agencia (
    cod_colaborador text, cod_agencia text, PRIMARY KEY (cod_colaborador, cod_agencia)
);
CREATE TABLE IF NOT EXISTS raw.colaboradores (
    cod_colaborador text PRIMARY KEY, primeiro_nome text, ultimo_nome text,
    email text, cpf text, data_nascimento text, endereco text, cep text
);
CREATE TABLE IF NOT EXISTS raw.contas (
    num_conta text PRIMARY KEY, cod_cliente text, cod_agencia text,
    cod_colaborador text, tipo_conta text, data_abertura text,
    saldo_total text, saldo_disponivel text, data_ultimo_lancamento text
);
CREATE TABLE IF NOT EXISTS raw.propostas_credito (
    cod_proposta text PRIMARY KEY, cod_cliente text, cod_colaborador text,
    data_entrada_proposta text, taxa_juros_mensal text, valor_proposta text,
    valor_financiamento text, valor_entrada text, valor_prestacao text,
    quantidade_parcelas text, carencia text, status_proposta text
);
CREATE TABLE IF NOT EXISTS raw.transacoes (
    cod_transacao text PRIMARY KEY, num_conta text, data_transacao text,
    nome_transacao text, valor_transacao text
);
CREATE INDEX IF NOT EXISTS transacoes_conta_idx ON raw.transacoes(num_conta);
CREATE INDEX IF NOT EXISTS contas_cliente_idx ON raw.contas(cod_cliente);

-- Raw preserves source strings, including leading zeros. Views expose explicit types.
CREATE OR REPLACE VIEW analytics.transacoes_mensais AS
SELECT date_trunc('month', t.data_transacao::timestamptz AT TIME ZONE 'UTC')::date AS mes,
       c.cod_agencia, a.nome AS agencia, a.cidade, a.uf, a.tipo_agencia,
       count(*) AS quantidade_transacoes,
       count(DISTINCT c.cod_cliente) AS clientes_com_transacoes,
       count(*)::numeric / nullif(count(DISTINCT c.cod_cliente), 0) AS transacoes_por_cliente,
       sum(t.valor_transacao::numeric) AS valor_liquido,
       sum(abs(t.valor_transacao::numeric)) AS volume_movimentado
FROM raw.transacoes t
JOIN raw.contas c USING (num_conta)
LEFT JOIN raw.agencias a USING (cod_agencia)
GROUP BY 1, 2, 3, 4, 5, 6;

CREATE OR REPLACE VIEW analytics.atividade_clientes AS
WITH reference AS (SELECT max(data_transacao::timestamptz) AS data_referencia FROM raw.transacoes),
activity AS (
    SELECT c.cod_cliente, count(t.cod_transacao) AS quantidade_transacoes,
           max(t.data_transacao::timestamptz) AS ultima_transacao
    FROM raw.contas c LEFT JOIN raw.transacoes t USING (num_conta)
    GROUP BY c.cod_cliente
)
SELECT a.cod_cliente, a.quantidade_transacoes, a.ultima_transacao, r.data_referencia,
       extract(day FROM r.data_referencia - a.ultima_transacao)::integer AS dias_sem_transacao,
       CASE WHEN a.ultima_transacao IS NULL THEN 'sem_transacao'
            WHEN a.ultima_transacao >= r.data_referencia - interval '90 days' THEN 'ativo_90d'
            ELSE 'inativo_90d' END AS faixa_atividade
FROM activity a CROSS JOIN reference r;

CREATE OR REPLACE VIEW analytics.credito_por_status AS
SELECT status_proposta, count(*) AS quantidade_propostas,
       sum(valor_financiamento::numeric) AS valor_financiamento,
       avg(taxa_juros_mensal::numeric) AS taxa_media_mensal
FROM raw.propostas_credito GROUP BY status_proposta;

GRANT USAGE ON SCHEMA raw, analytics TO banvic_analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA raw, analytics TO banvic_analyst;
GRANT USAGE ON SCHEMA audit TO banvic_analyst;
GRANT SELECT ON audit.current_snapshot, audit.table_results TO banvic_analyst;

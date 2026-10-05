-- Public analytical interfaces: no names, emails, document numbers or addresses.
CREATE OR REPLACE VIEW analytics.commercial_accounts AS
SELECT c.num_conta, c.cod_cliente, c.cod_agencia,
       (c.data_abertura::timestamptz AT TIME ZONE 'UTC')::date AS opened_at,
       (cl.data_nascimento::timestamptz AT TIME ZONE 'UTC')::date AS birth_date,
       (cl.cod_cliente IS NOT NULL) AS registered_client,
       a.nome AS agency, a.cidade AS city, a.uf AS state, a.tipo_agencia AS channel
FROM raw.contas c
LEFT JOIN raw.clientes cl USING(cod_cliente)
LEFT JOIN raw.agencias a USING(cod_agencia);

CREATE OR REPLACE VIEW analytics.commercial_transactions AS
SELECT t.num_conta, (t.data_transacao::timestamptz AT TIME ZONE 'UTC')::date AS occurred_at,
       t.nome_transacao AS transaction_type, t.valor_transacao::numeric AS amount,
       CASE WHEN t.nome_transacao LIKE 'Pix%' THEN 'Pix'
            WHEN t.nome_transacao='Compra Crédito' THEN 'Cartão de crédito'
            WHEN t.nome_transacao='Compra Débito' THEN 'Cartão de débito'
            WHEN t.nome_transacao IN ('Saque','Depósito em espécie') THEN 'Dinheiro'
            ELSE 'Transferências e pagamentos' END AS modality
FROM raw.transacoes t;

CREATE OR REPLACE VIEW analytics.commercial_credit AS
SELECT p.cod_cliente, p.cod_proposta,
       (p.data_entrada_proposta::timestamptz AT TIME ZONE 'UTC')::date AS submitted_at,
       p.status_proposta AS status, p.valor_financiamento::numeric AS requested_financing,
       p.taxa_juros_mensal::numeric AS monthly_rate, p.quantidade_parcelas::integer AS installments
FROM raw.propostas_credito p;

CREATE OR REPLACE VIEW analytics.commercial_monthly AS
SELECT date_trunc('month',t.occurred_at)::date AS month,
       a.cod_agencia,a.agency,a.city,a.state,a.channel,
       count(*) AS transactions,
       count(DISTINCT a.cod_cliente) FILTER (WHERE a.registered_client) AS active_registered_clients,
       count(*) FILTER (WHERE NOT a.registered_client) AS unregistered_client_transactions,
       sum(abs(t.amount)) AS gross_movement, sum(t.amount) AS net_movement
FROM analytics.commercial_transactions t JOIN analytics.commercial_accounts a USING(num_conta)
GROUP BY 1,2,3,4,5,6;

GRANT SELECT ON analytics.commercial_accounts,analytics.commercial_transactions,
    analytics.commercial_credit,analytics.commercial_monthly TO banvic_analyst;

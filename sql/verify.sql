SELECT 'agencias' AS tabela, count(*) AS registros FROM raw.agencias
UNION ALL SELECT 'clientes', count(*) FROM raw.clientes
UNION ALL SELECT 'colaborador_agencia', count(*) FROM raw.colaborador_agencia
UNION ALL SELECT 'colaboradores', count(*) FROM raw.colaboradores
UNION ALL SELECT 'contas', count(*) FROM raw.contas
UNION ALL SELECT 'propostas_credito', count(*) FROM raw.propostas_credito
UNION ALL SELECT 'transacoes', count(*) FROM raw.transacoes
ORDER BY tabela;
SELECT run_id, status, source_sha256, started_at, finished_at FROM audit.ingestion_runs ORDER BY started_at;
SELECT * FROM audit.current_snapshot;
SELECT * FROM analytics.credito_por_status ORDER BY quantidade_propostas DESC;

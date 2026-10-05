"""Read a consistent published snapshot using the analyst's read-only role."""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN
import os
import threading
import time

import pandas as pd
import psycopg
from psycopg.rows import dict_row


@dataclass
class Snapshot:
    marker: dict
    accounts: pd.DataFrame
    transactions: pd.DataFrame
    proposals: pd.DataFrame
    loaded_at: str


def cents(value):
    return int((Decimal(value) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_EVEN))


def connect():
    return psycopg.connect(host=os.environ.get('PGHOST','postgres'),
        port=int(os.environ.get('PGPORT','5432')),dbname=os.environ.get('PGDATABASE','banvic_dw'),
        user=os.environ.get('PGUSER','banvic_analyst'),password=os.environ['PGPASSWORD'],
        connect_timeout=10,application_name='banvic_commercial',row_factory=dict_row)


class Warehouse:
    def __init__(self):
        self._lock = threading.Lock()
        self._snapshot = None
        self._checked_at = 0

    def snapshot(self):
        with self._lock:
            if self._snapshot is not None and time.monotonic()-self._checked_at < 30:
                return self._snapshot
            with connect() as conn:
                conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
                conn.execute("SET LOCAL statement_timeout = '20s'")
                marker = conn.execute('SELECT run_id,source_sha256,published_at FROM audit.current_snapshot').fetchone()
                if marker is None:
                    raise RuntimeError('Nenhum snapshot publicado. Execute a ingestão primeiro.')
                if self._snapshot is not None and self._snapshot.marker['run_id'] == marker['run_id']:
                    self._checked_at = time.monotonic()
                    return self._snapshot
                accounts = pd.DataFrame(conn.execute('SELECT * FROM analytics.commercial_accounts').fetchall())
                transactions = pd.DataFrame(conn.execute('SELECT * FROM analytics.commercial_transactions').fetchall())
                proposals = pd.DataFrame(conn.execute('SELECT * FROM analytics.commercial_credit').fetchall())
            if accounts.empty or transactions.empty:
                raise RuntimeError('O snapshot comercial não contém contas e transações.')
            accounts['opened_at'] = pd.to_datetime(accounts['opened_at'])
            accounts['birth_date'] = pd.to_datetime(accounts['birth_date'])
            transactions['occurred_at'] = pd.to_datetime(transactions['occurred_at'])
            transactions['amount_cents'] = transactions.pop('amount').map(cents).astype('int64')
            transactions = transactions.merge(accounts.drop(columns=['birth_date']),on='num_conta',how='left',validate='many_to_one')
            if not transactions['cod_cliente'].notna().all():
                raise RuntimeError('Transação sem conta correspondente no snapshot.')
            proposals['submitted_at'] = pd.to_datetime(proposals['submitted_at'])
            proposals['financing_cents'] = proposals.pop('requested_financing').map(cents).astype('int64')
            proposals['monthly_rate'] = proposals['monthly_rate'].astype(float)
            self._snapshot = Snapshot(marker,accounts,transactions,proposals,datetime.now(timezone.utc).isoformat())
            self._checked_at = time.monotonic()
            return self._snapshot


warehouse = Warehouse()

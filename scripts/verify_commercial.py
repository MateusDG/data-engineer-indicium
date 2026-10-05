"""Verify the deployed service using the official source, without printing secrets."""
import argparse
import csv
import io
import json
import os
from datetime import datetime, timezone
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8090')
    parser.add_argument('--home', type=Path, default=Path(os.environ.get('BANVIC_HOME', str(Path.home()/'banvic-local'))))
    parser.add_argument('--evidence-dir', type=Path)
    args = parser.parse_args()
    credentials = json.loads((args.home/'secrets/credentials.json').read_text())
    jar = CookieJar()
    client = build_opener(HTTPCookieProcessor(jar))
    checks = []

    def request(path, expected=200, body=None, method=None):
        payload = json.dumps(body).encode() if body is not None else None
        headers = {'Content-Type':'application/json'} if payload is not None else {}
        req = Request(args.url.rstrip('/')+path, data=payload, headers=headers, method=method)
        try:
            response = client.open(req, timeout=90)
        except HTTPError as exc:
            response = exc
        content = response.read()
        assert response.code == expected, f'{path.split("?")[0]}: HTTP {response.code}, expected {expected}'
        if path.startswith('/api/'):
            assert response.headers.get('Cache-Control') == 'no-store'
        if response.headers.get('Content-Type','').startswith('application/json'):
            return json.loads(content), response.headers
        return content, response.headers

    def passed(name):
        checks.append(name)

    def no_pii(value):
        forbidden = {'cod_cliente','num_conta','cpf','cpfcnpj','birth_date','email','primeiro_nome','ultimo_nome','endereco'}
        if isinstance(value,dict):
            assert not forbidden.intersection(value), 'Individual identifiers exposed in API'
            for item in value.values(): no_pii(item)
        elif isinstance(value,list):
            for item in value: no_pii(item)

    request('/health/live')
    request('/health/ready')
    request('/api/meta',401)
    request('/api/export?kind=monthly&start=2022-10-01&end=2022-12-31',401)
    passed('health_and_unauthenticated_access')
    request('/api/session',401,{'username':'comercial','password':'invalid-test-password'})
    _, headers = request('/api/session',body={'username':'comercial','password':credentials['dashboard_admin']})
    assert 'HttpOnly' in headers['Set-Cookie'] and 'SameSite=strict' in headers['Set-Cookie']
    assert headers['X-Frame-Options']=='DENY' and "default-src 'self'" in headers['Content-Security-Policy']
    passed('authentication_cookie_and_security_headers')
    meta, _ = request('/api/meta')
    assert meta['first_date']=='2010-01-01' and meta['transaction_first_date']=='2010-02-27'
    assert meta['last_date']=='2023-01-15' and meta['default_end']=='2022-12-31'
    no_pii(meta)
    passed('coverage_and_partial_month_default')
    base = {'start':meta['default_start'],'end':meta['default_end'],'channel':'all','agency':'all'}
    default, _ = request('/api/dashboard?'+urlencode(base))
    all_data, _ = request('/api/dashboard?'+urlencode({**base,'start':meta['first_date'],'end':meta['last_date']}))
    assert all_data['kpis']['transactions']==71999
    assert all_data['kpis']['registered_client_transactions']==71921
    assert all_data['credit']['proposals']==2000
    assert default['kpis']['transactions']==28532 and default['kpis']['active_clients']==700
    assert abs(default['kpis']['gross_movement']-20124786.83)<.005
    assert sum(row['transactions'] for row in all_data['monthly'])==71999
    for value in (default,all_data): no_pii(value)
    passed('source_reconciliation_and_customer_denominators')
    digital, _ = request('/api/dashboard?'+urlencode({**base,'channel':'Digital'}))
    physical, _ = request('/api/dashboard?'+urlencode({**base,'channel':'Física'}))
    assert digital['kpis']['transactions']+physical['kpis']['transactions']==default['kpis']['transactions']
    assert len(digital['agencies'])==1 and len(physical['agencies'])==9
    agency, _ = request('/api/dashboard?'+urlencode({**base,'agency':'7'}))
    assert agency['kpis']==digital['kpis']
    passed('channel_and_agency_filters')
    for change in ({'start':'2023-01-16'},{'end':'2026-01-01'},{'agency':'999'},{'channel':'invalid'},{'channel':'Digital','agency':'1'}):
        request('/api/dashboard?'+urlencode({**base,**change}),422)
    request('/api/evidence?quarter=2023-Q1',422)
    request('/api/evidence?quarter=invalid',422)
    passed('invalid_scopes_rejected')
    ranking, _ = request('/api/evidence?quarter='+meta['default_quarter'])
    assert len(ranking['rows'])==4 and ranking['eligible_clients']==888
    assert ranking['causally_identified_count']==0 and ranking['causal_ranking']==[]
    assert sum(bool(row.get('diagnostics_pass')) for row in ranking['rows'])==3
    assert all(row['transaction_effect']['ci95'][0]<0<row['transaction_effect']['ci95'][1]
               for row in ranking['rows'] if row.get('observational_rank'))
    no_pii(ranking)
    passed('adjusted_contrasts_and_identification_gate')
    plan, _ = request('/api/experiment-plan?quarter='+meta['default_quarter'])
    filtered_plan, _ = request('/api/experiment-plan?'+urlencode({'quarter':meta['default_quarter'],'agency':'10'}))
    assert filtered_plan['eligible_clients']<plan['eligible_clients']
    request('/api/experiment-plan?quarter=2022-Q4&relative_lift=0',422)
    no_pii(plan)
    passed('power_planning_and_scope')
    exported = 0
    for kind in ('monthly','agencies','credit','evidence'):
        content, headers = request('/api/export?'+urlencode({**base,'kind':kind,'quarter':meta['default_quarter']}))
        assert content.startswith(b'\xef\xbb\xbf') and 'attachment;' in headers['Content-Disposition']
        rows = list(csv.DictReader(io.StringIO(content.decode('utf-8-sig')),delimiter=';'))
        assert rows and all(row['source_run_id']==meta['source']['run_id'] for row in rows)
        if kind=='evidence':
            assert {'p_holm_transacoes','p_holm_atividade','ic_simultaneo_inferior','diferenca_atividade_fracao'}.issubset(rows[0])
        no_pii(rows)
        exported += len(rows)
    passed('four_aggregate_csv_exports_with_traceability')
    request('/api/session',method='DELETE')
    request('/api/meta',401)
    passed('logout_invalidates_browser_access')
    receipt = {'verified_at':datetime.now(timezone.utc).isoformat(),'source_run_id':meta['source']['run_id'],
        'checks':checks,'check_groups_passed':len(checks),'exported_aggregate_rows':exported,
        'individual_identifiers_exposed':0,'causally_identified_count':0}
    if args.evidence_dir:
        args.evidence_dir.mkdir(parents=True,exist_ok=True)
        for name,value in [('metadata.json',meta),('dashboard-default.json',default),('dashboard-all.json',all_data),
                           ('ranking.json',ranking),('experiment-plan.json',plan),('api-validation.json',receipt)]:
            (args.evidence_dir/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()

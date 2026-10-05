"""Aggregate-only dashboard API served with its own local static assets."""
import csv
import io
import logging
import os
import threading
import time
from collections import OrderedDict,defaultdict
from datetime import date
from pathlib import Path
from typing import Literal

import pandas as pd
from fastapi import Depends,FastAPI,HTTPException,Query,Request,Response
from fastapi.responses import FileResponse,JSONResponse,StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field

from commercial import auth
from commercial.analytics import dashboard,filter_accounts,metadata,transaction_set
from commercial.causal import evidence,experiment_plan,quarter_window
from commercial.repository import warehouse

LOG = logging.getLogger('banvic.commercial')
STATIC = Path(__file__).parent/'static'
app = FastAPI(title='BanVic · Inteligência comercial',docs_url=None,redoc_url=None,openapi_url=None)
app.mount('/static',StaticFiles(directory=STATIC),name='static')
cache,cache_lock = OrderedDict(),threading.Lock()
login_attempts,login_lock = defaultdict(list),threading.Lock()


@app.middleware('http')
async def headers(request,call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    elif request.url.path == '/' or request.url.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'no-cache'
    return response


@app.exception_handler(Exception)
async def unexpected(request,error):
    LOG.error('Commercial request failed: %s (%s)',request.url.path,type(error).__name__)
    return JSONResponse({'detail':'A consulta não pôde ser concluída. Verifique o serviço e o último snapshot publicado.'},status_code=503)


def authenticated(request: Request):
    if not auth.validate_session(request.cookies.get(auth.COOKIE,'')):
        raise HTTPException(401,'Sessão expirada. Entre novamente.')


def snapshot():
    try:
        return warehouse.snapshot()
    except Exception as exc:
        LOG.error('Warehouse unavailable: %s',type(exc).__name__)
        raise HTTPException(503,'Dados indisponíveis. Confirme a ingestão e a conexão com o warehouse.') from None


def scope(start: date,end: date,channel,agency,data):
    meta = metadata(data)
    if start>end or start<date.fromisoformat(meta['first_date']) or end>date.fromisoformat(meta['last_date']):
        raise HTTPException(422,'Selecione um período válido dentro do histórico disponível.')
    if agency!='all' and agency not in {item['cod_agencia'] for item in meta['agencies']}:
        raise HTTPException(422,'Agência não encontrada.')
    if channel!='all' and agency!='all' and not any(item['cod_agencia']==agency and item['channel']==channel for item in meta['agencies']):
        raise HTTPException(422,'A agência não pertence ao canal selecionado.')


def cached(key,loader):
    with cache_lock:
        if key not in cache:
            cache[key] = loader()
            while len(cache)>32:
                cache.popitem(last=False)
        cache.move_to_end(key)
        return cache[key]


class Login(BaseModel):
    username: str = Field(min_length=1,max_length=64)
    password: str = Field(min_length=1,max_length=256)


@app.get('/')
def index():
    return FileResponse(STATIC/'index.html')


@app.get('/health/live')
def live():
    return {'status':'ok'}


@app.get('/health/ready')
def ready():
    snapshot()
    return {'status':'ready'}


@app.post('/api/session')
def login(body: Login,request: Request,response: Response):
    origin = request.headers.get('origin')
    if origin and origin != str(request.base_url).rstrip('/'):
        raise HTTPException(403,'Origem da requisição inválida.')
    key = request.client.host
    with login_lock:
        now = time.monotonic()
        login_attempts[key] = [attempt for attempt in login_attempts[key] if now-attempt<60]
        if len(login_attempts[key])>=10:
            raise HTTPException(429,'Aguarde um minuto antes de tentar novamente.')
        login_attempts[key].append(now)
    if not auth.valid_login(body.username,body.password):
        raise HTTPException(401,'Usuário ou senha inválidos.')
    response.set_cookie(auth.COOKIE,auth.create_session(),httponly=True,samesite='strict',max_age=auth.SESSION_SECONDS,
        secure=os.environ.get('DASHBOARD_SECURE_COOKIE','false').lower()=='true',path='/')
    return {'user':'Equipe comercial'}


@app.delete('/api/session')
def logout(response: Response):
    response.delete_cookie(auth.COOKIE,path='/')
    return {'status':'signed_out'}


@app.get('/api/meta',dependencies=[Depends(authenticated)])
def meta():
    return metadata(snapshot())


@app.get('/api/dashboard',dependencies=[Depends(authenticated)])
def commercial_dashboard(start: date,end: date,channel: Literal['all','Digital','Física']='all',agency: str='all'):
    data = snapshot()
    scope(start,end,channel,agency,data)
    key = ('dashboard',data.marker['run_id'],str(start),str(end),channel,agency)
    return cached(key,lambda:dashboard(data,start,end,channel,agency))


@app.get('/api/evidence',dependencies=[Depends(authenticated)])
def commercial_evidence(quarter: str=Query(pattern=r'^20\d{2}-Q[1-4]$'),channel: Literal['all','Digital','Física']='all',agency: str='all'):
    data = snapshot()
    meta = metadata(data)
    if quarter not in meta['quarters']:
        raise HTTPException(422,'Trimestre fora da janela de análise disponível.')
    left,right = quarter_window(quarter)
    scope(left.date(),right.date(),channel,agency,data)
    key = ('evidence',data.marker['run_id'],quarter,channel,agency)
    return cached(key,lambda:evidence(data,quarter,channel,agency))


@app.get('/api/experiment-plan',dependencies=[Depends(authenticated)])
def planner(quarter: str=Query(pattern=r'^20\d{2}-Q[1-4]$'),
    relative_lift: float=Query(default=.2,ge=.01,le=1),retention_lift: float=Query(default=.05,ge=.01,le=.3),
    channel: Literal['all','Digital','Física']='all',agency: str='all'):
    data = snapshot()
    if quarter not in metadata(data)['quarters']:
        raise HTTPException(422,'Trimestre inválido.')
    start,end = quarter_window(quarter)
    scope(start.date(),end.date(),channel,agency,data)
    accounts = filter_accounts(data,channel,agency)
    eligible = accounts[accounts['registered_client']&(accounts['opened_at']<start)].copy()
    tx = transaction_set(data,eligible)
    tx = tx[(tx['occurred_at']>=start)&(tx['occurred_at']<=end)]
    values = eligible['cod_cliente'].map(tx.groupby('cod_cliente').size()).fillna(0).to_numpy(float)/3
    if len(values)<2:
        raise HTTPException(422,'Base insuficiente para planejar o teste.')
    return experiment_plan(float(values.mean()),float(values.std(ddof=1)),float((values>0).mean()),len(values),relative_lift,retention_lift)


@app.get('/api/export',dependencies=[Depends(authenticated)])
def export(kind: Literal['monthly','agencies','credit','evidence'],start: date,end: date,
    channel: Literal['all','Digital','Física']='all',agency: str='all',quarter: str='2022-Q4'):
    data = commercial_dashboard(start,end,channel,agency)
    if kind=='evidence':
        study = commercial_evidence(quarter,channel,agency)
        rows = [{'alavanca':r['title'],'status':r['evidence_status'],'clientes':r['sample'],
            'diferenca_ajustada_trx_cliente_mes':r.get('transaction_effect',{}).get('estimate'),
            'ic95_inferior':r.get('transaction_effect',{}).get('ci95',[None,None])[0],
            'ic95_superior':r.get('transaction_effect',{}).get('ci95',[None,None])[1],
            'ic_simultaneo_inferior':r.get('transaction_effect',{}).get('simultaneous_ci95',[None,None])[0],
            'ic_simultaneo_superior':r.get('transaction_effect',{}).get('simultaneous_ci95',[None,None])[1],
            'p_holm_transacoes':r.get('transaction_effect',{}).get('holm_p_value'),
            'diferenca_atividade_fracao':r.get('retention_effect',{}).get('estimate'),
            'atividade_ic95_inferior':r.get('retention_effect',{}).get('ci95',[None,None])[0],
            'atividade_ic95_superior':r.get('retention_effect',{}).get('ci95',[None,None])[1],
            'p_holm_atividade':r.get('retention_effect',{}).get('holm_p_value'),
            'suporte_comum_fracao':r.get('support_share'),'smd_maximo_ponderado':r.get('max_weighted_smd'),
            'diagnosticos_aprovados':r.get('diagnostics_pass',False),'causal_identificado':False,
            'prioridade_validacao':r['observational_rank'],'trimestre':quarter,
            'source_run_id':study['source']['run_id'],'source_sha256':study['source']['sha256']} for r in study['rows']]
    else:
        rows = data[kind] if kind!='credit' else data['credit']['statuses']
        rows = [{**row,'period_start':str(start),'period_end':str(end),'source_run_id':data['source']['run_id']} for row in rows]
    buffer = io.StringIO()
    if rows:
        fields = list(dict.fromkeys(key for row in rows for key in row))
        writer = csv.DictWriter(buffer,fieldnames=fields,delimiter=';',lineterminator='\n')
        writer.writeheader()
        for row in rows:
            # Prevent spreadsheet formula execution in exported text.
            safe = {key: "'"+value if isinstance(value,str) and value.startswith(('=','+','-','@','\t','\r')) else value for key,value in row.items()}
            writer.writerow(safe)
    return StreamingResponse(iter(['\ufeff'+buffer.getvalue()]),media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition':f'attachment; filename="banvic-{kind}-{start}-{end}.csv"'})

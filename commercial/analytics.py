"""Business definitions and aggregates; customer-level data never leaves the server."""
import calendar
from datetime import date

import numpy as np
import pandas as pd

from commercial.repository import Snapshot


def last_complete_month(last_date):
    value = pd.Timestamp(last_date)
    if value.day == calendar.monthrange(value.year,value.month)[1]:
        return value.normalize()
    return (value.replace(day=1)-pd.Timedelta(days=1)).normalize()


def metadata(snapshot: Snapshot):
    transaction_first,transaction_last = snapshot.transactions['occurred_at'].min(),snapshot.transactions['occurred_at'].max()
    first = min(transaction_first,snapshot.accounts['opened_at'].min(),snapshot.proposals['submitted_at'].min())
    last = max(transaction_last,snapshot.accounts['opened_at'].max(),snapshot.proposals['submitted_at'].max())
    complete = last_complete_month(last)
    quarter_end = complete.to_period('Q').end_time.normalize()
    if quarter_end > complete:
        quarter_end = (complete.to_period('Q')-1).end_time.normalize()
    agencies = snapshot.accounts[['cod_agencia','agency','city','state','channel']].drop_duplicates().sort_values('cod_agencia',key=lambda s:s.astype(int))
    months = snapshot.transactions.assign(month=snapshot.transactions['occurred_at'].dt.to_period('M')).groupby('month').size()
    anomalies = []
    for month,count in months.items():
        earlier = months[(months.index>=month-6)&(months.index<month)]
        if len(earlier)>=3 and earlier.median()>0 and count/earlier.median()>=3:
            anomalies.append({'month':str(month),'transactions':int(count),'vs_previous_median':round(float(count/earlier.median()),2)})
    return {'source':{'run_id':snapshot.marker['run_id'],'sha256':snapshot.marker['source_sha256'],
            'published_at':snapshot.marker['published_at'].isoformat(),'loaded_at':snapshot.loaded_at},
        'first_date':str(first.date()),'last_date':str(last.date()),
        'transaction_first_date':str(transaction_first.date()),'transaction_last_date':str(transaction_last.date()),
        'last_complete_month':str(complete.date()),
        'default_start':str(quarter_end.to_period('Q').start_time.date()),'default_end':str(quarter_end.date()),
        'default_quarter':str(quarter_end.to_period('Q'))[:4]+'-Q'+str(quarter_end.quarter),
        'quarters':[f'{p.year}-Q{p.quarter}' for p in pd.period_range(quarter_end.to_period('Q')-7,quarter_end.to_period('Q'),freq='Q')],
        'agencies':agencies.to_dict('records'),'anomalies':anomalies,
        'quality':{'source_clients_missing':int((~snapshot.accounts['registered_client']).sum()),
            'transactions_without_registered_client':int((~snapshot.transactions['registered_client']).sum()),
            'proposals_without_registered_client':int((~snapshot.proposals['cod_cliente'].isin(snapshot.accounts.loc[snapshot.accounts['registered_client'],'cod_cliente'])).sum()),
            'source_transactions':len(snapshot.transactions),'registered_clients':int(snapshot.accounts['registered_client'].sum())},
        'time_zone':'UTC','currency':'BRL'}


def filter_accounts(snapshot,channel='all',agency='all'):
    accounts = snapshot.accounts
    if channel != 'all':
        accounts = accounts[accounts['channel']==channel]
    if agency != 'all':
        accounts = accounts[accounts['cod_agencia']==agency]
    return accounts


def transaction_set(snapshot,accounts):
    return snapshot.transactions[snapshot.transactions['num_conta'].isin(accounts['num_conta'])]


def period_summary(accounts,transactions,start,end):
    eligible = accounts[accounts['registered_client']&(accounts['opened_at']<=end)]
    selected = transactions[(transactions['occurred_at']>=start)&(transactions['occurred_at']<=end)]
    known = selected[selected['registered_client']]
    recent = transactions[(transactions['occurred_at']>end-pd.Timedelta(days=90))&(transactions['occurred_at']<=end)&transactions['registered_client']]
    active = known['cod_cliente'].nunique()
    eligible_n = eligible['cod_cliente'].nunique()
    return {'transactions':len(selected),'registered_client_transactions':len(known),
        'active_clients':int(active),'eligible_clients':int(eligible_n),
        'transactions_per_active_client':len(known)/active if active else None,
        'active_rate':active/eligible_n if eligible_n else None,
        'active_90d':int(recent['cod_cliente'].nunique()),
        'gross_movement':int(selected['amount_cents'].abs().sum())/100,
        'net_movement':int(selected['amount_cents'].sum())/100,
        'unregistered_client_transactions':int((~selected['registered_client']).sum()),
        'new_clients':int(((eligible['opened_at']>=start)&(eligible['opened_at']<=end)).sum())}


def dashboard(snapshot: Snapshot,start: date,end: date,channel='all',agency='all'):
    start,end = pd.Timestamp(start),pd.Timestamp(end)
    accounts = filter_accounts(snapshot,channel,agency)
    transactions = transaction_set(snapshot,accounts)
    current = period_summary(accounts,transactions,start,end)
    duration = (end-start).days+1
    previous_end = start-pd.Timedelta(days=1)
    previous_start = previous_end-pd.Timedelta(days=duration-1)
    previous = period_summary(accounts,transactions,previous_start,previous_end)
    eligible = accounts[accounts['registered_client']&(accounts['opened_at']<=end)].copy()
    historic = transactions[(transactions['occurred_at']<=end)&transactions['registered_client']]
    last = historic.groupby('cod_cliente')['occurred_at'].max()
    eligible['last_transaction'] = eligible['cod_cliente'].map(last)
    eligible['days_since'] = (end-eligible['last_transaction']).dt.days
    eligible['segment'] = np.select([eligible['last_transaction'].isna(),eligible['days_since']<=30,
        eligible['days_since']<=60,eligible['days_since']<=90],
        ['Sem transação','Ativo · 0–30 dias','Atenção · 31–60 dias','Risco · 61–90 dias'],default='Inativo · mais de 90 dias')
    current['inactive_90d'] = int(((eligible['opened_at']<=end-pd.Timedelta(days=90))&(eligible['last_transaction'].isna()|(eligible['days_since']>90))).sum())
    old_set = set(transactions.loc[(transactions['occurred_at']>=previous_start)&(transactions['occurred_at']<=previous_end)&transactions['registered_client'],'cod_cliente'])
    new_set = set(transactions.loc[(transactions['occurred_at']>=start)&(transactions['occurred_at']<=end)&transactions['registered_client'],'cod_cliente'])
    before90 = set(transactions.loc[(transactions['occurred_at']>=start-pd.Timedelta(days=90))&(transactions['occurred_at']<start),'cod_cliente'])
    ever_before = set(transactions.loc[transactions['occurred_at']<start,'cod_cliente'])
    current['retained_clients'] = len(new_set&old_set)
    current['previous_active_clients'] = len(old_set)
    current['retention_rate'] = len(new_set&old_set)/len(old_set) if old_set else None
    current['reactivated_clients'] = len((new_set-before90)&ever_before)
    monthly = []
    for month in pd.period_range(start.to_period('M'),end.to_period('M'),freq='M'):
        left,right = max(start,month.start_time),min(end,month.end_time.normalize())
        info = period_summary(accounts,transactions,left,right)
        monthly.append({'month':str(month),'partial':left!=month.start_time or right!=month.end_time.normalize(),**info})
    selected = transactions[(transactions['occurred_at']>=start)&(transactions['occurred_at']<=end)]
    mix = [{'name':name,'transactions':len(group),'share':len(group)/len(selected) if len(selected) else 0,
        'gross_movement':int(group['amount_cents'].abs().sum())/100} for name,group in selected.groupby('modality')]
    mix.sort(key=lambda x:x['transactions'],reverse=True)
    agency_rows = []
    for code,group in accounts.groupby('cod_agencia'):
        metrics = period_summary(group,transaction_set(snapshot,group),start,end)
        candidates = eligible[eligible['cod_agencia']==code]
        metrics['attention_clients'] = int(candidates['segment'].isin(['Atenção · 31–60 dias','Risco · 61–90 dias']).sum())
        info = group.iloc[0]
        agency_rows.append({'id':code,'name':info['agency'],'city':info['city'],'state':info['state'],'channel':info['channel'],**metrics})
    agency_rows.sort(key=lambda x:x['transactions'],reverse=True)
    segments = [{'name':name,'clients':int(count),'share':count/len(eligible) if len(eligible) else 0}
        for name,count in eligible['segment'].value_counts().items()]
    opportunities = []
    for segment in ['Sem transação','Atenção · 31–60 dias','Risco · 61–90 dias','Inativo · mais de 90 dias']:
        group = eligible[eligible['segment']==segment]
        opportunities.append({'segment':segment,'clients':len(group),'top_agencies':group['agency'].value_counts().head(3).to_dict()})
    cohorts = []
    first_activity = historic.groupby('cod_cliente')['occurred_at'].min().dt.to_period('M')
    active_months = historic.assign(month=historic['occurred_at'].dt.to_period('M')).groupby('month')['cod_cliente'].agg(set)
    for cohort in pd.period_range(start.to_period('M'),end.to_period('M'),freq='M')[-12:]:
        members = set(first_activity[first_activity==cohort].index)
        if not members:
            continue
        values = []
        for lag in range(7):
            month = cohort+lag
            if month>end.to_period('M'):
                values.append(None)
            else:
                rate = len(members&active_months.get(month,set()))/len(members)
                values.append({'rate':rate,'partial':month==end.to_period('M') and end.day!=calendar.monthrange(end.year,end.month)[1]})
        cohorts.append({'cohort':str(cohort),'clients':len(members),'retention':values})
    proposals = snapshot.proposals[(snapshot.proposals['submitted_at']>=start)&(snapshot.proposals['submitted_at']<=end)]
    if channel!='all' or agency!='all':
        proposals = proposals[proposals['cod_cliente'].isin(accounts['cod_cliente'])]
    statuses = [{'status':name,'proposals':len(group),'requested_financing':int(group['financing_cents'].sum())/100,
        'mean_monthly_rate':float(group['monthly_rate'].mean())} for name,group in proposals.groupby('status')]
    approved = proposals[proposals['status']=='Aprovada']
    credit = {'proposals':len(proposals),'approved':len(approved),'approved_share':len(approved)/len(proposals) if len(proposals) else None,
        'requested_financing':int(proposals['financing_cents'].sum())/100,
        'approved_requested_financing':int(approved['financing_cents'].sum())/100,'statuses':statuses,
        'note':'Status atual das propostas que entraram no período. Não representa desembolso, receita nem conversão acompanhada no tempo.'}
    meta = metadata(snapshot)
    warnings = []
    if end>pd.Timestamp(meta['last_complete_month']):
        warnings.append('O período inclui um mês incompleto; comparações de volume exigem cautela.')
    for item in meta['anomalies']:
        if start.to_period('M')<=pd.Period(item['month'],freq='M')<=end.to_period('M'):
            warnings.append(f"{item['month']}: volume de transações {item['vs_previous_median']:.1f} vezes a mediana dos seis meses anteriores; causa não registrada na fonte.")
    return {'scope':{'start':str(start.date()),'end':str(end.date()),'channel':channel,'agency':agency,
        'previous_start':str(previous_start.date()),'previous_end':str(previous_end.date())},
        'kpis':current,'previous':previous,'monthly':monthly,'mix':mix,'agencies':agency_rows,
        'segments':segments,'opportunities':opportunities,'cohorts':cohorts,'credit':credit,'warnings':warnings,
        'source':meta['source']}

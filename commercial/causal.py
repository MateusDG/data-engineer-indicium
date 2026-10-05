"""Cross-fitted AIPW estimates, identification gates and experiment planning.

ERP contrasts remain observational. An estimator cannot supply a missing
intervention, treatment history or unmeasured confounder by itself.
"""
import math
import warnings

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from commercial.analytics import filter_accounts, metadata, transaction_set

SEED = 20261004
CONTRASTS = [
    {'id':'pix','title':'Uso do Pix','definition':'Ao menos um Pix realizado no trimestre anterior',
     'action':'Testar onboarding do Pix para clientes que ainda não o utilizam.',
     'missing':'Uso observado não registra convite, incentivo nem adesão aleatória.'},
    {'id':'credit_card','title':'Uso do cartão de crédito','definition':'Ao menos uma compra no crédito no trimestre anterior',
     'action':'Testar ativação e orientação de uso do cartão entre clientes elegíveis.',
     'missing':'Não há limite, disponibilidade do cartão, renda ou campanhas de ativação.'},
    {'id':'diversity','title':'Relacionamento com 3+ modalidades','definition':'Três ou mais modalidades de transação no trimestre anterior',
     'action':'Testar uma oferta de relacionamento com serviços complementares.',
     'missing':'Diversificação é comportamento escolhido pelo cliente, sem intervenção registrada.'},
    {'id':'digital','title':'Relacionamento na agência digital','definition':'Conta vinculada à agência digital no snapshot',
     'action':'Testar assistência digital entre clientes de agências físicas.',
     'missing':'Uma única agência digital; não há histórico de migração nem uso de aplicativo.'},
]


def holm(pvalues,*,family_size=None):
    """Family-wise error control; preserve the caller's ordering."""
    values = np.asarray(pvalues,dtype=float)
    family_size = len(values) if family_size is None else family_size
    if family_size<len(values):
        raise ValueError('The testing family cannot be smaller than the observed tests.')
    order = np.argsort(values)
    corrected = np.empty(len(values))
    running = 0.0
    for rank,index in enumerate(order):
        running = max(running,(family_size-rank)*values[index])
        corrected[index] = min(1.0,running)
    return corrected.tolist()


def processor(features):
    numerical = list(features.select_dtypes(include='number').columns)
    categorical = [name for name in features if name not in numerical]
    return ColumnTransformer([
        ('number',make_pipeline(SimpleImputer(strategy='median'),StandardScaler()),numerical),
        ('category',OneHotEncoder(handle_unknown='ignore',sparse_output=False),categorical)],
        remainder='drop',verbose_feature_names_out=False)


def summary_score(scores,family_size=8):
    scores = np.asarray(scores,dtype=float)
    estimate = float(scores.mean())
    se = float(scores.std(ddof=1)/math.sqrt(len(scores)))
    critical = float(norm.ppf(1-.05/(2*family_size)))
    p = float(2*norm.sf(abs(estimate/se))) if se>0 else (1.0 if estimate==0 else 0.0)
    return {'estimate':estimate,'standard_error':se,'ci95':[estimate-1.96*se,estimate+1.96*se],
        'simultaneous_ci95':[estimate-critical*se,estimate+critical*se],'p_value':p}


def balance(features,treatment,weights):
    encoder = processor(features)
    matrix = encoder.fit_transform(features)
    names = encoder.get_feature_names_out()
    items = []
    for i,name in enumerate(names):
        x = matrix[:,i]
        sd = math.sqrt((x[treatment==1].var(ddof=1)+x[treatment==0].var(ddof=1))/2)
        if sd<=1e-12:
            continue
        before = abs(x[treatment==1].mean()-x[treatment==0].mean())/sd
        after = abs(np.average(x[treatment==1],weights=weights[treatment==1])-
                    np.average(x[treatment==0],weights=weights[treatment==0]))/sd
        items.append({'feature':str(name),'before':float(before),'after':float(after)})
    return sorted(items,key=lambda item:item['after'],reverse=True)


def aipw(features,treatment,outcomes,*,family_size=8):
    """OOF nuisance fits; each row belongs to one customer, never repeated months.

    Confidence intervals use the empirical influence-score standard error.
    Trimming changes the target to customers with estimated common support.
    """
    features = features.reset_index(drop=True)
    treatment = np.asarray(treatment,dtype=int)
    y = np.asarray(outcomes,dtype=float)
    if y.ndim==1:
        y = y[:,None]
    counts = np.bincount(treatment,minlength=2)
    if len(treatment)<80 or counts.min()<20:
        return {'estimable':False,'reason':'Amostra insuficiente: mínimo de 80 clientes e 20 em cada grupo.',
            'sample':len(treatment),'treated':int(counts[1]),'control':int(counts[0])}
    folds = StratifiedKFold(n_splits=5,shuffle=True,random_state=SEED)
    propensity = np.zeros(len(treatment))
    m0,m1 = np.zeros_like(y),np.zeros_like(y)
    for train,test in folds.split(features,treatment):
        preprocessor = processor(features)
        train_x = preprocessor.fit_transform(features.iloc[train])
        test_x = preprocessor.transform(features.iloc[test])
        propensity_model = LogisticRegression(C=.5,max_iter=1500,random_state=SEED)
        propensity_model.fit(train_x,treatment[train])
        propensity[test] = propensity_model.predict_proba(test_x)[:,1]
        for arm,predicted in ((0,m0),(1,m1)):
            model = Ridge(alpha=5)
            model.fit(train_x[treatment[train]==arm],y[train][treatment[train]==arm])
            values = model.predict(test_x)
            predicted[test] = values[:,None] if values.ndim==1 else values
    support = (propensity>=.05)&(propensity<=.95)
    n = int(support.sum())
    if n<60 or min(np.bincount(treatment[support],minlength=2))<15:
        return {'estimable':False,'reason':'Suporte comum insuficiente após trimming [0,05; 0,95].',
            'sample':len(treatment),'treated':int(counts[1]),'control':int(counts[0]),'supported_clients':n}
    a,e = treatment[support],propensity[support]
    weights = a/e+(1-a)/(1-e)
    effective = {str(arm):float(weights[a==arm].sum()**2/(weights[a==arm]**2).sum()) for arm in (0,1)}
    diagnostic = balance(features[support].reset_index(drop=True),a,weights)
    max_smd = max((item['after'] for item in diagnostic),default=0)
    scores = m1[support]-m0[support]+a[:,None]*(y[support]-m1[support])/e[:,None]-(1-a[:,None])*(y[support]-m0[support])/(1-e[:,None])
    results = [summary_score(scores[:,index],family_size) for index in range(y.shape[1])]
    hist = np.histogram(propensity,bins=np.linspace(0,1,11))[0].tolist()
    return {'estimable':True,'sample':len(treatment),'treated':int(counts[1]),'control':int(counts[0]),
        'supported_clients':n,'support_share':n/len(treatment),'effective_sample':effective,
        'max_weighted_smd':max_smd,'balance':diagnostic[:10],'propensity_histogram':hist,
        'diagnostics_pass':n/len(treatment)>=.8 and min(effective.values())>=30 and max_smd<=.2,
        'effects':results,'naive_difference':(y[treatment==1].mean(axis=0)-y[treatment==0].mean(axis=0)).tolist()}


def identification_gate(*,registered_intervention=False,randomized=False,unobserved_confounding=True,diagnostics_pass=False):
    if not registered_intervention:
        return {'identified':False,'status':'exploratory','reason':'Ação comercial e atribuição de tratamento não registradas.'}
    if unobserved_confounding and not randomized:
        return {'identified':False,'status':'exploratory','reason':'Confundidores relevantes não observados; efeito causal não identificado.'}
    if not diagnostics_pass:
        return {'identified':False,'status':'insufficient_support','reason':'Critérios de comparabilidade não atendidos.'}
    return {'identified':True,'status':'identified_under_assumptions','reason':'Intervenção registrada e estratégia de identificação explicitada.'}


def quarter_window(quarter):
    year,number = quarter.split('-Q')
    period = pd.Period(f'{year}Q{number}',freq='Q')
    return period.start_time.normalize(),period.end_time.normalize()


def evidence(snapshot,quarter,channel='all',agency='all'):
    post_start,post_end = quarter_window(quarter)
    exposure_start = (post_start.to_period('Q')-1).start_time.normalize()
    exposure_end = post_start-pd.Timedelta(days=1)
    baseline_start = (post_start.to_period('Q')-2).start_time.normalize()
    baseline_end = exposure_start-pd.Timedelta(days=1)
    accounts = filter_accounts(snapshot,channel,agency)
    accounts = accounts[accounts['registered_client']&(accounts['opened_at']<baseline_start)].copy().reset_index(drop=True)
    transactions = transaction_set(snapshot,accounts)
    ids = accounts['cod_cliente']
    def window(left,right):
        return transactions[(transactions['occurred_at']>=left)&(transactions['occurred_at']<=right)]
    baseline = window(baseline_start,baseline_end)
    exposure = window(exposure_start,exposure_end)
    outcome = window(post_start,post_end)
    sensitivity_end = post_end.to_period('M').start_time-pd.Timedelta(days=1)
    short_outcome = window(post_start,sensitivity_end)
    earlier = window(baseline_start-pd.DateOffset(months=3),baseline_start-pd.Timedelta(days=1))
    def counts(frame):
        return ids.map(frame.groupby('cod_cliente').size()).fillna(0).to_numpy(float)
    def diversity(frame):
        return ids.map(frame.groupby('cod_cliente')['modality'].nunique()).fillna(0).to_numpy(float)
    earlier_history = transactions[transactions['occurred_at']<=baseline_end].groupby('cod_cliente')['occurred_at'].max()
    age = (baseline_start-accounts['birth_date']).dt.days/365.2425
    # Financial balances/statuses from the current snapshot are deliberately excluded.
    features = pd.DataFrame({'age':age.clip(18,100),
        'relationship_years':(baseline_start-accounts['opened_at']).dt.days/365.2425,
        'baseline_transactions':counts(baseline)/3,'baseline_modalities':diversity(baseline),
        'days_since_previous_transaction':(baseline_end-ids.map(earlier_history)).dt.days.fillna(1000).clip(0,1000),
        'agency':accounts['cod_agencia'],'city':accounts['city'].fillna('Não informada')})
    y = np.column_stack([counts(outcome)/3,(counts(outcome)>0).astype(float),counts(short_outcome)/2,counts(earlier)/3])
    exposure_pix = set(exposure.loc[exposure['transaction_type']=='Pix - Realizado','cod_cliente'])
    exposure_credit = set(exposure.loc[exposure['transaction_type']=='Compra Crédito','cod_cliente'])
    treatments = {'pix':ids.isin(exposure_pix).to_numpy(int),'credit_card':ids.isin(exposure_credit).to_numpy(int),
        'diversity':(diversity(exposure)>=3).astype(int),'digital':(accounts['channel']=='Digital').to_numpy(int)}
    rows = []
    for contrast in CONTRASTS:
        x = features.drop(columns=['agency']) if contrast['id']=='digital' else features
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UserWarning)
            result = aipw(x,treatments[contrast['id']],y)
        gate = identification_gate(diagnostics_pass=result.get('diagnostics_pass',False))
        row = {**contrast,**result,'identification':gate,'causal_rank':None,'observational_rank':None}
        if result['estimable']:
            main,retention,sensitivity,placebo = result.pop('effects')
            row.pop('effects',None)
            stable = main['estimate']*sensitivity['estimate']>=0
            row.update(transaction_effect=main,retention_effect=retention,sensitivity_effect=sensitivity,
                selection_check=placebo,sensitivity_direction_stable=stable,
                priority_basis='Limite inferior do intervalo simultâneo de transações por cliente/mês, somente entre contrastes com diagnóstico aprovado.')
            row['evidence_status'] = 'Comparabilidade limitada' if not result['diagnostics_pass'] else ('Sensível ao último mês' if not stable else 'Associação ajustada')
        else:
            row['evidence_status'] = 'Não estimável nesta amostra'
        rows.append(row)
    tested = [row for row in rows if row['estimable']]
    pvalues = [row[key]['p_value'] for row in tested for key in ('transaction_effect','retention_effect')]
    for index,value in enumerate(holm(pvalues,family_size=8)):
        tested[index//2][('transaction_effect','retention_effect')[index%2]]['holm_p_value'] = value
    candidates = sorted([row for row in tested if row['diagnostics_pass'] and row['sensitivity_direction_stable']],
        key=lambda row:row['transaction_effect']['simultaneous_ci95'][0],reverse=True)
    for rank,row in enumerate(candidates,1):
        row['observational_rank'] = rank
    rows.sort(key=lambda row:(row['observational_rank'] is None,row['observational_rank'] or 99,row['id']))
    meta = metadata(snapshot)
    return {'quarter':quarter,'scope':{'channel':channel,'agency':agency},'eligible_clients':len(accounts),
        'timeline':{'baseline':[str(baseline_start.date()),str(baseline_end.date())],
            'exposure':[str(exposure_start.date()),str(exposure_end.date())],
            'outcome':[str(post_start.date()),str(post_end.date())],
            'sensitivity':[str(post_start.date()),str(sensitivity_end.date())]},
        'method':{'estimator':'AIPW com cross-fitting estratificado de 5 folds',
            'propensity':'Regressão logística regularizada (C=0,5)',
            'outcome_model':'Ridge (alpha=5)', 'seed':SEED,'support':[.05,.95],
            'confidence':'IC individual de 95% e IC simultâneo de 95% por Bonferroni, família pré-definida de 8 contrastes/desfechos.',
            'multiplicity':'Holm para 4 exposições × 2 desfechos principais. Sensibilidade e seleção prévia são diagnósticos exploratórios.',
            'unit':'Um cliente por linha; transações/cliente/mês e atividade no trimestre.',
            'ranking':'Prioridade de validação, baseada no limite inferior do IC simultâneo. Não é ranking de retorno financeiro ou de efeito causal identificado.'},
        'causally_identified_count':0,'causal_ranking':[], 'rows':rows,
        'blocked':[{'id':'approved_credit','title':'Concessão de crédito','reason':'Há status atual e data de entrada da proposta, mas não data de aprovação/desembolso nem decisões finais do grupo de controle. Estimar após a entrada geraria classificação temporal incorreta.'},
            {'id':'marketing','title':'Investimento em marketing','reason':'Não há campanhas, exposição, atribuição aleatória, custos ou margem por transação. ROI causal não identificável.'}],
        'decision':'Usar os contrastes como hipóteses para testes controlados. Nenhuma alavanca nesta fonte tem retorno causal ou financeiro garantido.',
        'source':meta['source']}


def experiment_plan(baseline_mean,baseline_sd,baseline_active,eligible_clients,relative_lift=.2,retention_lift=.05,alpha=.05,power=.8):
    """Approximate two-arm planning; hypotheses, never observed causal returns."""
    z = float(norm.ppf(1-alpha/2)+norm.ppf(power))
    delta = baseline_mean*relative_lift
    transactions_n = math.ceil(2*z*z*baseline_sd**2/delta**2) if delta>0 and baseline_sd>0 else None
    p0 = min(max(baseline_active,0),1)
    p1 = min(p0+retention_lift,1.0)
    effect = p1-p0
    retention_n = math.ceil(z*z*(p0*(1-p0)+p1*(1-p1))/effect**2) if effect>0 else None
    return {'assumptions':{'relative_transaction_lift':relative_lift,'retention_lift':retention_lift,
        'alpha':alpha,'power':power,'baseline_mean':baseline_mean,'baseline_sd':baseline_sd,
        'baseline_activity_rate':baseline_active,'design':'Dois grupos aleatórios 1:1; unidade cliente; um teste primário.'},
        'transactions':{'minimum_detectable_effect':delta,'clients_per_arm':transactions_n,
            'feasible_in_current_base':transactions_n is not None and 2*transactions_n<=eligible_clients},
        'activity':{'minimum_detectable_effect':effect,'clients_per_arm':retention_n,
            'feasible_in_current_base':retention_n is not None and 2*retention_n<=eligible_clients},
        'eligible_clients':eligible_clients,'follow_up_days':90,
        'protocol':['Definir um único tratamento, população elegível e desfecho primário antes do sorteio.',
            'Sortear clientes 1:1, estratificando por agência e atividade anterior; registrar atribuição, não apenas adesão.',
            'Acompanhar 90 dias, medir intenção de tratar e preservar o grupo controle.',
            'Registrar custo, margem, recusas e mudanças de política; não misturar saldo atual com histórico.',
            'Se houver vários testes confirmatórios, ajustar multiplicidade e recalcular o tamanho da amostra.'],
        'note':'Planejamento aproximado pela distribuição normal; não é resultado de um experimento nem garantia de retorno.'}

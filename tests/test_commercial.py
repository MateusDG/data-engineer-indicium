"""Business and inference checks; all artificial examples are test fixtures only."""
from datetime import datetime,timezone
import os
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from commercial.analytics import dashboard,last_complete_month,metadata
from commercial.auth import create_session,validate_session,valid_login
from commercial.causal import aipw,experiment_plan,holm,identification_gate,summary_score
from commercial.repository import Snapshot,cents


def fixture():
    accounts = pd.DataFrame([
        {'num_conta':'1','cod_cliente':'1','cod_agencia':'7','opened_at':pd.Timestamp('2020-01-01'),'birth_date':pd.Timestamp('1990-01-01'),'registered_client':True,'agency':'Digital','city':'São Paulo','state':'SP','channel':'Digital'},
        {'num_conta':'2','cod_cliente':'2','cod_agencia':'1','opened_at':pd.Timestamp('2020-01-01'),'birth_date':pd.Timestamp('1980-01-01'),'registered_client':True,'agency':'Matriz','city':'São Paulo','state':'SP','channel':'Física'},
        {'num_conta':'3','cod_cliente':'ausente','cod_agencia':'1','opened_at':pd.Timestamp('2020-01-01'),'birth_date':pd.NaT,'registered_client':False,'agency':'Matriz','city':'São Paulo','state':'SP','channel':'Física'}])
    transactions = pd.DataFrame([{'num_conta':account,'occurred_at':pd.Timestamp(day),'amount_cents':value,'transaction_type':'Compra Débito','modality':'Cartão de débito'}
        for account,day,value in [('1','2022-09-01',100),('1','2022-10-01',100),('2','2022-10-15',-250),('3','2022-11-01',1000),('1','2022-12-01',200),('1','2023-01-15',100)]]).merge(accounts.drop(columns='birth_date'),on='num_conta',validate='many_to_one')
    proposals = pd.DataFrame([{'cod_cliente':'1','cod_proposta':'1','submitted_at':pd.Timestamp('2022-10-05'),'status':'Aprovada','financing_cents':10000,'monthly_rate':.02,'installments':12}])
    return Snapshot({'run_id':'fixture_only','source_sha256':'test','published_at':datetime(2026,10,4,tzinfo=timezone.utc)},accounts,transactions,proposals,'test')


class BusinessTests(unittest.TestCase):
    def test_money_is_quantized_without_binary_float_rounding(self):
        self.assertEqual(cents('1234.56'),123456)
        self.assertEqual(cents('-0.125'),-12)

    def test_partial_last_month_is_excluded_from_default(self):
        self.assertEqual(str(last_complete_month('2023-01-15').date()),'2022-12-31')
        meta = metadata(fixture())
        self.assertEqual(meta['default_start'],'2022-10-01')
        self.assertEqual(meta['default_end'],'2022-12-31')

    def test_orphans_remain_in_totals_but_not_customer_denominators(self):
        result = dashboard(fixture(),datetime(2022,10,1).date(),datetime(2022,12,31).date())
        self.assertEqual(result['kpis']['transactions'],4)
        self.assertEqual(result['kpis']['registered_client_transactions'],3)
        self.assertEqual(result['kpis']['active_clients'],2)
        self.assertEqual(result['kpis']['transactions_per_active_client'],1.5)
        self.assertEqual(result['kpis']['gross_movement'],15.5)
        self.assertEqual(result['kpis']['unregistered_client_transactions'],1)
        self.assertEqual(sum(r['transactions'] for r in result['monthly']),4)
        self.assertEqual(sum(r['clients'] for r in result['segments']),2)

    def test_channel_filter_changes_the_entire_scope(self):
        result = dashboard(fixture(),datetime(2022,10,1).date(),datetime(2022,12,31).date(),'Digital')
        self.assertEqual(result['kpis']['transactions'],2)
        self.assertEqual(result['kpis']['active_clients'],1)
        self.assertEqual(result['credit']['proposals'],1)
        self.assertEqual(len(result['agencies']),1)

    def test_history_includes_proposals_before_first_transaction(self):
        data = fixture()
        data.proposals.loc[0,'submitted_at'] = pd.Timestamp('2010-01-01')
        meta = metadata(data)
        self.assertEqual(meta['first_date'],'2010-01-01')
        result = dashboard(data,datetime(2010,1,1).date(),datetime(2023,1,15).date())
        self.assertEqual(result['credit']['proposals'],1)

    def test_future_retention_cells_are_absent_instead_of_zero(self):
        result = dashboard(fixture(),datetime(2022,10,1).date(),datetime(2022,12,31).date())
        row = next(row for row in result['cohorts'] if row['cohort']=='2022-10')
        self.assertEqual(row['retention'][0]['rate'],1)
        self.assertEqual(row['retention'][1]['rate'],0)
        self.assertIsNone(row['retention'][3])

    def test_no_customer_identifiers_are_exposed_in_aggregates(self):
        result = dashboard(fixture(),datetime(2022,10,1).date(),datetime(2022,12,31).date())
        def keys(value):
            if isinstance(value,dict):
                return set(value)|set().union(*(keys(v) for v in value.values()))
            if isinstance(value,list):
                return set().union(*(keys(v) for v in value)) if value else set()
            return set()
        self.assertFalse(keys(result)&{'cod_cliente','num_conta','cpf','cpfcnpj','birth_date','email','primeiro_nome'})


class InferenceTests(unittest.TestCase):
    def test_cross_fitted_estimator_recovers_a_known_randomized_effect(self):
        rng = np.random.default_rng(71)
        x = rng.normal(size=1000)
        treatment = rng.binomial(1,.5,size=1000)
        outcome = 1.8*treatment+2*x+rng.normal(size=1000)
        result = aipw(pd.DataFrame({'baseline':x}),treatment,outcome)
        self.assertTrue(result['estimable'])
        effect = result['effects'][0]
        self.assertAlmostEqual(effect['estimate'],1.8,delta=.2)
        self.assertLess(effect['ci95'][0],1.8)
        self.assertGreater(effect['ci95'][1],1.8)
        self.assertGreaterEqual(effect['simultaneous_ci95'][1]-effect['simultaneous_ci95'][0],effect['ci95'][1]-effect['ci95'][0])

    def test_constant_exposure_cannot_create_a_rank(self):
        result = aipw(pd.DataFrame({'x':np.arange(100)}),np.ones(100),np.arange(100))
        self.assertFalse(result['estimable'])

    def test_identification_is_not_granted_by_significance_or_balance(self):
        self.assertFalse(identification_gate(diagnostics_pass=True)['identified'])
        self.assertFalse(identification_gate(registered_intervention=True,diagnostics_pass=True)['identified'])
        self.assertTrue(identification_gate(registered_intervention=True,randomized=True,diagnostics_pass=True)['identified'])

    def test_holm_preserves_order_and_controls_the_family(self):
        np.testing.assert_allclose(holm([.01,.04,.2,.005]),[.03,.08,.2,.02])

    def test_missing_contrasts_do_not_shrink_the_prespecified_family(self):
        np.testing.assert_allclose(holm([.01,.03],family_size=8),[.08,.21])
        self.assertEqual(holm([],family_size=8),[])

    def test_zero_scores_do_not_claim_a_significant_effect(self):
        result = summary_score(np.zeros(100))
        self.assertEqual(result['p_value'],1)
        self.assertEqual(result['estimate'],0)

    def test_power_planning_is_a_hypothesis_and_respects_capacity(self):
        result = experiment_plan(5,20,.4,1000,.2,.05)
        self.assertGreater(result['transactions']['clients_per_arm'],1000)
        self.assertFalse(result['transactions']['feasible_in_current_base'])
        ceiling = experiment_plan(5,2,1,1000)
        self.assertIsNone(ceiling['activity']['clients_per_arm'])
        self.assertEqual(ceiling['activity']['minimum_detectable_effect'],0)


class SessionTests(unittest.TestCase):
    def test_signed_session_rejects_tampering_and_invalid_credentials(self):
        with patch.dict(os.environ,{'DASHBOARD_USER':'comercial','DASHBOARD_PASSWORD':'fixture-password','DASHBOARD_SESSION_KEY':'fixture-signature-key'}):
            token = create_session()
            self.assertTrue(validate_session(token))
            self.assertFalse(validate_session(token[:-5]+'xxxxx'))
            self.assertFalse(validate_session('malformed'))
            self.assertTrue(valid_login('comercial','fixture-password'))
            self.assertFalse(valid_login('comercial','wrong'))
            self.assertFalse(valid_login('other','fixture-password'))


if __name__=='__main__':
    unittest.main()

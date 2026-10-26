import tempfile,unittest
from pathlib import Path

class AccountCycleTests(unittest.TestCase):
 def test_user_dashboard_reset_keeps_an_extra_safety_hour_without_inventing_first_use(self):
  from account_cycles import WeeklyAccounts
  with tempfile.TemporaryDirectory() as t:
   ledger=WeeklyAccounts(Path(t)/'cycles.json');ledger.set_reset_deadline('https://tokenharbor.ai/v1','key',1000+50*3600,safety_seconds=3600)
   self.assertTrue(ledger.blocked('https://tokenharbor.ai/v1','key',1000+50*3600));self.assertFalse(ledger.blocked('https://tokenharbor.ai/v1','key',1000+51*3600))
   self.assertIsNone(ledger.entry('https://tokenharbor.ai/v1','key').get('first_success_observed_at'))
 def test_prime_once_then_use_accounts_in_order_and_reuse_after_reset(self):
  import json,urllib.error
  from unittest.mock import patch
  from io import BytesIO
  from reviewforge import CompatibleAPI
  from account_cycles import WEEK
  with tempfile.TemporaryDirectory() as t:
   env={'RF_API_KEYS':'alpha,beta','RF_BASE_URL':'https://tokenharbor.ai/v1','RF_WRITER_MODEL':'deepseek-v4.1-flash:free','RF_REVIEWER_MODEL':'deepseek-v4.1-flash:free','RF_FALLBACK_MODEL':'deepseek-v4.1-flash:free','RF_TOKENHARBOR_CYCLES_FILE':str(Path(t)/'cycles.json'),'RF_ACCOUNT_HEALTH_FILE':str(Path(t)/'health.json'),'RF_PROVIDER_FILE':str(Path(t)/'missing.json'),'RF_ALLOW_RATE_LIMIT_FAILOVER':'1'}
   seen=[];now=[1000];exhaust=[False]
   class Response:
    def __enter__(self):return BytesIO(b'{"choices":[{"message":{"content":"OK"}}]}')
    def __exit__(self,*args):return False
   def request(req,timeout):
    key=req.get_header('Authorization');seen.append(key)
    self.assertTrue(json.loads(req.data)['model'].endswith(':free'))
    if exhaust[0] and key=='Bearer alpha':raise urllib.error.HTTPError(req.full_url,429,'used',{},BytesIO(b'{"error":{"code":"free_quota_exceeded"}}'))
    return Response()
   with patch.dict('os.environ',env),patch('reviewforge.time.time',side_effect=lambda:now[0]),patch('reviewforge.urllib.request.urlopen',side_effect=request):
    api=CompatibleAPI();api.prime_free_accounts(deadline=1060);api.prime_free_accounts(deadline=1060);api.chat('s','u');api.chat('s','u')
    self.assertEqual(seen,['Bearer alpha','Bearer beta','Bearer alpha','Bearer alpha'])
    exhaust[0]=True;api.chat('s','u');self.assertEqual(seen[-2:],['Bearer alpha','Bearer beta'])
    now[0]=1000+WEEK+1;exhaust[0]=False;api.chat('s','u');self.assertEqual(seen[-1],'Bearer alpha')
 def test_exhaustion_is_reusable_after_seven_days_without_resetting_on_every_call(self):
  from account_cycles import WeeklyAccounts,WEEK
  with tempfile.TemporaryDirectory() as t:
   ledger=WeeklyAccounts(Path(t)/'cycles.json');ledger.success('https://tokenharbor.ai/v1','secret',1000)
   ledger.success('https://tokenharbor.ai/v1','secret',2000);self.assertEqual(ledger.entry('https://tokenharbor.ai/v1','secret')['window_started_at'],1000)
   self.assertEqual(ledger.exhausted('https://tokenharbor.ai/v1','secret',3000),1000+WEEK)
   self.assertTrue(ledger.blocked('https://tokenharbor.ai/v1','secret',1000+WEEK-1));self.assertFalse(ledger.blocked('https://tokenharbor.ai/v1','secret',1000+WEEK))
   ledger.success('https://tokenharbor.ai/v1','secret',1000+WEEK+10);self.assertEqual(ledger.entry('https://tokenharbor.ai/v1','secret')['window_started_at'],1000+WEEK+10)
   self.assertNotIn('secret',(Path(t)/'cycles.json').read_text());self.assertEqual(WeeklyAccounts(Path(t)/'cycles.json').entry('https://tokenharbor.ai/v1','secret')['first_success_observed_at'],1000)
 def test_unknown_start_is_not_invented_and_historical_record_is_labeled(self):
  from account_cycles import WeeklyAccounts,WEEK
  with tempfile.TemporaryDirectory() as t:
   ledger=WeeklyAccounts(Path(t)/'cycles.json');self.assertEqual(ledger.exhausted('https://tokenharbor.ai/v1','used',5000),5000+WEEK)
   self.assertIsNone(ledger.entry('https://tokenharbor.ai/v1','used').get('first_success_observed_at'))
   ledger.success('https://tokenharbor.ai/v1','other',1000,basis='historical_log');self.assertEqual(ledger.entry('https://tokenharbor.ai/v1','other')['start_basis'],'historical_log')
 def test_only_definite_free_quota_errors_are_weekly_exhaustion(self):
  from account_cycles import is_tokenharbor_free,is_weekly_quota
  self.assertTrue(is_tokenharbor_free('https://tokenharbor.ai/v1','deepseek-v4.1-flash:free'))
  self.assertFalse(is_tokenharbor_free('https://apimaster.ai/v1','deepseek-flash'))
  self.assertFalse(is_weekly_quota(429,{'error':{'code':'rate_limit_exceeded','message':'Too many requests per minute'}}))
  self.assertTrue(is_weekly_quota(429,{'error':{'code':'free_quota_exceeded','message':'Free period allowance exhausted'}}))

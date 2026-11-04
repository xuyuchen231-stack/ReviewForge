import json,tempfile,unittest,urllib.error
from pathlib import Path
from io import BytesIO
from unittest.mock import patch
from account_cycles import WeeklyAccounts,WEEK

class RefreshPriorityTests(unittest.TestCase):
 def test_new_key_probe_only_calls_that_key_once(self):
  from reviewforge import CompatibleAPI
  with tempfile.TemporaryDirectory() as t,patch.dict('os.environ',{'RF_BASE_URL':'https://tokenharbor.ai/v1','RF_API_KEYS':'old,new','RF_WRITER_MODEL':'x:free','RF_TOKENHARBOR_CYCLES_FILE':str(Path(t)/'cycles.json'),'RF_ACCOUNT_HEALTH_FILE':str(Path(t)/'health.json'),'RF_PROVIDER_FILE':str(Path(t)/'none')}):
   api=CompatibleAPI();seen=[]
   def request(req,timeout):
    seen.append(req.get_header('Authorization'));self.assertEqual(json.loads(req.data)['max_tokens'],32)
    return BytesIO(b'{"choices":[{"message":{"content":"OK"}}]}')
   with patch('reviewforge.urllib.request.urlopen',side_effect=request):
    api.prime_free_accounts(only_indices={1});api.prime_free_accounts(only_indices={1})
   self.assertEqual(seen,['Bearer new']);self.assertFalse(api.weekly_accounts.entry(api.base,'new')['server_window_confirmed'])
 def test_mixed_weekly_exhaustion_and_cooldown_keeps_retry_time(self):
  from reviewforge import CompatibleAPI
  with tempfile.TemporaryDirectory() as t,patch.dict('os.environ',{'RF_BASE_URL':'https://tokenharbor.ai/v1','RF_API_KEYS':'spent,cooling','RF_WRITER_MODEL':'x:free','RF_FALLBACK_MODEL':'x:free','RF_TOKENHARBOR_CYCLES_FILE':str(Path(t)/'cycles.json'),'RF_ACCOUNT_HEALTH_FILE':str(Path(t)/'health.json'),'RF_PROVIDER_FILE':str(Path(t)/'none')}),patch('reviewforge.time.time',return_value=1000):
   api=CompatibleAPI();api.weekly_accounts.exhausted(api.base,'spent',1000);api.key_cooldowns[1]=1120
   with patch('reviewforge.urllib.request.urlopen') as request:
    with self.assertRaisesRegex(RuntimeError,'Retry-After: 121'):api.chat('s','u')
    request.assert_not_called()
 def test_provider_message_date_is_recorded_without_fabricating_first_use(self):
  from account_cycles import provider_reset_epoch
  data={'error':{'message':"You've used this period's free allowance. Your next rolling 7-day period starts on 10 Nov 2026 at 22:19 UTC."}}
  stamp=provider_reset_epoch(data);self.assertIsNotNone(stamp)
  with tempfile.TemporaryDirectory() as t:
   ledger=WeeklyAccounts(Path(t)/'cycles.json')
   ledger.exhausted('https://tokenharbor.ai/v1','key',stamp-50,provider_data=data)
   row=ledger.entry('https://tokenharbor.ai/v1','key')
   self.assertEqual(row['server_reset_at'],stamp);self.assertTrue(row['server_window_confirmed'])
   self.assertIsNone(row.get('first_success_observed_at'));self.assertEqual(row['exhausted_until'],stamp+3600)
 def test_order_earliest_next_reset_filters_exhausted_cooling_and_unknown(self):
  with tempfile.TemporaryDirectory() as t:
   ledger=WeeklyAccounts(Path(t)/'cycles.json');base='https://tokenharbor.ai/v1'
   ledger.success(base,'late',900);ledger.success(base,'early',100)
   self.assertEqual(ledger.ordered_eligible(base,['unknown','late','early'],{},1000),[2,1,0])
   self.assertEqual(ledger.ordered_eligible(base,['unknown','late','early'],{2:1500},1000),[1,0])
   ledger.exhausted(base,'early',1000)
   self.assertEqual(ledger.ordered_eligible(base,['unknown','late','early'],{},1000),[1,0])
 def test_confirmed_period_anchor_does_not_drift_on_late_success(self):
  with tempfile.TemporaryDirectory() as t:
   ledger=WeeklyAccounts(Path(t)/'cycles.json');base='https://tokenharbor.ai/v1'
   ledger.record_provider_reset(base,'key',1000000)
   ledger.success(base,'key',1000100)
   row=ledger.entry(base,'key');self.assertEqual(ledger.next_reset(row,1000100),1000000+WEEK)
   self.assertTrue(row['server_window_confirmed']);self.assertEqual(row['window_started_at'],1000000)
 def test_runtime_uses_sorted_order_for_primary_and_failover(self):
  from reviewforge import CompatibleAPI
  with tempfile.TemporaryDirectory() as t,patch.dict('os.environ',{'RF_BASE_URL':'https://tokenharbor.ai/v1','RF_API_KEYS':'late,early,middle','RF_WRITER_MODEL':'x:free','RF_FALLBACK_MODEL':'x:free','RF_TOKENHARBOR_CYCLES_FILE':str(Path(t)/'cycles.json'),'RF_ACCOUNT_HEALTH_FILE':str(Path(t)/'health.json'),'RF_PROVIDER_FILE':str(Path(t)/'none')}),patch('reviewforge.time.time',return_value=1000):
   api=CompatibleAPI();ledger=api.weekly_accounts
   for key,start in [('early',100),('middle',200),('late',300)]:ledger.success(api.base,key,start)
   seen=[]
   def request(req,timeout):
    key=req.get_header('Authorization');seen.append(key)
    if key=='Bearer early':raise urllib.error.HTTPError(req.full_url,429,'quota',{},BytesIO(b'{"error":{"message":"Free allowance used up"}}'))
    return BytesIO(b'{"choices":[{"message":{"content":"OK"}}]}')
   with patch('reviewforge.urllib.request.urlopen',side_effect=request):self.assertEqual(api.chat('s','u'),'OK')
   self.assertEqual(seen,['Bearer early','Bearer middle'])

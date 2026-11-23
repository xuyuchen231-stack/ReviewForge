import json,tempfile,unittest
from pathlib import Path
from request_accounting import TransportTracker,authorize_network_recovery,authorize_model_recovery
from efficient_payload import InputBudgetExceeded

class DiagnosedRecoveryTests(unittest.TestCase):
 def failures(self,root):
  tracker=TransportTracker(root,'request','writer',100)
  for model in ['a','b','a']:
   token=tracker.reserve(model,6,'primary');tracker.finish(token,'FAILED',error_type='TimeoutError')
  return tracker
 def test_one_receipted_send_keeps_all_old_counters(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);tracker=self.failures(root)
   proof=authorize_network_recovery(root,'request','328d9dcfcf96bfa63a294bdbdcddd2283f8904ac','Fixed weekly-priority reselection after network failure')
   self.assertEqual(tracker.state()['chargeable_or_unknown'],3)
   with self.assertRaises(InputBudgetExceeded):tracker.reserve('a',6,'primary')
   token=tracker.reserve('a',7,'primary');tracker.finish(token,'RETURNED',{'prompt_tokens':1,'completion_tokens':1})
   state=tracker.state();self.assertEqual(state['total'],4);self.assertEqual(state['chargeable_or_unknown'],4)
   self.assertEqual(state['network_recovery']['used'],1)
   with self.assertRaises(InputBudgetExceeded):TransportTracker(root,'request','writer',100).reserve('a',8,'primary')
   authorize_network_recovery(root,'request','328d9dcfcf96bfa63a294bdbdcddd2283f8904ac','Fixed weekly-priority reselection after network failure')
   self.assertEqual(tracker.state(),state)
 def test_no_grant_for_unproven_or_successful_request(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   with self.assertRaises(ValueError):authorize_network_recovery(root,'request','a'*40,'A concrete diagnosis')
   tracker=TransportTracker(root,'request','writer',100)
   for _ in range(3):
    token=tracker.reserve('a',6,'primary');tracker.finish(token,'RETURNED',{'prompt_tokens':1})
   with self.assertRaises(ValueError):authorize_network_recovery(root,'request','a'*40,'A concrete diagnosis')
 def test_refusal_does_not_consume_chargeable_recovery_but_total_keeps_growing(self):
  from request_accounting import usage_summary
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);tracker=self.failures(root)
   authorize_network_recovery(root,'request','a'*40,'Concrete verified fix')
   token=tracker.reserve('a',7,'primary');tracker.finish(token,'REFUSED',http_status=403)
   self.assertEqual(tracker.state()['total'],4);self.assertEqual(tracker.state()['chargeable_or_unknown'],3)
   self.assertEqual(tracker.state()['network_recovery']['used'],0)
   token=tracker.reserve('b',8,'primary');tracker.finish(token,'RETURNED',{'prompt_tokens':1})
   self.assertEqual(tracker.state()['total'],5);self.assertEqual(tracker.state()['chargeable_or_unknown'],4)
   self.assertEqual(usage_summary(root/'requests.jsonl')['unknown_charge_attempts'],3)
   with self.assertRaises(InputBudgetExceeded):tracker.reserve('a',9,'primary')
 def test_different_model_recovery_requires_prior_success_and_two_failed_accounts(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);tracker=self.failures(root)
   authorize_network_recovery(root,'request','a'*40,'Network priority fixed')
   token=tracker.reserve('a',7,'primary');tracker.finish(token,'FAILED',error_type='TimeoutError')
   with self.assertRaises(ValueError):authorize_model_recovery(root,'request','fallback:free','Route confirmed failing across accounts')
   other=TransportTracker(root,'successful','writer',100)
   token=other.reserve('fallback:free',8,'primary');other.finish(token,'RETURNED',{'prompt_tokens':10})
   grant=authorize_model_recovery(root,'request','fallback:free','Route confirmed failing across accounts')
   self.assertEqual(tracker.state()['chargeable_or_unknown'],4)
   with self.assertRaises(InputBudgetExceeded):tracker.reserve('a',8,'primary')
   token=tracker.reserve('fallback:free',8,'primary');tracker.finish(token,'RETURNED',{'prompt_tokens':10})
   self.assertEqual(tracker.state()['chargeable_or_unknown'],5)
   with self.assertRaises(InputBudgetExceeded):tracker.reserve('fallback:free',9,'primary')
 def test_modified_recovery_receipt_is_not_reauthorized(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);tracker=self.failures(root)
   authorize_network_recovery(root,'request','a'*40,'Concrete fix')
   state=tracker.state();state['network_recovery']['baseline_total']=0
   tracker.budget_path.write_text(json.dumps(state))
   with self.assertRaises(ValueError):authorize_network_recovery(root,'request','a'*40,'Concrete fix')
if __name__=='__main__':unittest.main()

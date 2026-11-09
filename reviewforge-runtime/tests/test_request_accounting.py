import json,tempfile,unittest
from pathlib import Path
from request_accounting import RequestJournal

class RequestAccountingTests(unittest.TestCase):
 def test_usage_summary_does_not_double_count_logical_and_transport_rows(self):
  from request_accounting import usage_summary
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/'requests.jsonl';j=RequestJournal(path)
   for scope in ('logical','transport'):
    token=j.start('same','writer',100,200,scope=scope);j.finish(token,'RETURNED',{'prompt_tokens':35,'completion_tokens':4})
   token=j.start('cached','writer',100,200);j.finish(token,'CACHE_HIT',{})
   token=j.start('unknown','writer',100,200,scope='transport');j.finish(token,'FAILED',{})
   summary=usage_summary(path)
   self.assertEqual(summary['prompt_tokens'],35);self.assertEqual(summary['completion_tokens'],4)
   self.assertEqual(summary['cache_hits'],1);self.assertEqual(summary['unknown_charge_attempts'],1)
 def test_physical_sends_inside_model_fallback_are_each_accounted(self):
  from reviewforge import CompatibleAPI
  from request_accounting import TransportTracker
  from unittest.mock import patch
  from io import BytesIO
  with tempfile.TemporaryDirectory() as t,patch.dict('os.environ',{'RF_ACCOUNT_HEALTH_FILE':str(Path(t)/'health.json')}):
   api=CompatibleAPI({'RF_BASE_URL':'https://fixture.example/v1','RF_API_KEY':'secret','RF_WRITER_MODEL':'first','RF_FALLBACK_MODEL':'second'})
   api.transport_tracker=TransportTracker(Path(t),'binding','writer',200);calls=[]
   def request(req,timeout):
    calls.append(req)
    if len(calls)==1:raise TimeoutError('fixture')
    return BytesIO(b'{"choices":[{"message":{"content":"OK"}}],"usage":{"prompt_tokens":15,"completion_tokens":2}}')
   with patch('reviewforge.open_chat_response',side_effect=request):self.assertEqual(api.chat('s','u'),'OK')
   rows=[json.loads(s) for s in Path(t,'requests.jsonl').read_text().splitlines()]
   self.assertEqual([r['status'] for r in rows],['STARTED','FAILED','STARTED','RETURNED'])
   self.assertTrue(all(r['scope']=='transport' for r in rows));self.assertEqual(api.transport_tracker.state()['total'],2)
 def test_physical_cap_survives_restart_and_prevents_fourth_send(self):
  from request_accounting import TransportTracker
  from efficient_payload import InputBudgetExceeded
  with tempfile.TemporaryDirectory() as t:
   for _ in range(3):
    tracker=TransportTracker(Path(t),'binding','writer',200);token=tracker.reserve('m',1,'p');tracker.finish(token,'FAILED',error_type='TimeoutError')
   with self.assertRaises(InputBudgetExceeded):TransportTracker(Path(t),'binding','writer',200).reserve('m',1,'p')
 def test_restart_appends_and_does_not_expose_prompts(self):
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/'requests.jsonl'
   for _ in range(2):
    j=RequestJournal(path);token=j.start('binding','reviewer',100,200)
    j.finish(token,'RETURNED',{'prompt_tokens':35,'completion_tokens':4},model='model',slot=2)
   rows=[json.loads(s) for s in path.read_text().splitlines()]
   self.assertEqual(len(rows),4);self.assertEqual(sum(r.get('usage',{}).get('prompt_tokens',0) for r in rows),70)
   self.assertTrue(all('prompt' not in r for r in rows))
 def test_failed_attempt_has_unknown_charge_and_no_stale_usage(self):
  with tempfile.TemporaryDirectory() as t:
   j=RequestJournal(Path(t)/'log.jsonl');token=j.start('binding','writer',100,200);j.finish(token,'FAILED',{},error_type='TimeoutError')
   row=json.loads(j.path.read_text().splitlines()[-1]);self.assertTrue(row['charge_unknown']);self.assertEqual(row['usage'],{})

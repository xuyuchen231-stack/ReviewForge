import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from major_revision import provider_request
from efficient_payload import InputBudgetExceeded

class ExecutionLimitTests(unittest.TestCase):
 class API:
  last_finish_reason=None;last_model='fixture';last_key_slot=1
  def __init__(self,path):self.execution_root=Path(path);self.calls=0
  def chat(self,system,user,role):self.calls+=1;self.last_usage={'prompt_tokens':10,'completion_tokens':3};return '{"accepted":true}'
 def test_oversized_review_never_dispatches(self):
  with tempfile.TemporaryDirectory() as t:
   api=self.API(t)
   with self.assertRaises(InputBudgetExceeded):provider_request(api,'system',{'text':'x'*150000},'accepted','reviewer')
   self.assertEqual(api.calls,0)
 def test_cache_and_append_only_ledger_survive_restart(self):
  with tempfile.TemporaryDirectory() as t:
   a=self.API(t);provider_request(a,'s',{'text':'evidence'},'accepted','reviewer')
   b=self.API(t);provider_request(b,'s',{'text':'evidence'},'accepted','reviewer')
   self.assertEqual((a.calls,b.calls),(1,0))
   rows=[json.loads(x) for x in Path(t,'requests.jsonl').read_text().splitlines()]
   self.assertEqual(len(rows),4);self.assertEqual(sum(r.get('usage',{}).get('prompt_tokens',0) for r in rows),10)
 def test_changed_evidence_invalidates_response_cache(self):
  with tempfile.TemporaryDirectory() as t:
   a=self.API(t)
   for n in (1,2):provider_request(a,'s',{'canonical_studies':[{'citekey':'A','facts':{'n':{'id':'f1','value':n}}}]},'accepted','reviewer')
   self.assertEqual(a.calls,2)
 def test_changed_wire_policy_invalidates_response_cache(self):
  with tempfile.TemporaryDirectory() as t:
   a=self.API(t)
   for version in (1,2):
    with patch('efficient_payload.project_payload',return_value={'text':'evidence','policy':version}):provider_request(a,'s',{'text':'evidence'},'accepted','reviewer')
   self.assertEqual(a.calls,2)
 def test_failed_response_does_not_reuse_previous_usage(self):
  with tempfile.TemporaryDirectory() as t:
   a=self.API(t);a.last_usage={'prompt_tokens':99999}
   def fail(*args,**kwargs):raise TimeoutError('fixture')
   a.chat=fail
   with self.assertRaises(TimeoutError):provider_request(a,'s',{},'accepted','reviewer',retry=lambda call,deadline:call())
   row=json.loads(Path(t,'requests.jsonl').read_text().splitlines()[-1]);self.assertEqual(row['usage'],{});self.assertTrue(row['charge_unknown'])

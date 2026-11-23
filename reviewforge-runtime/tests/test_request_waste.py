import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from major_revision import provider_request
from editorial_refinement import _process_chunk,CHECKS

class WasteTests(unittest.TestCase):
 def test_transport_only_change_reuses_saved_response(self):
  class API:
   calls=0
   last_finish_reason=None
   def chat(self,*a,**k): self.calls+=1; return '{"facts":[]}'
  with tempfile.TemporaryDirectory() as d:
   api=API();api.execution_root=Path(d)
   payload={'facts':[],'question':'same exact scientific request'}
   provider_request(api,'same system',payload,'facts','reviewer')
   with patch('evidence_transport.encode_context_payload',return_value=' {"facts":[],"question":"same exact scientific request"} '):
    provider_request(api,'same system',payload,'facts','reviewer')
   self.assertEqual(api.calls,1)
 def test_changed_evidence_does_not_reuse_response(self):
  class API:
   calls=0;last_finish_reason=None
   def chat(self,*a,**k): self.calls+=1; return '{"facts":[]}'
  with tempfile.TemporaryDirectory() as d:
   api=API();api.execution_root=Path(d)
   for text in ['qualification one','qualification two']:
    provider_request(api,'system',{'facts':[],'evidence':text},'facts','reviewer')
   self.assertEqual(api.calls,2)
 def test_identical_rejected_repair_is_not_reviewed_twice(self):
  calls=[]
  body='A complete scientific argument with a concrete limitation.'
  def chat(system,payload,role):
   calls.append(role)
   if role=='writer':return body
   return json.dumps({'accept':False,**{k:True for k in CHECKS},'editorial_goal_met':False,'explanation':'Redundancy remains.'})
  with tempfile.TemporaryDirectory() as d:
   result=_process_chunk(body,'clean',chat,Path(d)/'chunk.json',None,binding='binding')
   self.assertFalse(result['accepted'])
   self.assertEqual(calls.count('writer'),2)
   self.assertEqual(calls.count('reviewer'),1)
   self.assertEqual(result.get('no_progress_reason'),'identical_rejected_candidate')
 def test_corrupt_logical_cache_fails_closed(self):
  class API:
   calls=0;last_finish_reason=None
   def chat(self,*a,**k):self.calls+=1;return '{"facts":[]}'
  with tempfile.TemporaryDirectory() as d:
   api=API();api.execution_root=Path(d)
   provider_request(api,'system',{'facts':[]},'facts','reviewer')
   cache=next((Path(d)/'semantic_responses').glob('*.json'))
   saved=json.loads(cache.read_text());saved['response']={'facts':['tampered']};cache.write_text(json.dumps(saved))
   with self.assertRaisesRegex(ValueError,'hash mismatch'):
    provider_request(api,'system',{'facts':[]},'facts','reviewer')
   self.assertEqual(api.calls,1)
 def test_real_repair_still_gets_independent_review(self):
  roles=[];writer=[0]
  body='The original scientific statement.'
  def chat(system,payload,role):
   roles.append(role)
   if role=='writer':
    writer[0]+=1
    return body if writer[0]==1 else 'The clarified scientific statement.'
   approved=writer[0]==2
   return json.dumps({'accept':approved,**{k:True for k in CHECKS},'editorial_goal_met':approved,'explanation':'Meaning and evidence assessed.'})
  with tempfile.TemporaryDirectory() as d:
   record=_process_chunk(body,'clean',chat,Path(d)/'chunk.json',None,binding='bound')
   self.assertTrue(record['accepted']);self.assertEqual(roles.count('reviewer'),2)
 def test_audit_does_not_double_count_logical_and_physical_usage(self):
  from audit_request_costs import audit
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/'requests.jsonl'
   rows=[{'binding':'b','status':'RETURNED','scope':scope,'role':'reviewer','usage':{'prompt_tokens':100}} for scope in ('logical','transport')]
   p.write_text('\n'.join(json.dumps(x) for x in rows))
   report=audit(root)['journals'][0]
   self.assertEqual(report['recorded_sends'],1)
   self.assertEqual(report['roles']['reviewer']['known_input'],100)
 def test_cached_rejection_stays_rejected_and_changed_prompt_is_new(self):
  class API:
   calls=0;last_finish_reason=None
   def chat(self,*a,**k):self.calls+=1;return '{"accepted":false,"issues":["unresolved evidence"]}'
  with tempfile.TemporaryDirectory() as d:
   api=API();api.execution_root=Path(d)
   first=provider_request(api,'system',{'candidate':'same'},'accepted','reviewer')
   again=provider_request(api,'system',{'candidate':'same'},'accepted','reviewer')
   self.assertEqual(first,again);self.assertFalse(again['accepted']);self.assertEqual(api.calls,1)
   provider_request(api,'changed scientific instruction',{'candidate':'same'},'accepted','reviewer')
   self.assertEqual(api.calls,2)
 def test_network_failures_do_not_retry_forever_without_deadline(self):
  from editorial_refinement import resilient_request
  sent=[0]
  def fail():
   sent[0]+=1
   if sent[0]>5:raise AssertionError('Unbounded network retry')
   raise ConnectionError('connection failure')
  with self.assertRaises(ConnectionError):
   resilient_request(fail,float('inf'),sleep=lambda delay:None)
  self.assertEqual(sent[0],5)
 def test_blankline_only_repair_does_not_buy_same_substantive_review(self):
  roles=[];body='First scientific statement.\n\n\nSecond scientific statement.';writes=[0]
  def chat(system,payload,role):
   roles.append(role)
   if role=='writer':
    writes[0]+=1
    return body if writes[0]==1 else body.replace('\n\n\n','\n\n')
   return json.dumps({'accept':False,**{k:True for k in CHECKS},'editorial_goal_met':False,'explanation':'Duplicated scientific argument remains.'})
  with tempfile.TemporaryDirectory() as d:
   result=_process_chunk(body,'condense',chat,Path(d)/'chunk.json',None,binding='bound')
   self.assertFalse(result['accepted']);self.assertEqual(roles.count('reviewer'),1)
if __name__=='__main__':unittest.main()

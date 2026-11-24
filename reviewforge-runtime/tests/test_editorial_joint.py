import json,tempfile,unittest
from pathlib import Path
from editorial_joint import apply_edits, issue_errors, process_chunk
from editorial_refinement import CHECKS,sha

class JointTests(unittest.TestCase):
 def test_patch_only_changes_named_adjacent_blocks(self):
  source="First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
  result,changes=apply_edits(source,[{'block_ids':['b002'],'replacement':'Better second paragraph.'}])
  self.assertEqual(result,"First paragraph.\n\nBetter second paragraph.\n\nThird paragraph.")
  self.assertEqual(changes[0]['before'],'Second paragraph.')
 def test_overlapping_and_nonadjacent_edits_rejected(self):
  for edits in ([{'block_ids':['b001','b003'],'replacement':'x'}],[{'block_ids':['b001'],'replacement':'x'},{'block_ids':['b001'],'replacement':'y'}]):
   with self.assertRaises(ValueError):apply_edits('A.\n\nB.\n\nC.',edits)
 def test_old_only_issue_quote_rejected(self):
  self.assertTrue(issue_errors({'issues':[{'kind':'current','quote':'Old duplication','check':'editorial_goal_met'}]},'New prose.',[]))
 def test_noop_rejected_candidate_not_reviewed_again_on_resume(self):
  calls=[]
  def chat(system,payload,role):
   calls.append(role)
   if role=='writer':return json.dumps({'edits':[]})
   return json.dumps(dict(accept=False,explanation='Needs clearer prose',issues=[{'kind':'current','quote':'Hybrid prose.','check':'editorial_goal_met'}],**{k:k!='editorial_goal_met' for k in CHECKS}))
  with tempfile.TemporaryDirectory() as d:
   cache=Path(d)/'record.json'
   record=process_chunk('Hybrid prose.',chat,cache,None,None,'bound')
   self.assertFalse(record['accepted']);self.assertEqual(calls,['writer','reviewer','writer'])
   process_chunk('Hybrid prose.',chat,cache,None,None,'bound')
   self.assertEqual(calls,['writer','reviewer','writer'])
 def test_pending_review_resumes_without_writer(self):
  calls=[]
  def chat(system,payload,role):
   calls.append(role)
   return json.dumps(dict(accept=True,explanation='Preserved',issues=[],**{k:True for k in CHECKS}))
  with tempfile.TemporaryDirectory() as d:
   cache=Path(d)/'record.json'
   cache.write_text(json.dumps({'source_sha256':sha('Text.'),'binding_sha256':'bound','candidate':'Text.','writer_calls':1,'review_calls':0,'accepted':False,'pending_review':True,'history':[],'changes':[]}),encoding='utf-8')
   self.assertTrue(process_chunk('Text.',chat,cache,None,None,'bound')['accepted'])
   self.assertEqual(calls,['reviewer'])
 def test_duplicate_citation_schema_never_invokes_writer_repair(self):
  from editorial_quality import citation_passage_options
  source=r'An exact hybrid evidence statement \cite{A}. A second related result \cite{A}.'
  context={'selected_citekeys':['A'],'anchors':[{'citekey':'A'}],'canonical_studies':[]};calls=[]
  def chat(system,payload,role):
   calls.append(role)
   if role=='writer':return json.dumps({'edits':[]})
   rows=[{'citekey':'A','passage_id':p['id'],'status':status,'reason':'Exact source support'} for p,status in zip(citation_passage_options(source,['A']),['supported','qualified'])]
   return json.dumps(dict(accept=True,explanation='Preserved',issues=[],citation_checks=rows,**{k:True for k in CHECKS}))
  with tempfile.TemporaryDirectory() as d:
   r=process_chunk(source,chat,Path(d)/'c.json',None,context,'bound')
   self.assertTrue(r['accepted']);self.assertEqual(calls,['writer','reviewer']);self.assertEqual(r['citation_audit']['checks'][0]['status'],'qualified')

 def test_duplicate_passages_preserve_worst_verdict(self):
  from editorial_joint import citation_audit
  from editorial_quality import citation_passage_options
  text=r'Hybrid evidence is qualified \cite{A}. A second related result \cite{A}.'
  options=citation_passage_options(text,['A'])
  review={'citation_checks':[{'citekey':'A','passage_id':o['id'],'status':status,'reason':'Exact qualified support'} for o,status in zip(options,['supported','qualified'])]}
  result=citation_audit(review,{'selected_citekeys':['A'],'anchors':[{'citekey':'A'}]},text)
  self.assertTrue(result['complete']);self.assertEqual(result['checks'][0]['status'],'qualified');self.assertEqual(len(result['all_passage_checks']),2)
 def test_invalid_patch_is_rolled_back_without_corrupting_other_edit(self):
  from editorial_joint import safe_edits
  text=r'Math $x=1$.'+'\n\n'+'Wordy redundant prose.'
  edited,rejected=safe_edits(text,[{'block_ids':['b001'],'replacement':'Math.'},{'block_ids':['b002'],'replacement':'Clear prose.'}])
  self.assertIn('$x=1$',edited);self.assertIn('Clear prose.',edited);self.assertEqual(len(rejected),1)
 def test_completed_response_reused_without_new_call_or_budget(self):
  from editorial_joint import ask
  calls=[]
  def chat(*args):calls.append(1);return json.dumps({'edits':[]})
  with tempfile.TemporaryDirectory() as d:
   cache=Path(d)/'c.json';record={}
   self.assertEqual(ask(chat,'system',{'body':'Text'},'writer',record,cache,None),{'edits':[]})
   restored=json.loads(cache.read_text(encoding='utf-8'))
   ask(chat,'system',{'body':'Text'},'writer',restored,cache,None)
   self.assertEqual(calls,[1]);self.assertEqual(restored['writer_calls'],1)
 def test_persisted_budget_prevents_send(self):
  from editorial_joint import ask
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(RuntimeError):ask(lambda *a:self.fail('Must not send'),'system',{},'writer',{'writer_calls':3},Path(d)/'c.json',None)
 def test_route_needs_two_accounts_and_proven_configured_free_fallback(self):
  from editorial_joint import proven_free_route
  from types import SimpleNamespace
  api=SimpleNamespace(base='https://tokenharbor.ai/v1',model='writer:free',fallback_model='fallback:free')
  rows=[{'scope':'transport','status':'FAILED','model':'writer:free','provider':'primary','account_slot':slot,'error_type':'TimeoutError','request_id':str(slot)} for slot in (1,2)]
  rows.append({'scope':'transport','status':'RETURNED','model':'fallback:free','role':'writer','provider':'primary','usage':{'prompt_tokens':10},'request_id':'success'})
  with tempfile.TemporaryDirectory() as d:
   journal=Path(d)/'r.jsonl'
   journal.write_text('\n'.join(json.dumps(r) for r in rows),encoding='utf-8')
   result=proven_free_route(api,[journal]);self.assertEqual(result['model'],'fallback:free')
   rows[1]['account_slot']=1;journal.write_text('\n'.join(json.dumps(r) for r in rows),encoding='utf-8')
   self.assertIsNone(proven_free_route(api,[journal]))
 def test_resume_cannot_promote_malformed_issues_or_empty_explanation(self):
  from unittest.mock import patch
  for issues,explanation in (({},'Preserved'),([],'')):
   with tempfile.TemporaryDirectory() as d:
    cache=Path(d)/'c.json';review=dict(accept=True,issues=issues,explanation=explanation,**{k:True for k in CHECKS})
    cache.write_text(json.dumps({'source_sha256':sha('Text.'),'binding_sha256':'b','candidate':'Text.','writer_calls':2,'review_calls':1,'terminal':True,'accepted':False,'review':review,'changes':[],'history':[]}),encoding='utf-8')
    r=process_chunk('Text.',lambda *a:self.fail('Do not send'),cache,None,None,'b')
    self.assertFalse(r['accepted'])
 def test_citation_repair_does_not_erase_another_keys_unsupported_finding(self):
  from editorial_joint import repair_citation_metadata,citation_audit
  from editorial_quality import citation_passage_options
  text=r'Hybrid model evidence contradicts A \cite{A}. Another model result belongs to B \cite{B}.'
  options=citation_passage_options(text,['A','B']);ids={o['citekey']:o['id'] for o in options}
  checks=[{'citekey':'A','passage_id':ids['A'],'status':status,'reason':'Reason for '+status} for status in ('unsupported','supported')]
  checks.append({'citekey':'B','passage_id':'bad','status':'supported','reason':'Invalid binding'})
  review=dict(accept=True,explanation='Preserved',issues=[],citation_checks=checks,**{k:True for k in CHECKS})
  context={'selected_citekeys':['A','B'],'anchors':[{'citekey':'A'},{'citekey':'B'}],'canonical_studies':[]}
  def chat(*a):return json.dumps({'candidate_sha256':sha(text),'citation_checks':[{'citekey':'B','passage_id':ids['B'],'status':'supported','reason':'Located primary support'}]})
  with tempfile.TemporaryDirectory() as d:
   revised=repair_citation_metadata(review,context,text,chat,{'history':[]},Path(d)/'c.json',None)
   audit=citation_audit(revised,context,text)
   self.assertTrue(audit['complete']);self.assertIn('A',audit['unsupported'])
if __name__=='__main__':unittest.main()

import json,tempfile,time,unittest
from pathlib import Path
from autonomous_review import RunLock, bootstrap, choose_task, assemble, source_packet, checkpoint_call, run_review

class AutonomousTests(unittest.TestCase):
 def source(self,w):
  text='\\begin{document}\n\\section{Methods}\n\\subsection{One}\nOriginal scientifically useful discussion. '*1+'\\cite{A}\n\\subsection{Two}\nSecond discussion. \\cite{A}\n\\end{document}'
  (w/'review_en.tex').write_text(text)
  (w/'evidence_ledger.json').write_text(json.dumps({'entries':[{'citekey':'A','claim':'A bounded finding','source_id':'A','locator':'p1','excerpt':'A quoted finding','limitations':'A limited study'}]}))
  return text
 def test_duplicate_run_refused_and_lock_released(self):
  with tempfile.TemporaryDirectory() as t:
   with RunLock(Path(t)/'run.lock'):
    with self.assertRaises(RuntimeError):
     with RunLock(Path(t)/'run.lock'):pass
   with RunLock(Path(t)/'run.lock'):pass
 def test_bootstrap_creates_frozen_copy_without_touching_master(self):
  with tempfile.TemporaryDirectory() as t:
   w=Path(t);before=self.source(w);run,state=bootstrap(w,9)
   self.assertEqual((w/'review_en.tex').read_text(),before)
   self.assertTrue((run/'synthesis_plan.json').exists());self.assertEqual(state['mode'],'autonomous')
   self.assertAlmostEqual(state['deadline']-state['started'],9*3600,delta=1)
 def test_scheduler_does_not_restart_completed_or_retry_exhausted_tasks(self):
  state={'tasks':{'a':{'status':'completed','visits':1},'b':{'status':'pending','visits':0},'c':{'status':'retry','visits':3}}}
  self.assertEqual(choose_task(state,3),'b')
  state['tasks']['b']['status']='completed';self.assertIsNone(choose_task(state,3))
 def test_assembly_preserves_original_when_no_passing_candidates(self):
  with tempfile.TemporaryDirectory() as t:
   w=Path(t);before=self.source(w);run,state=bootstrap(w,9)
   result=assemble(run,state)
   self.assertEqual(Path(result['english']).read_text(),before)
   self.assertEqual(result['accepted_units'],0);self.assertFalse(result['submission_ready'])
 def test_missing_full_text_is_not_invented(self):
  with tempfile.TemporaryDirectory() as t:
   w=Path(t);self.source(w);run,state=bootstrap(w,9)
   p=source_packet(w,run,{'citekey':'A','excerpt':'A quoted finding','locator':'p1','limitations':'Only excerpt'},'methods')
   self.assertEqual(p['access'],'anchor_only');self.assertIn('A quoted finding',str(p))
 def test_assembly_adds_only_registered_missing_bibliography_entries(self):
  with tempfile.TemporaryDirectory() as t:
   w=Path(t);self.source(w)
   p=w/'review_en.tex';p.write_text(p.read_text().replace(r'\end{document}',r'\begin{thebibliography}{99}\end{thebibliography}\end{document}'))
   (w/'literature.json').write_text(json.dumps([{'key':'A','title':'An actual registered title','authors':['Author'],'year':2020,'doi':'10.example/a','metadata_status':'REGISTERED_METADATA'}]))
   run,state=bootstrap(w,9);r=assemble(run,state)
   self.assertIn(r'\bibitem{A}',Path(r['english']).read_text());self.assertEqual(r['bibliography_added'],['A'])
 def test_expired_budget_makes_no_model_call(self):
  class API:
   def chat(self,*a,**k):raise AssertionError('API called after budget')
  with tempfile.TemporaryDirectory() as t:
   state={'deadline':time.time()-1,'calls':0}
   with self.assertRaises(TimeoutError):checkpoint_call(API(),state,Path(t)/'state.json','s',{},'writer')
 def test_autonomous_loop_prepares_and_reviews_without_manual_calibration(self):
  from synthesis_pipeline import CRITERIA
  class API:
   def chat(self,system,user,role='writer'):
    p=json.loads(user)
    if 'required_original_keys' in p:
     return json.dumps({'argument':{'question':'What is supported?','thesis':'Support is bounded.','comparison_axes':['reported_finding'],'study_keys':['A'],'paragraph_plan':[{'role':'comparison','point':'Discuss bounds','study_keys':['A']}],'synthesis_claim':'A bounded inference.','limitations':'Only one source.','open_question':'What transfers?','sparse_evidence_reason':'Single-study test fixture','kind':'core'},'studies':[{'citekey':'A','fields':{'reported_finding':{'status':'supported','value':'A bounded finding','locator':'p1','excerpt':'A quoted finding'}}}]})
    if role=='writer':return p['body']+'\n'+('A concrete comparative analysis of the retained assumptions. '*3)
    return json.dumps({'accept':True,'issues':[],'criteria':{k:{'status':'pass','explanation':'Mock grounded judgment','passages':[p['candidate'][-50:]]} for k in CRITERIA}})
  with tempfile.TemporaryDirectory() as t:
   w=Path(t);before=self.source(w)
   report=run_review(w,hours=.001,reserve_minutes=0,max_visits=1,translate=False,api_factory=API)
   self.assertEqual(report['accepted_units'],2);self.assertEqual((w/'review_en.tex').read_text(),before)
   from autonomous_review import coherence_review
   run=Path(report['english']).parent.parent;state=json.loads((run/'autonomous_state.json').read_text())
   key=report['accepted_ids'][0];body=(run/'synthesis_candidates/accepted'/(key+'.tex')).read_text()
   class GlobalAPI:
    def chat(self,*a,**k):return json.dumps({'issues':[{'unit_id':key,'id':'contradiction','severity':'major','passage':body[-40:],'reason':'Inconsistent conclusion','required_change':'Reconcile conclusion'}]})
   state['deadline']=time.time()+30;state['work_deadline']=state['deadline'];coherence_review(run,state,GlobalAPI())
   self.assertEqual(assemble(run,state)['accepted_units'],1)
   matrix=json.loads((run/'study_comparisons.json').read_text());matrix['studies'][0]['fields']['reported_finding']['value']='Changed evidence contract'
   (run/'study_comparisons.json').write_text(json.dumps(matrix))
   self.assertEqual(assemble(run,state)['accepted_units'],0)

 def test_resume_recovers_interrupted_final_visit(self):
  with tempfile.TemporaryDirectory() as t:
   w=Path(t);self.source(w);run,state=bootstrap(w,9)
   key=next(iter(state['tasks']));state['tasks'][key].update(visits=3,in_flight=True,status='retry')
   (run/'autonomous_state.json').write_text(json.dumps(state))
   _,resumed=bootstrap(w,9)
   self.assertEqual(resumed['tasks'][key]['visits'],2)
 def test_assembly_keeps_pdf_and_input_assets_without_overwriting_candidate(self):
  with tempfile.TemporaryDirectory() as t:
   w=Path(t);self.source(w);(w/'figure.pdf').write_bytes(b'figure');(w/'extra.tex').write_text('extra')
   run,state=bootstrap(w,9);result=assemble(run,state);output=Path(result['english']).parent
   self.assertTrue((output/'figure.pdf').exists());self.assertTrue((output/'extra.tex').exists())
 def test_scoped_contract_ignores_unrelated_units_but_tracks_relevant_evidence(self):
  from synthesis_pipeline import contract_digest
  plan={'units':[{'id':'a','study_keys':['A']},{'id':'b','study_keys':['B']}]};matrix={'studies':[{'citekey':'A','fields':{}},{'citekey':'B','fields':{}}]}
  first=contract_digest(plan,matrix,{},'a');plan['units'][1]['thesis']='changed';matrix['studies'][1]['fields']['x']='changed'
  self.assertEqual(first,contract_digest(plan,matrix,{},'a'))
  matrix['studies'][0]['fields']['x']='changed';self.assertNotEqual(first,contract_digest(plan,matrix,{},'a'))
 def test_provider_failures_pause_without_consuming_scientific_visits(self):
  from unittest.mock import patch
  class API:
   def chat(self,*a,**k):raise RuntimeError('API attempts failed: model: ValueError; Empty API response; finish_reason=length')
  with tempfile.TemporaryDirectory() as t:
   w=Path(t);self.source(w)
   with patch('autonomous_review.heartbeat'),patch('threading.Event.wait',return_value=False):
    report=run_review(w,hours=.1,translate=False,api_factory=API)
   self.assertEqual(report['status'],'paused_provider_failure')
   run=Path(report['report']).parent.parent;state=json.loads((run/'autonomous_state.json').read_text())
   self.assertEqual(state['requests_attempted'],3);self.assertEqual(state['calls'],0)
   self.assertTrue(all(row['visits']==0 for row in state['tasks'].values()))
 def test_request_timeout_is_provider_failure_not_run_deadline(self):
  class API:
   def chat(self,*a,**k):raise TimeoutError('API time budget reached')
  with tempfile.TemporaryDirectory() as t:
   with self.assertRaisesRegex(RuntimeError,'API attempts failed: request timeout'):
    checkpoint_call(API(),{'deadline':time.time()+3600},Path(t)/'state.json','s',{},'writer')
 def test_no_translation_or_build_for_unchanged_original(self):
  from unittest.mock import patch
  class API:
   def chat(self,*a,**k):raise AssertionError('No API expected')
  with tempfile.TemporaryDirectory() as t:
   w=Path(t);self.source(w);run,state=bootstrap(w,9)
   for task in state['tasks'].values():task.update(status='retry',visits=3)
   (run/'autonomous_state.json').write_text(json.dumps(state))
   with patch('reviewforge_v4.generate_chinese_body') as translation,patch('reviewforge_v4.compile_tex') as build:
    report=run_review(w,api_factory=API)
   translation.assert_not_called();build.assert_not_called()
   self.assertEqual(report['accepted_units'],0)
 def test_planning_extracts_sources_separately_and_caches_progress(self):
  from autonomous_review import prepare_unit,read,units
  class API:
   def __init__(self):self.requests=[]
   def chat(self,system,user,role='writer'):
    p=json.loads(user);self.requests.append(p)
    if 'required_original_keys' in p:
     assert len(json.dumps(p))<15000
     return json.dumps({'argument':{'question':'What is supported?','thesis':'Support is bounded.','comparison_axes':['reported_finding'],'study_keys':['A'],'paragraph_plan':[{'role':'comparison','point':'Discuss bounds','study_keys':['A']}],'synthesis_claim':'A bounded inference.','limitations':'Only one source.','open_question':'What transfers?','sparse_evidence_reason':'Single-study fixture','kind':'core'}})
    assert len(p['sources'])==1
    return json.dumps({'studies':[{'citekey':'A','fields':{'reported_finding':{'status':'supported','value':'A bounded finding','locator':'p1','excerpt':'A quoted finding'}}}]})
  with tempfile.TemporaryDirectory() as t:
   w=Path(t);self.source(w);run,state=bootstrap(w,9);unit=units((run/'review_en.tex').read_text())[0];api=API()
   prepare_unit(w,run,state,unit,api);self.assertEqual(len(api.requests),2)
   prepare_unit(w,run,state,unit,api);self.assertEqual(len(api.requests),2)
 def test_truncated_structured_output_retried_and_never_accepted(self):
  from autonomous_review import structured_call
  class API:
   def __init__(self):self.calls=0;self.max_tokens=1000
   def chat(self,*a,**k):
    self.calls+=1;self.last_finish_reason='length' if self.calls==1 else 'stop'
    return '{"argument":' if self.calls==1 else '{"argument":{"question":"bounded"}}'
  with tempfile.TemporaryDirectory() as t:
   api=API();result=structured_call(api,{'deadline':time.time()+3600},Path(t)/'state.json','s',{},'argument')
   self.assertEqual(result['argument']['question'],'bounded');self.assertEqual(api.calls,2)
   self.assertGreater(api.max_tokens,1000)
 def test_malformed_json_does_not_reset_provider_failure_streak(self):
  from autonomous_review import structured_call
  class API:
   max_tokens=1000
   def chat(self,*a,**k):return '{"studies": invalid}'
  with tempfile.TemporaryDirectory() as t:
   state={'deadline':time.time()+3600,'consecutive_provider_failures':2}
   with self.assertRaisesRegex(RuntimeError,'invalid structured'):
    structured_call(API(),state,Path(t)/'state.json','s',{},'studies')
   self.assertEqual(state['consecutive_provider_failures'],2)
 def test_surplus_closing_brace_is_normalized_without_changing_json_values(self):
  from autonomous_review import structured_call
  class API:
   def chat(self,*a,**k):return '{"studies":[{"citekey":"A","value":"literal } in text"}]}}'
  with tempfile.TemporaryDirectory() as t:
   state={'deadline':time.time()+3600};result=structured_call(API(),state,Path(t)/'state.json','s',{},'studies')
   self.assertEqual(result['studies'][0]['value'],'literal } in text')
   self.assertEqual(state['requests_attempted'],1)
   self.assertEqual(state['format_normalization'],'surplus_closing_delimiters')

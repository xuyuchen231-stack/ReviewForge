import json,tempfile,time,unittest
from pathlib import Path
from autonomous_review import RunLock, bootstrap, choose_task, assemble, source_packet, checkpoint_call, run_review

class AutonomousTests(unittest.TestCase):
 def test_coherence_route_is_reset_before_local_scientific_review(self):
  class API:
   model='writer';reviewer_model='critic';max_tokens=1000
   def chat(self,*args,**kwargs):return 'ok'
  with tempfile.TemporaryDirectory() as t:
   api=API();state={'deadline':time.time()+1200};path=Path(t)/'state.json'
   checkpoint_call(api,state,path,'s',{'units':[]},'reviewer');self.assertEqual(api.request_model,'critic');self.assertIsNone(api.reasoning_effort);self.assertEqual(api.thinking_mode,'disabled')
   checkpoint_call(api,state,path,'s',{'candidate':'draft','study_comparisons':[]},'reviewer');self.assertIsNone(api.request_model);self.assertIsNone(api.reasoning_effort);self.assertIsNone(api.thinking_mode)
 def test_resume_with_unfinished_units_reopens_coherence_budget(self):
  with tempfile.TemporaryDirectory() as t:
   ws=Path(t);self.source(ws);run,state=bootstrap(ws,9);state['coherence_rounds']=2
   (run/'autonomous_state.json').write_text(json.dumps(state),encoding='utf-8')
   _,resumed=bootstrap(ws,9);self.assertEqual(resumed['coherence_rounds'],0)
 def test_coherence_uses_the_same_validated_candidates_as_assembly(self):
  from autonomous_review import coherence_review
  from synthesis_pipeline import units
  with tempfile.TemporaryDirectory() as t:
   ws=Path(t);original=self.source(ws);run,state=bootstrap(ws,9);expected=units(original)[0]['body'];folder=run/'synthesis_candidates/accepted';folder.mkdir(parents=True);(folder/'unit_001.tex').write_text('Unreviewed stale candidate')
   class API:
    max_tokens=1000
    def chat(api,system,user,role):
     self.assertEqual(json.loads(user)['units'][0]['text'],expected);return json.dumps({'issues':[]})
   self.assertEqual(coherence_review(run,state,API()),[])
 def test_resume_requeues_completed_tasks_whose_accepted_candidate_is_invalid(self):
  from autonomous_review import reconcile_completed_tasks
  with tempfile.TemporaryDirectory() as t:
   ws=Path(t);before=self.source(ws);run,state=bootstrap(ws,9);key=next(iter(state['tasks']))
   state['tasks'][key].update(status='completed',visits=3)
   reconcile_completed_tasks(run,state,max_visits=3)
   self.assertEqual(state['tasks'][key]['status'],'retry');self.assertEqual(state['tasks'][key]['visits'],2)
   self.assertEqual(state['tasks'][key]['last_result'],'accepted_candidate_invalidated');self.assertEqual((ws/'review_en.tex').read_text(),before)
 def test_coherence_transport_failure_has_a_bounded_recovery_attempt(self):
  from autonomous_review import coherence_review
  class API:
   calls=0;max_tokens=1000
   def chat(self,*args,**kwargs):
    self.calls+=1
    if self.calls==1:raise RuntimeError('API attempts failed: simulated IncompleteRead')
    return json.dumps({'issues':[]})
  with tempfile.TemporaryDirectory() as t:
   ws=Path(t);self.source(ws);run,state=bootstrap(ws,9);state['work_deadline']=state['deadline'];state['coherence_rounds']=1;api=API()
   self.assertEqual(coherence_review(run,state,api),[]);self.assertEqual(api.calls,2)
 def test_coherence_quote_error_retries_review_without_discarding_progress(self):
  from autonomous_review import coherence_review
  class API:
   calls=0;max_tokens=1000
   def chat(self,*args,**kwargs):
    self.calls+=1
    return json.dumps({'issues':[{'unit_id':'unit_001','id':'I1','severity':'major','passage':'Invented passage','reason':'A concern','required_change':'Fix it'}] if self.calls==1 else []})
  with tempfile.TemporaryDirectory() as t:
   ws=Path(t);self.source(ws);run,state=bootstrap(ws,9);state['work_deadline']=state['deadline'];state['coherence_rounds']=1;api=API()
   self.assertEqual(coherence_review(run,state,api),[]);self.assertEqual(api.calls,2)
 def test_small_whole_unit_review_has_review_output_and_time_budgets(self):
  class API:
   max_tokens=1000
   def chat(self,*args,**kwargs):return 'ok'
  with tempfile.TemporaryDirectory() as t:
   api=API();state={'deadline':time.time()+1200}
   checkpoint_call(api,state,Path(t)/'state.json','review',{'candidate':'Current draft','study_comparisons':[]},'reviewer')
   self.assertEqual(api.call_timeout,600);self.assertGreaterEqual(api.max_tokens,12000)
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
   self.assertIn(r'\bibitem[Author(2020)]{A}',Path(r['english']).read_text());self.assertEqual(r['bibliography_added'],['A'])
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
    def chat(self,system,user,**k):
     packets=json.loads(user)['units'];target=next(p for p in packets if p['unit_id']==key);other=next(p for p in packets if p['unit_id']!=key)
     return json.dumps({'issues':[{'unit_id':key,'id':'contradiction','severity':'major','passage_id':target['passage_options'][0]['id'],'related_passage_ids':[other['passage_options'][0]['id']],'reason':'Inconsistent conclusion','required_change':'Reconcile conclusion'}]})
   state['deadline']=time.time()+30;state['work_deadline']=state['deadline'];coherence_review(run,state,GlobalAPI())
   self.assertEqual(assemble(run,state)['accepted_units'],1)
   remaining=next(i for i in report['accepted_ids'] if i!=key);snapshot=run/'unit_studies'/(remaining+'.json')
   matrix=json.loads(snapshot.read_text());matrix['studies'][0]['fields']['reported_finding']['value']='Changed evidence contract'
   snapshot.write_text(json.dumps(matrix))
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
   w=Path(t);self.source(w);p=w/'review_en.tex';p.write_text(p.read_text().replace(r'\end{document}',r'\includegraphics{figure}\input{extra}\end{document}'));(w/'figure.pdf').write_bytes(b'figure');(w/'extra.tex').write_text('extra')
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
 def test_indexed_extraction_maps_only_requested_axes(self):
  from autonomous_review import normalize_study
  row={'citekey':'A','comparisons':[{'axis_index':0,'status':'not_accessible','value':''},{'axis_index':1,'status':'supported','value':'bounded','locator':'p1','excerpt':'quoted'}]}
  result=normalize_study(row,['long axis one','long axis two'])
  self.assertEqual(set(result['fields']),{'long axis one','long axis two'})
  self.assertEqual(result['fields']['long axis two']['excerpt'],'quoted')
  row['comparisons'].append({'axis_index':9,'status':'supported'})
  with self.assertRaises(ValueError):normalize_study(row,['long axis one','long axis two'])
 def test_cached_invalid_plan_is_rejected_before_use(self):
  from autonomous_review import validate_argument
  with self.assertRaises(ValueError):validate_argument({'argument':{'study_keys':[]}}, {'A'}, {'A'})
 def test_source_validation_checks_cached_fields_and_exact_quotes(self):
  from autonomous_review import validate_study
  packet={'citekey':'A','chunks':[{'text':'An exact source quote'}]}
  bad={'citekey':'A','fields':{'axis':{'status':'supported','value':'claim','locator':'p1','excerpt':'Invented quote'}}}
  with self.assertRaises(ValueError):validate_study(bad,['axis'],packet)
  bad['fields']['axis']['excerpt']='exact source quote';validate_study(bad,['axis'],packet)

 def test_assembly_does_not_copy_unrelated_private_project_files(self):
  with tempfile.TemporaryDirectory() as t:
   w=Path(t);self.source(w);private=w/'autonomous_diagnostics';private.mkdir();(private/'unrelated.tex').write_text('unrelated manuscript')
   run,state=bootstrap(w,9);result=assemble(run,state)
   self.assertFalse((Path(result['english']).parent/'autonomous_diagnostics/unrelated.tex').exists())
 def test_reviewer_transport_and_format_recovery_reuses_writer_draft(self):
  from unittest.mock import patch
  from synthesis_pipeline import CRITERIA
  for mode in ('format','outage','grounding'):
   class API:
    def __init__(self):self.writes=0;self.reviews=0
    def chat(self,system,user,role='writer'):
     p=json.loads(user)
     if 'required_original_keys' in p:
      return json.dumps({'argument':{'question':'What is supported?','thesis':'Bounded evidence.','comparison_axes':['finding'],'study_keys':['A'],'paragraph_plan':[{'role':'comparison','point':'Assess bounds'}],'synthesis_claim':'Bounded inference.','limitations':'One source.','open_question':'What transfers?','sparse_evidence_reason':'Fixture single study','kind':'core'},'studies':[{'citekey':'A','fields':{'finding':{'status':'supported','value':'Bounded','locator':'p1','excerpt':'A quoted finding'}}}]})
     if role=='writer':self.writes+=1;return p['body']+'\n'+('A bounded comparison of assumptions and observed evidence. '*4)
     self.reviews+=1
     if self.reviews==1:
      if mode=='outage':raise RuntimeError('API attempts failed: simulated reviewer outage')
      if mode=='grounding':return json.dumps({'accept':True,'issues':[],'criteria':{k:{'status':'pass','explanation':'Grounded mock judgment','passages':['This passage was invented']} for k in CRITERIA}})
      return '{"accept":true,"issues":[],"criteria":[]}'
     return json.dumps({'accept':True,'issues':[],'criteria':{k:{'status':'pass','explanation':'Grounded mock judgment','passages':[p['candidate'][-40:]]} for k in CRITERIA}})
   with tempfile.TemporaryDirectory() as t:
    w=Path(t);self.source(w);api=API()
    with patch('autonomous_review.heartbeat'),patch('threading.Event.wait',return_value=False):
     report=run_review(w,hours=.001,reserve_minutes=0,max_visits=1,translate=False,api_factory=lambda:api)
    self.assertEqual(report['accepted_units'],2);self.assertEqual(api.writes,2)
 def test_blocked_evidence_is_rechecked_on_resume(self):
  with tempfile.TemporaryDirectory() as t:
   w=Path(t);self.source(w);run,state=bootstrap(w,9);key=next(iter(state['tasks']));state['tasks'][key].update(status='blocked_evidence',visits=3)
   (run/'autonomous_state.json').write_text(json.dumps(state));_,resumed=bootstrap(w,9)
   self.assertEqual(resumed['tasks'][key]['status'],'retry');self.assertLess(resumed['tasks'][key]['visits'],3)
 def test_assembly_quarantines_stale_outputs_even_without_delivery(self):
  with tempfile.TemporaryDirectory() as t:
   w=Path(t);self.source(w);run,state=bootstrap(w,9);out=run/'output';out.mkdir();(out/'review_zh.tex').write_text('stale translation');(out/'output').mkdir();(out/'output/review_en.pdf').write_bytes(b'stale')
   assemble(run,state)
   self.assertFalse((out/'review_zh.tex').exists());self.assertFalse((out/'output/review_en.pdf').exists())
 def test_source_ids_materialize_exact_immutable_evidence(self):
  from autonomous_review import indexed_source,materialize_evidence
  packet={'citekey':'A','chunks':[{'locator':'offset 0','text':'PDF text contains 锟紺 unusual punctuation, and this is an exact source sentence.'}]}
  indexed=indexed_source(packet);identifier=indexed['evidence_spans'][0]['id']
  row={'citekey':'A','fields':{'axis':{'status':'supported','value':'A bounded interpretation','evidence_ids':[identifier]}}}
  result=materialize_evidence(row,indexed)
  self.assertEqual(result['fields']['axis']['excerpt'],packet['chunks'][0]['text'])
  row['fields']['axis']['evidence_ids']=['invented']
  with self.assertRaises(ValueError):materialize_evidence(row,indexed)
 def test_repeated_source_quotes_are_deduplicated_without_losing_values(self):
  from autonomous_review import compact_evidence_payload
  payload={'study_comparisons':[{'citekey':'A','fields':{'x':{'value':'one','locator':'p1','excerpt':'Exact source quote '*30},'y':{'value':'two','locator':'p1','excerpt':'Exact source quote '*30}}}]}
  result=compact_evidence_payload(payload);fields=result['study_comparisons'][0]['fields']
  self.assertEqual(fields['x']['excerpt_ref'],fields['y']['excerpt_ref']);self.assertEqual(len(result['source_quotes']),1)
  self.assertEqual(result['source_quotes'][fields['x']['excerpt_ref']]['excerpt'],'Exact source quote '*30)
  self.assertEqual(payload['study_comparisons'][0]['fields']['x']['excerpt'],'Exact source quote '*30)
 def test_whole_unit_request_gets_stage_budget_but_never_exceeds_run_deadline(self):
  class API:
   def chat(self,*a,**k):
    self.observed_remaining=self.deadline-time.time();return 'ok'
  with tempfile.TemporaryDirectory() as t:
   api=API();state={'deadline':time.time()+3600}
   checkpoint_call(api,state,Path(t)/'state.json','s',{'body':'x','study_comparisons':[]},'writer')
   self.assertGreater(api.observed_remaining,300)
   state['deadline']=time.time()+10
   checkpoint_call(api,state,Path(t)/'state.json','s',{'body':'x','study_comparisons':[]},'writer')
   self.assertLessEqual(api.observed_remaining,10)
 def test_evidence_compaction_never_increases_large_payload_size(self):
  from autonomous_review import compact_evidence_payload
  p={'study_comparisons':[{'citekey':'A','fields':{str(i):{'excerpt':'Unique quote '+str(i),'locator':'p'+str(i)} for i in range(20)}}]}
  self.assertLessEqual(len(json.dumps(compact_evidence_payload(p))),len(json.dumps(p)))

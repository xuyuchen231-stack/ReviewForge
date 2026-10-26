import hashlib,json,tempfile,unittest
from pathlib import Path
from synthesis_pipeline import initialize, audit_contract, revise_unit, review_verdict, CRITERIA

class SynthesisTests(unittest.TestCase):
 def test_repair_feedback_reuses_findings_without_repeating_criterion_quotes(self):
  from synthesis_pipeline import repair_feedback
  record={'attempt':1,'problems':['review_rejected'],'review':{'accept':False,'criteria':{'evidence_scope':{'status':'fail','explanation':'Distinguish random-split accuracy from unseen-policy transfer.','passages':['large quote'*300]}},'issues':[{'id':'M1','reason':'Compare validation conditions'}],'resolved_issue_ids':[]}}
  result=repair_feedback(record)
  self.assertEqual(result['review']['criteria']['evidence_scope'],{'status':'fail','explanation':'Distinguish random-split accuracy from unseen-policy transfer.'});self.assertEqual(result['review']['issues'],record['review']['issues']);self.assertIn('passages',record['review']['criteria']['evidence_scope'])
 def test_review_passage_ids_materialize_exact_body_and_reject_forgery(self):
  from synthesis_pipeline import review_passage_options,validate_review_response
  candidate=r'\subsection{Results}'+'\nActual supported interpretation.'
  option=review_passage_options(candidate)[0]
  v={'accept':True,'issues':[],'criteria':{k:{'status':'pass','explanation':'Specific judgment','passage_ids':[option['id']]} for k in CRITERIA}}
  self.assertTrue(validate_review_response(v,candidate));self.assertEqual(v['criteria']['question_answered']['passages'],['Actual supported interpretation.'])
  v['criteria']['question_answered']['passage_ids']=['invented']
  with self.assertRaisesRegex(ValueError,'passage'):validate_review_response(v,candidate)
 def test_child_coverage_handles_malformed_passage_inventory_as_rejection(self):
  candidate=r'\subsection{Transition}'+'\nA bridge.'
  self.assertFalse(review_verdict({'accept':False,'issues':[],'criteria':{'question_answered':{'passages':None}}},candidate)[0])
 def test_review_cannot_use_one_good_child_to_approve_untouched_other_child(self):
  candidate=r'\subsection{Comparison}'+'\nA grounded comparison of studies.\n'+r'\subsubsection{Transfer}'+'\nTransfer is important.'
  verdict={'accept':True,'issues':[],'criteria':{k:{'status':'pass','explanation':'Specific judgment','passages':['A grounded comparison of studies.']} for k in CRITERIA}}
  accepted,problems=review_verdict(verdict,candidate)
  self.assertFalse(accepted);self.assertIn('unassessed_subsection:Transfer',problems)
 def test_child_coverage_does_not_turn_scientific_failure_into_schema_retry(self):
  from synthesis_pipeline import validate_review_response
  candidate=r'\subsection{Comparison}'+'\nA grounded comparison of studies.\n'+r'\subsubsection{Transfer}'+'\nTransfer is important.'
  verdict={'accept':False,'issues':[],'criteria':{k:{'status':'fail','explanation':'Transfer remains a definition.','passages':['Transfer is important.']} for k in CRITERIA}}
  self.assertTrue(validate_review_response(verdict,candidate))
 def test_repair_budget_includes_previous_candidate_before_api_call(self):
  with tempfile.TemporaryDirectory() as t:
   ws=self.workspace(t);u=self.prepared(ws);folder=ws/'synthesis_candidates';folder.mkdir(exist_ok=True)
   (folder/(u['id']+'.json')).write_text(json.dumps({'status':'needs_revision','history':[]}),encoding='utf-8')
   (folder/(u['id']+'.tex')).write_text('x'*180001,encoding='utf-8')
   with self.assertRaisesRegex(ValueError,'context budget'):
    revise_unit(ws,u['id'],lambda *args:self.fail('Oversized repair reached API'),max_rounds=1)
 def test_synthesis_and_assembly_validate_existing_cross_unit_reference_targets(self):
  from autonomous_review import assemble
  with tempfile.TemporaryDirectory() as t:
   ws=self.workspace(t);p=ws/'review_en.tex';p.write_text(p.read_text(encoding='utf-8').replace(r'\end{document}',r'\subsection{Timing}'+'\n'+r'\begin{equation}\label{eq:known}a=b\end{equation}\end{document}'),encoding='utf-8');u=self.prepared(ws)
   def chat(s,p,r):return self.passing_chat(s,p,r)+r' See \eqref{eq:known}.' if r=='writer' else self.passing_chat(s,p,r)
   result=revise_unit(ws,u['id'],chat,max_rounds=1);self.assertEqual(result['status'],'model_review_passed')
   self.assertIn(u['id'],assemble(ws,{})['accepted_ids'])
 def test_repair_receives_original_context_for_legacy_cross_unit_findings(self):
  with tempfile.TemporaryDirectory() as t:
   ws=self.workspace(t);source=(ws/'review_en.tex').read_text(encoding='utf-8').replace(r'\end{document}',r'\subsection{Related}'+'\nA normative related statement. '+r'\cite{A}\end{document}');(ws/'review_en.tex').write_text(source,encoding='utf-8');u=self.prepared(ws)
   def first(system,payload,role):
    if role=='writer':return self.passing_chat(system,payload,role)
    verdict=json.loads(self.passing_chat(system,payload,role));verdict.update(accept=False,issues=[{'id':'I1','severity':'major','locator':'A definition','reason':'Compare the scope with unit_002.','required_evidence_or_change':'Clarify the normative scope.'}]);return json.dumps(verdict)
   revise_unit(ws,u['id'],first,max_rounds=1)
   def inspect(system,payload,role):
    context=payload['active_issue_details'][0]['cross_unit_context'];self.assertEqual(context[0]['unit_id'],'unit_002');self.assertIn('normative related statement',context[0]['passage']);self.assertEqual(context[0]['review_status'],'original_not_revalidated');raise RuntimeError('stop after context inspection')
   with self.assertRaisesRegex(RuntimeError,'stop after context inspection'):revise_unit(ws,u['id'],inspect,max_rounds=1)
 def test_grounded_negative_review_remains_a_scientific_rejection(self):
  from synthesis_pipeline import validate_review_response
  verdict={'accept':False,'issues':[],'criteria':{k:{'status':'fail','passages':['Actual text'],'explanation':'Comparison is insufficient.'} for k in CRITERIA}}
  self.assertTrue(validate_review_response(verdict,'Actual text'))
  self.assertFalse(review_verdict(verdict,'Actual text')[0])
 def test_bibliography_is_not_a_writing_unit(self):
  from synthesis_pipeline import units
  text='\\begin{document}\n\\section{X}\n\\subsection{Y}\nProse.\n\\begin{thebibliography}{99}\n\\bibitem{A} Reference\n\\end{thebibliography}\n\\end{document}'
  result=units(text)
  self.assertNotIn('bibitem',result[-1]['body'])
 def workspace(self,tmp):
  w=Path(tmp);(w/'review_en.tex').write_text('\\begin{document}\n\\section{Models}\n\\subsection{Parameters}\nA definition and an equation. \\cite{A,B}\n\\end{document}',encoding='utf-8')
  (w/'evidence_ledger.json').write_text(json.dumps({'entries':[{'citekey':k,'claim':'Narrow finding','source_id':k,'locator':'p1','excerpt':'An exact short passage','limitations':'Limited scope'} for k in ['A','B']]}))
  return w
 def prepared(self,w):
  initialize(w);p=json.loads((w/'synthesis_plan.json').read_text());u=next(u for u in p['units'] if u['heading']==r'\subsection{Parameters}')
  u.update(question='What is learned?',thesis='Parameter learning has conditional scope.',comparison_axes=['learned_component'],study_keys=['A','B'],paragraph_plan=[{'role':'comparison','point':'Compare parameter roles','study_keys':['A','B']}],synthesis_claim='The boundary depends on the retained model.',limitations='Validation differs.',open_question='Transfer remains uncertain.')
  p['sample_unit_id']=u['id'];(w/'synthesis_plan.json').write_text(json.dumps(p))
  rows=[{'citekey':k,'source_type':'full_text','fields':{'learned_component':{'status':'supported','value':'a conditional parameter','locator':'p1','excerpt':'An exact short passage'}}} for k in ['A','B']]
  (w/'study_comparisons.json').write_text(json.dumps({'studies':rows}));return u
 def test_scaffold_is_not_approval_and_never_changes_master(self):
  with tempfile.TemporaryDirectory() as t:
   w=self.workspace(t);before=(w/'review_en.tex').read_bytes();initialize(w)
   self.assertFalse(audit_contract(w)['ready']);self.assertEqual(before,(w/'review_en.tex').read_bytes())
   with self.assertRaises(FileExistsError):initialize(w)
 def test_abstract_cannot_support_unreported_split(self):
  with tempfile.TemporaryDirectory() as t:
   w=self.workspace(t);u=self.prepared(w)
   p=json.loads((w/'synthesis_plan.json').read_text());next(x for x in p['units'] if x['id']==u['id'])['comparison_axes']=['validation_split'];(w/'synthesis_plan.json').write_text(json.dumps(p))
   rows=json.loads((w/'study_comparisons.json').read_text());r=rows['studies'][0];r['source_type']='abstract_only';r['fields']['validation_split']={'status':'supported','value':'whole-batch holdout','locator':'abstract','excerpt':'An exact short passage'};(w/'study_comparisons.json').write_text(json.dumps(rows))
   report=audit_contract(w,u['id']);self.assertFalse(report['ready']);self.assertIn('abstract_detail_requires_explicit_evidence',str(report))
 def test_reviewer_cannot_accept_without_passage_based_depth_assessment(self):
  ok,issues=review_verdict({'accept':True,'issues':[]},'Definition and equation only.')
  self.assertFalse(ok)
 def test_rejected_rewrite_is_saved_but_master_is_unchanged(self):
  with tempfile.TemporaryDirectory() as t:
   w=self.workspace(t);u=self.prepared(w);before=(w/'review_en.tex').read_bytes()
   candidate='A definition and an equation. '+('More general explanation. '*8)+r'\cite{A,B}'
   calls=[]
   def chat(system,payload,role):
    calls.append(role)
    return candidate if role=='writer' else json.dumps({'accept':False,'issues':[{'severity':'major','reason':'Textbook description without comparison'}]})
   result=revise_unit(w,u['id'],chat,max_rounds=1)
   self.assertEqual(result['status'],'needs_revision');self.assertEqual(before,(w/'review_en.tex').read_bytes());self.assertEqual(calls,['writer','reviewer'])
 def test_stale_plan_blocks_api(self):
  with tempfile.TemporaryDirectory() as t:
   w=self.workspace(t);u=self.prepared(w);(w/'review_en.tex').write_text('changed')
   with self.assertRaises(ValueError):revise_unit(w,u['id'],lambda *a: self.fail('API called'))
 def test_fake_reviewer_passage_rejected(self):
  verdict={'accept':True,'issues':[],'criteria':{k:{'status':'pass','explanation':'Specific judgment','passages':['Invented passage']} for k in CRITERIA}}
  self.assertFalse(review_verdict(verdict,'Actual prose.')[0])
 def test_reviewer_outage_preserves_generated_candidate(self):
  with tempfile.TemporaryDirectory() as t:
   w=self.workspace(t);u=self.prepared(w);candidate=u['heading']+'\n'+('Comparative argument. '*15)+r'\cite{A,B}'
   def chat(system,payload,role):
    if role=='reviewer':raise RuntimeError('Provider outage')
    return candidate
   with self.assertRaises(RuntimeError):revise_unit(w,u['id'],chat,max_rounds=1)
   self.assertEqual((w/'synthesis_candidates'/(u['id']+'.tex')).read_text(),candidate)
   self.assertEqual(json.loads((w/'synthesis_candidates'/(u['id']+'.json')).read_text())['status'],'review_pending')
 def test_non_axis_supported_field_is_also_checked(self):
  with tempfile.TemporaryDirectory() as t:
   w=self.workspace(t);u=self.prepared(w);p=w/'study_comparisons.json';data=json.loads(p.read_text())
   data['studies'][0]['fields']['quantitative_results']={'status':'supported','value':'99% improvement','locator':'p99','excerpt':'Made-up result'};p.write_text(json.dumps(data))
   self.assertFalse(audit_contract(w,u['id'])['ready'])
 def test_previous_major_issue_requires_explicit_resolution(self):
  text='A concrete comparative conclusion.'
  v={'accept':True,'issues':[],'criteria':{k:{'status':'pass','explanation':'Specific judgment','passages':[text]} for k in CRITERIA}}
  self.assertFalse(review_verdict(v,text,prior_major=['M1'])[0])
 def passing_chat(self,system,payload,role):
  if role=='writer':return payload['body']+'\n'+('A conditional comparison follows the retained model and its evidence. '*5)
  text=payload['candidate']
  return json.dumps({'accept':True,'issues':[],'criteria':{k:{'status':'pass','explanation':'Mock reviewer judgment','passages':[text[-69:]]} for k in CRITERIA}})
 def test_last_accepted_survives_rejected_rerun(self):
  with tempfile.TemporaryDirectory() as t:
   w=self.workspace(t);u=self.prepared(w);first=revise_unit(w,u['id'],self.passing_chat,max_rounds=1)
   self.assertEqual(first['status'],'model_review_passed');accepted=w/'synthesis_candidates/accepted'/(u['id']+'.tex');old=accepted.read_bytes()
   def reject(s,p,r):return self.passing_chat(s,p,r) if r=='writer' else json.dumps({'accept':False,'issues':[]})
   revise_unit(w,u['id'],reject,max_rounds=1)
   self.assertEqual(accepted.read_bytes(),old)
   self.assertEqual(len(list((w/'synthesis_candidates/runs').iterdir())),2)
 def test_approved_sample_invalidated_by_changed_study_contract(self):
  with tempfile.TemporaryDirectory() as t:
   w=self.workspace(t);p=w/'review_en.tex';p.write_text(p.read_text().replace(r'\end{document}',r'\subsection{Second}'+'\nMore text. '+r'\cite{A,B}\end{document}'))
   u=self.prepared(w);pp=w/'synthesis_plan.json';plan=json.loads(pp.read_text());other=next(x for x in plan['units'] if x['id']!=u['id'])
   for k,v in u.items():
    if k not in ('id','heading','source_sha256'):other[k]=v
   pp.write_text(json.dumps(plan));revise_unit(w,u['id'],self.passing_chat,max_rounds=1)
   folder=w/'synthesis_candidates/accepted';sample=folder/(u['id']+'.tex');review=sample.with_suffix('.json')
   plan['calibration']={'approved':True,'approved_by':'user','sample_sha256':hashlib.sha256(sample.read_bytes()).hexdigest(),'review_sha256':hashlib.sha256(review.read_bytes()).hexdigest()};pp.write_text(json.dumps(plan))
   matrix=w/'study_comparisons.json';data=json.loads(matrix.read_text());data['studies'][0]['fields']['learned_component']['value']='A changed interpretation';matrix.write_text(json.dumps(data))
   with self.assertRaisesRegex(ValueError,'changed'):revise_unit(w,other['id'],lambda *a:self.fail('API called after stale calibration'))
 def test_major_issues_survive_another_invocation(self):
  with tempfile.TemporaryDirectory() as t:
   w=self.workspace(t);u=self.prepared(w)
   def reject(s,p,r):
    if r=='writer':return self.passing_chat(s,p,r)
    return json.dumps({'accept':False,'issues':[{'id':'M1','severity':'major','locator':'opening','reason':'No comparative evidence','required_evidence_or_change':'Compare actual study constructions'}]})
   revise_unit(w,u['id'],reject,max_rounds=1)
   result=revise_unit(w,u['id'],self.passing_chat,max_rounds=1)
   self.assertEqual(result['status'],'needs_revision')
   self.assertIn('previous_major_issues_unresolved',str(result))
 def test_unit_study_snapshot_is_stable_when_other_unit_updates_catalogue(self):
  from synthesis_pipeline import matrix_for_unit,contract_digest,unit_evidence,read,units
  with tempfile.TemporaryDirectory() as t:
   w=self.workspace(t);u=self.prepared(w);matrix=read(w/'study_comparisons.json');folder=w/'unit_studies';folder.mkdir();(folder/(u['id']+'.json')).write_text(json.dumps(matrix))
   plan=read(w/'synthesis_plan.json');actual=next(x for x in units((w/'review_en.tex').read_text()) if x['id']==u['id']);before=contract_digest(plan,matrix_for_unit(w,u['id']),unit_evidence(w,actual,u),u['id'])
   matrix['studies'][0]['fields']['unrelated_axis']={'status':'supported','value':'Other-unit interpretation'};(w/'study_comparisons.json').write_text(json.dumps(matrix))
   self.assertEqual(before,contract_digest(plan,matrix_for_unit(w,u['id']),unit_evidence(w,actual,u),u['id']))
   self.assertTrue(audit_contract(w,u['id'])['ready'])
 def test_reviewer_schema_errors_are_safe_rejections(self):
  for malformed in [{'accept':True,'issues':[],'criteria':[]},{'accept':True,'issues':[],'criteria':{'question_answered':[]}}]:
   self.assertFalse(review_verdict(malformed,'Actual prose')[0])
 def test_grounded_resolutions_do_not_resurrect_on_later_rounds(self):
  with tempfile.TemporaryDirectory() as t:
   w=self.workspace(t);u=self.prepared(w);rounds=[0]
   def chat(s,p,r):
    if r=='writer':return self.passing_chat(s,p,r)
    rounds[0]+=1;v=json.loads(self.passing_chat(s,p,r));n=rounds[0];v['accept']=n==3
    if n<3:v['issues']=[{'id':'A' if n==1 else 'B','severity':'major','locator':p['candidate'][-40:],'reason':'Specific problem','required_evidence_or_change':'Repair this problem'}]
    if n>1:
     key='A' if n==2 else 'B';v['resolved_issue_ids']=[key];v['resolutions']=[{'issue_id':key,'explanation':'Resolved in quoted text','passages':[p['candidate'][-40:]]}]
    return json.dumps(v)
   self.assertEqual(revise_unit(w,u['id'],chat,max_rounds=1)['status'],'needs_revision')
   second=revise_unit(w,u['id'],chat,max_rounds=1);self.assertEqual(second['open_major_issues'],['B'])
   self.assertEqual(revise_unit(w,u['id'],chat,max_rounds=1)['status'],'model_review_passed')
 def test_review_schema_rejects_malformed_issues_and_resolutions(self):
  from synthesis_pipeline import review_schema
  base={'accept':False,'issues':[],'criteria':{k:{'status':'fail','explanation':'Concrete problem','passages':['text']} for k in CRITERIA}}
  for extra in [{'issues':[None]},{'issues':[{'id':'A','severity':'major'}]},{'resolved_issue_ids':'A'},{'resolutions':[{'issue_id':'A'}]}]:
   self.assertFalse(review_schema({**base,**extra}))
 def test_writer_receives_explicit_original_citation_inventory_for_repairs(self):
  with tempfile.TemporaryDirectory() as t:
   w=self.workspace(t);u=self.prepared(w);calls=[0]
   def chat(s,p,r):
    if r=='writer':
     self.assertEqual(p['required_citation_keys'],['A','B']);calls[0]+=1
     return self.passing_chat(s,p,r).replace(r'\cite{A,B}',r'\cite{A}') if calls[0]==1 else self.passing_chat(s,p,r)
    return self.passing_chat(s,p,r)
   result=revise_unit(w,u['id'],chat,max_rounds=2)
   self.assertEqual(result['status'],'model_review_passed')
   self.assertIn('B',result['history'][0]['problems'][0])

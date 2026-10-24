import hashlib,json,tempfile,unittest
from pathlib import Path
from synthesis_pipeline import initialize, audit_contract, revise_unit, review_verdict, CRITERIA

class SynthesisTests(unittest.TestCase):
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

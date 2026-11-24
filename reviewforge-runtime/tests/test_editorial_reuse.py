import json,tempfile,unittest
from pathlib import Path
from editorial_reuse import repair_locations,make_receipt,restore_receipt,prepare_recheck,merge_recheck
from editorial_refinement import CHECKS
class ReuseTests(unittest.TestCase):
 def review(self,text):return dict(accept=True,explanation='Full current text checked',issues=[],citation_checks=[],issue_resolutions=[{'id':'r','status':'resolved','current_quote':text,'reason':'Actual full review completed'}],**{k:True for k in CHECKS})
 def test_location_repair_sends_no_facts_and_cannot_change_verdict(self):
  text='Exact current manuscript paragraph.';review=self.review('Generic summary, not a source quote');seen=[]
  context={'selected_citekeys':[],'anchors':[],'canonical_studies':[{'PRIVATE_FULL_SOURCE':'x'*90000}],'required_primary_evidence':['x'*90000],'revision_requirements':[{'id':'r','required_citekeys':[]}]}
  def chat(system,payload,role):
   seen.append(payload)
   self.assertNotIn('required_primary_evidence',payload);self.assertNotIn('canonical_studies',json.dumps(payload))
   return json.dumps({'locations':[{'target':'resolution:0','option_id':payload['fields'][0]['options'][0]['id']}],'accept':False,'scope_preserved':False})
  with tempfile.TemporaryDirectory() as d:
   r={'history':[]};result=repair_locations(review,context,text,[],chat,r,Path(d)/'c.json',None)
   self.assertEqual(result['issue_resolutions'][0]['current_quote'],text);self.assertTrue(result['accept']);self.assertTrue(result['scope_preserved']);self.assertEqual(len(seen),1)
 def test_location_repair_never_resolves_a_scientific_rejection(self):
  text='Exact current manuscript paragraph.';review=self.review('Not a real quote');review['accept']=False;review['scope_preserved']=False;review['issue_resolutions'][0]['status']='unresolved'
  def chat(system,payload,role):return json.dumps({'locations':[{'target':'resolution:0','option_id':payload['fields'][0]['options'][0]['id']}],'accept':True,'issue_resolutions':[{'status':'resolved'}]})
  with tempfile.TemporaryDirectory() as d:
   result=repair_locations(review,{'revision_requirements':[{'id':'r'}]},text,[],chat,{'history':[]},Path(d)/'c.json',None)
   self.assertFalse(result['accept']);self.assertFalse(result['scope_preserved']);self.assertEqual(result['issue_resolutions'][0]['status'],'unresolved')
 def test_receipt_only_reuses_exact_accepted_candidate_and_contract(self):
  text='Exact current manuscript paragraph.';context={'selected_citekeys':[],'anchors':[],'revision_requirements':[{'id':'r'}]};review=self.review(text)
  r={'binding_sha256':'bound','source_sha256':'source','candidate':text,'review':review,'accepted':True,'changes':[],'citation_audit':{'complete':True,'unsupported':[],'checks':[]}}
  proof=make_receipt(r,context)
  blocked={**r,'accepted':False,'writer_calls':3,'review_calls':5}
  self.assertTrue(restore_receipt(blocked,context,proof));self.assertEqual(blocked['writer_calls'],3);self.assertEqual(blocked['review_calls'],5)
  self.assertFalse(restore_receipt({**blocked,'candidate':text+' Changed'},context,proof))
  self.assertFalse(restore_receipt({**blocked,'binding_sha256':'other'},context,proof))
  self.assertFalse(restore_receipt(blocked,{**context,'revision_requirements':[{'id':'new'}]},proof))
 def test_later_negative_review_cannot_be_erased_by_receipt(self):
  text='Exact current manuscript paragraph.';context={'selected_citekeys':[],'anchors':[]};r={'binding_sha256':'b','source_sha256':'s','candidate':text,'review':dict(accept=True,explanation='Pass',issues=[],**{k:True for k in CHECKS}),'accepted':True,'changes':[],'citation_audit':{'complete':True,'unsupported':[],'checks':[]}}
  proof=make_receipt(r,context)
  r.update(accepted=False,history=[{'candidate_sha256':__import__('editorial_refinement').sha(text),'review':{'accept':False,'issues':[{'kind':'current','quote':text,'check':'scope_preserved'}]}}])
  self.assertFalse(restore_receipt(r,context,proof))
 def recheck_case(self):
  from editorial_reuse import _digest
  from editorial_refinement import sha
  a=r'An exact supported statement about organism A \cite{A}.'
  b=r'Old rate description for organism B \cite{B}.'
  old=a+'\n\n'+('Other mathematical reasoning. '*30)+'\n\n'+b
  new=old.replace('Old rate description','Explicit state-based rate description')
  ctx={'selected_citekeys':['A','B'],'anchors':[{'citekey':'A'},{'citekey':'B'}],'canonical_studies':[{'citekey':'A','facts':{'value':'Exact A'}},{'citekey':'B','facts':{'value':'Exact B'}}],'revision_requirements':[]}
  review=dict(accept=True,explanation='Fully reviewed',issues=[],citation_checks=[{'citekey':k,'passage':p,'status':'supported','reason':'Exact source support'} for k,p in [('A',a),('B',b)]],**{k:True for k in CHECKS})
  parent={'binding_sha256':'same','context_sha256':_digest(ctx),'candidate':old,'review':review}
  return old,new,ctx,parent
 def test_recheck_keeps_full_current_text_but_only_changed_sources(self):
  old,new,ctx,parent=self.recheck_case();plan=prepare_recheck({'binding_sha256':'same'},parent,ctx,new)
  self.assertEqual(plan['context']['selected_citekeys'],['B']);self.assertEqual([x['citekey'] for x in plan['inherited_citations']],['A'])
  report=dict(accept=True,explanation='Changed relation checked',issues=[],citation_checks=[{'citekey':'B','passage':new.split('\n\n')[-1],'status':'supported','reason':'Checked changed B'}],**{k:True for k in CHECKS})
  merged=merge_recheck(report,plan,ctx,new)
  self.assertEqual({x['citekey'] for x in merged['citation_checks']},{'A','B'})
  self.assertEqual(ctx['selected_citekeys'],['A','B'])
 def test_recheck_cannot_reuse_changed_evidence_or_ignore_required_source(self):
  old,new,ctx,parent=self.recheck_case();parent['context_sha256']='different'
  self.assertIsNone(prepare_recheck({'binding_sha256':'same'},parent,ctx,new))
 def test_recheck_preserves_new_negative_about_an_inherited_source(self):
  old,new,ctx,parent=self.recheck_case();plan=prepare_recheck({'binding_sha256':'same'},parent,ctx,new)
  report=dict(accept=False,explanation='Conflict found',issues=[],citation_checks=[{'citekey':'A','passage':old.split('\n\n')[0],'status':'unsupported','reason':'New conflict'},{'citekey':'B','passage':new.split('\n\n')[-1],'status':'supported','reason':'Checked B'}],**{k:True for k in CHECKS})
  merged=merge_recheck(report,plan,ctx,new)
  self.assertFalse(merged['accept']);self.assertIn('unsupported',[x['status'] for x in merged['citation_checks'] if x['citekey']=='A'])
 def test_receipt_preserves_all_later_negative_event_types(self):
  import copy
  text='Exact current manuscript paragraph.';context={'selected_citekeys':[],'anchors':[]};r={'binding_sha256':'b','source_sha256':'s','candidate':text,'review':dict(accept=True,explanation='Pass',issues=[],**{k:True for k in CHECKS}),'accepted':True,'changes':[],'citation_audit':{'complete':True,'unsupported':[],'checks':[]}}
  proof=make_receipt(r,context)
  for name in ('review','source_review','requested_evidence_review','citation_metadata_review','block_metadata_review'):
   bad={'accept':True,'citation_checks':[{'citekey':'A','status':'unsupported'}]}
   changed=copy.deepcopy(r);changed.update(accepted=False,history=[{name:bad}])
   self.assertFalse(restore_receipt(changed,context,proof),name)
  changed=copy.deepcopy(r);changed['review']={**r['review'],'no_new_claims':False};self.assertFalse(restore_receipt(changed,context,proof))
 def test_requested_evidence_payload_contains_only_disputed_source(self):
  from unittest.mock import patch
  from editorial_reuse import resolve_requested_evidence
  a=r'Exact already supported A claim \cite{A}.';b=r'Exact disputed B model claim \cite{B}.';text=a+'\n\n'+b
  context={'selected_citekeys':['A','B'],'anchors':[{'citekey':'A'},{'citekey':'B'}],'canonical_studies':[],'revision_requirements':[{'id':'b','required_citekeys':['B']}]}
  review=dict(accept=False,explanation='Need original B',issues=[{'kind':'current','quote':b,'check':'scope_preserved','fix':'Check B original'}],citation_checks=[{'citekey':'A','passage':a,'status':'supported','reason':'Already verified A'},{'citekey':'B','passage':b,'status':'uncertain','reason':'Need B evidence'}],evidence_requests=[{'citekey':'B','fields':['mechanism']}],issue_resolutions=[{'id':'b','status':'unresolved','current_quote':b,'reason':'Need B'}],**{k:True for k in CHECKS})
  study={'citekey':'B','facts':{'mechanism':{'id':'b1','value':'Exact B with material qualification','anchors':[{'excerpt':'Original B quote','source_sha256':'sha'}]}}}
  def chat(system,payload,role):
   self.assertEqual({f['citekey'] for f in payload['requested_primary_evidence']},{'B'})
   self.assertNotIn('canonical_studies',payload)
   return json.dumps(dict(accept=True,explanation='B independently resolved',issues=[],evidence_requests=[],citation_checks=[{'citekey':'B','passage':b,'status':'qualified','reason':'Exact primary B with qualification'}],issue_resolutions=[{'id':'b','status':'resolved','current_quote':b,'reason':'Primary source B verified'}],**{k:True for k in CHECKS}))
  with tempfile.TemporaryDirectory() as d,patch('study_registry.load_registry',return_value={}),patch('study_registry.facts_for_studies',return_value=[study]):
   result=resolve_requested_evidence(review,context,text,chat,{'history':[]},Path(d)/'r.json',None,Path(d))
   self.assertTrue(result['accept']);self.assertEqual([x for x in result['citation_checks'] if x['citekey']=='A'],[review['citation_checks'][0]])
 def test_requesting_an_inherited_source_fetches_it_without_rechecking_other_sources(self):
  from unittest.mock import patch
  from editorial_joint import process_chunk,delta
  from editorial_refinement import sha
  old,new,ctx,parent=self.recheck_case();calls=[]
  def chat(system,payload,role):
   calls.append(payload['stage'])
   if payload['stage']=='joint':
    self.assertEqual(payload['citation_context']['selected_citekeys'],['B'])
    return json.dumps(dict(accept=False,explanation='Need original inherited A',issues=[],evidence_requests=[{'citekey':'A','fields':['mechanism']}],citation_checks=[{'citekey':'B','passage':new.split('\n\n')[-1],'status':'supported','reason':'Verified B'}],**{k:True for k in CHECKS}))
   self.assertEqual({f['citekey'] for f in payload['requested_primary_evidence']},{'A'})
   return json.dumps(dict(accept=True,explanation='A verified from original',issues=[],evidence_requests=[],citation_checks=[{'citekey':'A','passage':old.split('\n\n')[0],'status':'supported','reason':'Verified requested A'}],**{k:True for k in CHECKS}))
  study={'citekey':'A','facts':{'mechanism':{'id':'a1','value':'Exact A source','anchors':[{'excerpt':'Original A','source_sha256':'sha'}]}}}
  with tempfile.TemporaryDirectory() as d,patch('study_registry.load_registry',return_value={}),patch('study_registry.facts_for_studies',return_value=[study]):
   cache=Path(d)/'c.json';cache.write_text(json.dumps({'source_sha256':sha(old),'binding_sha256':'same','candidate':new,'writer_calls':3,'review_calls':0,'accepted':False,'pending_review':True,'history':[],'changes':delta(old,new),'recheck_parent':parent}),encoding='utf-8')
   result=process_chunk(old,chat,cache,None,ctx,'same',Path(d))
   self.assertTrue(result['accepted']);self.assertEqual(result['writer_calls'],3);self.assertEqual(calls,['joint','requested_evidence_only'])
 def test_scoped_source_response_preserves_unrelated_new_unresolved_requirement(self):
  from unittest.mock import patch
  from editorial_reuse import resolve_requested_evidence
  a=r'Exact already supported A claim \cite{A}.';b=r'Exact disputed B model claim \cite{B}.';text=a+'\n\n'+b
  ctx={'selected_citekeys':['A','B'],'anchors':[{'citekey':'A'},{'citekey':'B'}],'canonical_studies':[],'revision_requirements':[{'id':'a','required_citekeys':['A']},{'id':'b','required_citekeys':['B']}]}
  review=dict(accept=False,explanation='Need B',issues=[],evidence_requests=[{'citekey':'B','fields':['mechanism']}],citation_checks=[{'citekey':'A','passage':a,'status':'supported','reason':'A checked'},{'citekey':'B','passage':b,'status':'uncertain','reason':'Need B'}],issue_resolutions=[{'id':'a','status':'resolved','current_quote':a,'reason':'A done'},{'id':'b','status':'unresolved','current_quote':b,'reason':'B open'}],**{k:True for k in CHECKS})
  answer=dict(accept=True,explanation='B verified but new A conflict',issues=[],evidence_requests=[],citation_checks=[{'citekey':'B','passage':b,'status':'supported','reason':'B checked'}],issue_resolutions=[{'id':'a','status':'unresolved','current_quote':a,'reason':'New A conflict'},{'id':'b','status':'resolved','current_quote':b,'reason':'B done'}],**{k:True for k in CHECKS})
  study={'citekey':'B','facts':{'mechanism':{'id':'b1','value':'Exact B','anchors':[{'excerpt':'Original B','source_sha256':'sha'}]}}}
  with tempfile.TemporaryDirectory() as d,patch('study_registry.load_registry',return_value={}),patch('study_registry.facts_for_studies',return_value=[study]):
   result=resolve_requested_evidence(review,ctx,text,lambda *args:json.dumps(answer),{'history':[]},Path(d)/'c.json',None,Path(d))
   self.assertFalse(result['accept']);self.assertEqual([x['status'] for x in result['issue_resolutions'] if x['id']=='a'],['unresolved'])
 def test_failed_format_repair_never_sends_manuscript_to_writer(self):
  from editorial_joint import process_chunk
  from editorial_refinement import sha
  text='Exact current manuscript paragraph.';calls=[]
  context={'selected_citekeys':[],'anchors':[],'canonical_studies':[],'revision_requirements':[{'id':'r'}]}
  def chat(system,payload,role):
   calls.append(role);self.assertEqual(role,'reviewer')
   if payload['stage']=='review_locations':return json.dumps({'locations':[{'target':'resolution:0','option_id':'INVALID'}]})
   return json.dumps(self.review('A generic invented summary rather than source text'))
  with tempfile.TemporaryDirectory() as d:
   cache=Path(d)/'r.json';cache.write_text(json.dumps({'source_sha256':sha(text),'binding_sha256':'b','candidate':text,'writer_calls':2,'review_calls':0,'accepted':False,'pending_review':True,'history':[],'changes':[]}),encoding='utf-8')
   result=process_chunk(text,chat,cache,None,context,'b')
   self.assertFalse(result['accepted']);self.assertTrue(result['terminal']);self.assertEqual(result['writer_calls'],2);self.assertEqual(calls,['reviewer','reviewer'])
 def test_source_retrieval_keeps_prior_failed_editorial_check(self):
  from unittest.mock import patch
  from editorial_reuse import resolve_requested_evidence
  text=r'Exact current B statement \cite{B}.';ctx={'selected_citekeys':['B'],'anchors':[{'citekey':'B'}],'revision_requirements':[]}
  review=dict(accept=False,explanation='Evidence and editorial issue',issues=[],evidence_requests=[{'citekey':'B','fields':['mechanism']}],citation_checks=[{'citekey':'B','passage':text,'status':'uncertain','reason':'Need original'}],**{k:k!='editorial_goal_met' for k in CHECKS})
  answer=dict(accept=True,explanation='Source resolved',issues=[],evidence_requests=[],citation_checks=[{'citekey':'B','passage':text,'status':'supported','reason':'Original inspected'}],**{k:True for k in CHECKS})
  study={'citekey':'B','facts':{'mechanism':{'id':'b','value':'Exact B','anchors':[{'excerpt':'Primary B','source_sha256':'sha'}]}}};calls=[]
  def chat(*args):calls.append(1);return json.dumps(answer)
  with tempfile.TemporaryDirectory() as d,patch('study_registry.load_registry',return_value={}),patch('study_registry.facts_for_studies',return_value=[study]):
   result=resolve_requested_evidence(review,ctx,text,chat,{'history':[]},Path(d)/'r.json',None,Path(d))
   self.assertEqual(calls,[1]);self.assertFalse(result['editorial_goal_met']);self.assertFalse(result['accept']);self.assertEqual(result['evidence_requests'],[])
if __name__=='__main__':unittest.main()

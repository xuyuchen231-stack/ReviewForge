import json,tempfile,unittest
from pathlib import Path
from editorial_joint import requirement_errors,ask,decode_block_metadata,table_prose_preservation_errors
class ContractTests(unittest.TestCase):
 def test_generic_pass_does_not_resolve_a_documented_issue(self):
  context={'revision_requirements':[{'id':'pinto','required_citekeys':['A']}]}
  self.assertTrue(requirement_errors({'issue_resolutions':[]},'Current manuscript.',context))
 def test_resolution_requires_exact_current_quote_and_citation_support(self):
  context={'revision_requirements':[{'id':'pinto','required_citekeys':['A']}]}
  review={'issue_resolutions':[{'id':'pinto','status':'resolved','current_quote':'Current manuscript.','reason':'Original anchor supports this narrow claim'}],'citation_checks':[{'citekey':'A','status':'uncertain'}]}
  self.assertTrue(requirement_errors(review,'Current manuscript.',context))
  review['citation_checks'][0]['status']='qualified'
  self.assertFalse(requirement_errors(review,'Current manuscript.',context))
 def test_shared_budget_is_not_reset_by_new_source_binding(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);budget=p/'budget.json';budget.write_text(json.dumps({'writer_calls':3,'review_calls':1}),encoding='utf-8')
   with self.assertRaises(RuntimeError):ask(lambda *a:self.fail('No send'),'s',{},'writer',{'shared_budget_path':str(budget)},p/'cache.json',None)
   self.assertEqual(json.loads(budget.read_text())['writer_calls'],3)
 def test_block_metadata_is_copied_exactly_and_invalid_ids_rejected(self):
  text='First current paragraph.\n\nSecond current paragraph.'
  review={'issues':[{'kind':'current','current_block_id':'b002','check':'editorial_goal_met','fix':'Clarify'}],'issue_resolutions':[{'id':'a','current_block_id':'b001','status':'resolved','reason':'Verified'}]}
  result=decode_block_metadata(review,text)
  self.assertEqual(result['issues'][0]['quote'],'Second current paragraph.')
  self.assertEqual(result['issue_resolutions'][0]['current_quote'],'First current paragraph.')
  review['issues'][0]['current_block_id']='bad'
  with self.assertRaises(ValueError):decode_block_metadata(review,text)
 def test_only_located_plain_table_cells_can_change(self):
  before=r'\begin{table}Study & Reduced space & Nine 50-L runs.\\\end{table}'
  after=before.replace('Reduced space','PCA-reduced space')
  quote='Study & Reduced space & Nine 50-L runs.'
  self.assertFalse(table_prose_preservation_errors(before,after,[quote]))
  self.assertTrue(table_prose_preservation_errors(before,after,[]))
  self.assertTrue(table_prose_preservation_errors(before,after.replace('50-L','70-L'),[quote]))
 def test_saved_metadata_response_survives_interrupt_before_merge(self):
  from editorial_joint import repair_review_metadata,CHECKS
  from unittest.mock import patch
  calls=[];text='An exact current paragraph.'
  context={'revision_requirements':[{'id':'r','required_citekeys':[]}]}
  previous=dict(accept=True,explanation='Checked',issues=[],issue_resolutions=[{'id':'r','status':'resolved','current_quote':'Not an actual quote','reason':'Checked'}],**{k:True for k in CHECKS})
  answer=dict(previous,issue_resolutions=[{'id':'r','status':'resolved','current_block_id':'b001','reason':'Checked actual paragraph'}])
  def chat(*a):calls.append(1);return json.dumps(answer)
  with tempfile.TemporaryDirectory() as d:
   cache=Path(d)/'c.json';record={'history':[]}
   with patch('editorial_joint.decode_block_metadata',side_effect=RuntimeError('Injected interruption')):
    with self.assertRaises(RuntimeError):repair_review_metadata(previous,context,text,[],chat,record,cache,None)
   restored=json.loads(cache.read_text(encoding='utf-8'))
   repaired=repair_review_metadata(previous,context,text,[],chat,restored,cache,None)
   self.assertFalse(requirement_errors(repaired,text,context));self.assertEqual(calls,[1]);self.assertEqual(restored['review_calls'],1)
 def test_table_numeric_words_are_not_editable_prose(self):
  before=r'\begin{table}Study & Five independent batches & Value\\\end{table}'
  after=before.replace('Five','Six')
  self.assertTrue(table_prose_preservation_errors(before,after,['Study & Five independent batches & Value']))
 def test_revision_plan_rejects_other_source_before_any_request(self):
  from editorial_joint import refine_joint
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):refine_joint('Source.',Path(d),lambda *a:self.fail('No send'),revision_plan={'source_sha256':'wrong'})
 def test_public_joint_route_uses_existing_shared_budget_and_issue_contract(self):
  from editorial_joint import refine_joint
  from editorial_refinement import sha,CHECKS
  from unittest.mock import patch
  source='Current scientific paragraph.';calls=[]
  context={'selected_citekeys':[],'canonical_studies':[],'anchors':[],'missing_citekeys':[]}
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);budget=root/'budget.json';budget.write_text(json.dumps({'writer_calls':3,'review_calls':1}),encoding='utf-8')
   plan={'source_sha256':sha(source),'requirements_by_chunk':{'1':[{'id':'actual','required_citekeys':[]}]},'shared_budgets':{'1':str(budget)}}
   def chat(system,payload,role):
    calls.append(role)
    self.assertTrue(payload['citation_context']['revision_requirements'])
    return json.dumps(dict(accept=True,explanation='Verified actual text',issues=[],citation_checks=[],issue_resolutions=[{'id':'actual','status':'resolved','current_quote':source,'reason':'Verified evidence scope'}],**{k:True for k in CHECKS}))
   with patch('editorial_joint.evidence_index',return_value={}),patch('editorial_joint.scoped_context',return_value=context),patch('editorial_quality.citation_context',return_value=context),patch('study_registry.load_registry',return_value={}),patch('study_registry.facts_for_studies',return_value=[]):
    result=refine_joint(source,root/'job',chat,quality_workspace=root,revision_plan=plan)
   self.assertEqual(result['status'],'COMPLETE');self.assertEqual(calls,['reviewer'])
   counts=json.loads(budget.read_text());self.assertEqual(counts['writer_calls'],3);self.assertEqual(counts['review_calls'],2)
 def test_plan_cannot_silently_drop_required_sources_or_chunks(self):
  from editorial_joint import refine_joint
  from editorial_refinement import sha
  from unittest.mock import patch
  for extra,message in (({'required_citekeys':['ABSENT']},'Required citation absent'),({'requirements_by_chunk':{'9':[{'id':'lost'}]}},'outside actual source chunks')):
   with tempfile.TemporaryDirectory() as d,patch('editorial_joint.evidence_index',return_value={}):
    plan={'source_sha256':sha('Current paragraph.'),**extra}
    with self.assertRaisesRegex(ValueError,message):refine_joint('Current paragraph.',Path(d),lambda *a:self.fail('No send'),quality_workspace=Path(d),revision_plan=plan)
 def test_metadata_cache_cannot_replace_a_new_rejection_of_same_candidate(self):
  from editorial_joint import repair_review_metadata,CHECKS
  text='An exact current paragraph.';context={'revision_requirements':[{'id':'r','required_citekeys':[]}]};calls=[]
  prior=dict(accept=True,explanation='Checked',issues=[],issue_resolutions=[{'id':'r','status':'resolved','current_quote':'Invalid quote','reason':'Checked'}],**{k:True for k in CHECKS})
  answer=dict(prior,issue_resolutions=[{'id':'r','status':'resolved','current_block_id':'b001','reason':'Verified'}])
  def chat(*a):calls.append(1);return json.dumps(answer)
  with tempfile.TemporaryDirectory() as d:
   record={'history':[]};cache=Path(d)/'c.json'
   self.assertTrue(repair_review_metadata(prior,context,text,[],chat,record,cache,None)['accept'])
   later=dict(prior,accept=False,scope_preserved=False,issues=[{'kind':'current','quote':'Invalid quote','check':'scope_preserved','fix':'New negative finding'}])
   result=repair_review_metadata(later,context,text,[],chat,record,cache,None)
   self.assertFalse(result['accept']);self.assertFalse(result['scope_preserved']);self.assertEqual(calls,[1])
 def test_citation_cache_cannot_erase_later_unsupported_status(self):
  from editorial_joint import repair_citation_metadata,CHECKS
  from editorial_quality import citation_passage_options
  from editorial_refinement import sha
  text=r'Current study evidence \cite{A}. Other independent result \cite{B}.'
  ids={p['citekey']:p['id'] for p in citation_passage_options(text,['A','B'])}
  prior=dict(accept=True,explanation='Checked',issues=[],citation_checks=[{'citekey':'A','passage_id':ids['A'],'status':'supported','reason':'Bound A'},{'citekey':'B','passage_id':'bad','status':'supported','reason':'Bad B ID'}],**{k:True for k in CHECKS})
  context={'selected_citekeys':['A','B'],'anchors':[{'citekey':'A'},{'citekey':'B'}],'canonical_studies':[]};calls=[]
  def chat(*a):calls.append(1);return json.dumps({'candidate_sha256':sha(text),'citation_checks':[{'citekey':'B','passage_id':ids['B'],'status':'supported','reason':'Bound B'}]})
  with tempfile.TemporaryDirectory() as d:
   record={'history':[]};cache=Path(d)/'c.json';repair_citation_metadata(prior,context,text,chat,record,cache,None)
   import copy
   later=copy.deepcopy(prior);later['citation_checks'][0]['status']='unsupported'
   result=repair_citation_metadata(later,context,text,chat,record,cache,None)
   self.assertIn('unsupported',[r['status'] for r in result['citation_checks']]);self.assertEqual(calls,[1])
if __name__=='__main__':unittest.main()

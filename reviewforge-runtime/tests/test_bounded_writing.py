import tempfile, unittest
from pathlib import Path
from bounded_writing import write_units, source_blocks
from paragraph_review import paragraph_options
from test_paragraph_review import keep

class UnitWritingTests(unittest.TestCase):
 def test_identical_full_repair_stops_before_review_and_survives_restart(self):
  import json
  from reviewforge import atomic_json
  from pipeline_recovery import UnitRevisionsPending
  ask,review,calls=self.service()
  with tempfile.TemporaryDirectory() as d:
   write_units(ask,self.payload(),Path(d),'writer',review,{'facts'},{'f1':('A',{})})
   folder=next((Path(d)/'argument_units').iterdir());path=folder/'u2.json'
   row=json.loads(path.read_text());r={'accepted':False,'checks':{'facts':False},'issues':['Move misplaced evidence'],**keep(paragraph_options(row['candidate']['latex']))}
   r['paragraph_review'][0].update(decision='move',destination='supplement',reason='Move misplaced evidence')
   row.update(accepted=False,stage='reviewed',review=r);atomic_json(path,row)
   def unexpected(*args):raise AssertionError('Identical rejected draft must not be reviewed again')
   with self.assertRaises(UnitRevisionsPending):write_units(ask,self.payload(),Path(d),'writer',unexpected,{'facts'},{'f1':('A',{})})
   sent=len(calls)
   with self.assertRaises(UnitRevisionsPending):write_units(ask,self.payload(),Path(d),'writer',unexpected,{'facts'},{'f1':('A',{})})
   self.assertEqual(len(calls),sent);self.assertFalse(json.loads(path.read_text())['accepted'])
 def test_discourse_only_change_reuses_exact_local_approval_and_requires_assembly(self):
  import json
  from reviewforge import atomic_json
  ask,review,calls=self.service()
  with tempfile.TemporaryDirectory() as d:
   write_units(ask,self.payload(),Path(d),'writer',review,{'facts'},{'f1':('A',{})})
   folder=next((Path(d)/'argument_units').iterdir());path=folder/'u2.json'
   row=json.loads(path.read_text());row['context_sha256']='previous-discourse';atomic_json(path,row)
   def unexpected(*args):raise AssertionError('Unchanged accepted unit was re-reviewed')
   result=write_units(ask,self.payload(),Path(d),'writer',unexpected,{'facts'},{'f1':('A',{})})
   saved=json.loads(path.read_text());self.assertTrue(saved['accepted'])
   self.assertTrue(saved['assembly_context_recheck_required'])
   self.assertEqual(saved['review_context_sha256'],'previous-discourse')
   self.assertIn('_argument_units_binding',result)
 def test_source_change_still_invalidates_local_approval(self):
  import copy
  ask,review,calls=self.service()
  with tempfile.TemporaryDirectory() as d:
   write_units(ask,self.payload(),Path(d),'writer',review,{'facts'},{'f1':('A',{})})
   payload=copy.deepcopy(self.payload());payload['canonical_studies'][0]['facts']['count']['qualification']='Only the training cohort'
   write_units(ask,payload,Path(d),'writer',review,{'facts'},{'f1':('A',{})})
   self.assertEqual(calls.count(('units',None)),2)
 def test_unbound_previous_selection_requires_real_review_and_cannot_force_pass(self):
  import json
  from reviewforge import atomic_json
  from study_registry import signature
  from pipeline_recovery import UnitRevisionsPending
  ask,review,calls=self.service();reviewed=[]
  with tempfile.TemporaryDirectory() as d:
   candidate=write_units(ask,self.payload(),Path(d),'writer',review,{'facts'},{'f1':('A',{})})
   folder=next((Path(d)/'argument_units').iterdir())
   feedback={'accepted':False,'checks':{'facts':False},**keep(paragraph_options(candidate['latex']))}
   feedback['paragraph_review'][-1].update(decision='revise',reason='Second-unit defect',category='factual',severity='major')
   row=json.loads((folder/'u1.json').read_text());row.update(accepted=False,stage='needs_repair',repair_binding=signature([feedback,candidate['latex'],2]))
   atomic_json(folder/'u1.json',row)
   for u in ('u1','u2'):atomic_json(folder/(u+'.budget.json'),{'full_writes':4,'paragraph_patches':6})
   def reject(ask,payload,candidate,save,pending=None):
    reviewed.append(payload['unit_id']);r={'accepted':False,'checks':{'facts':False},'issues':['Actual unresolved fact'],**keep(paragraph_options(candidate['latex']))};save(r);return r,[]
   payload={**self.payload(),'repair_feedback':feedback,'previous_candidate':candidate['latex'],'_repair_generation':2}
   with self.assertRaises(UnitRevisionsPending):write_units(ask,payload,Path(d),'writer',reject,{'facts'},{'f1':('A',{})})
   self.assertEqual(reviewed,['u1']);saved=json.loads((folder/'u1.json').read_text());self.assertFalse(saved['accepted']);self.assertFalse(saved['review']['checks']['facts'])
 def test_complete_paragraph_map_routes_only_the_bound_unit_without_model_selection(self):
  import json
  from reviewforge import atomic_json
  from pipeline_recovery import UnitRevisionsPending
  ask,review,calls=self.service()
  with tempfile.TemporaryDirectory() as d:
   candidate=write_units(ask,self.payload(),Path(d),'writer',review,{'facts'},{'f1':('A',{})})
   folder=next((Path(d)/'argument_units').iterdir());atomic_json(folder/'u2.budget.json',{'full_writes':4,'paragraph_patches':6})
   feedback={'accepted':False,'checks':{'facts':False},**keep(paragraph_options(candidate['latex']))}
   feedback['paragraph_review'][-1].update(decision='revise',reason='Specific second-unit defect',severity='major',category='factual')
   payload={**self.payload(),'repair_feedback':feedback,'previous_candidate':candidate['latex'],'_repair_generation':2}
   with self.assertRaises(UnitRevisionsPending):write_units(ask,payload,Path(d),'writer',review,{'facts'},{'f1':('A',{})})
   self.assertTrue(json.loads((folder/'u1.json').read_text())['accepted'])
   self.assertFalse(json.loads((folder/'u2.json').read_text())['accepted'])
   self.assertNotIn(('unit_ids',None),calls)
 def test_scoped_repair_is_saved_as_unaccepted_even_when_budget_is_exhausted(self):
  import json
  from reviewforge import atomic_json
  from pipeline_recovery import UnitRevisionsPending
  ask,review,calls=self.service()
  with tempfile.TemporaryDirectory() as d:
   write_units(ask,self.payload(),Path(d),'writer',review,{'facts'},{'f1':('A',{})})
   folder=next((Path(d)/'argument_units').iterdir());path=folder/'u2.json'
   atomic_json(folder/'u2.budget.json',{'full_writes':4,'paragraph_patches':6})
   def scoped(system,payload,required,role):
    if required=='unit_ids':return {'unit_ids':['u2']}
    return ask(system,payload,required,role)
   payload={**self.payload(),'repair_feedback':{'issues':['Specific chapter defect']},'previous_candidate':'Complete old section','_repair_generation':2}
   with self.assertRaises(UnitRevisionsPending):write_units(scoped,payload,Path(d),'writer',review,{'facts'},{'f1':('A',{})})
   self.assertFalse(json.loads(path.read_text())['accepted'])
 def test_upstream_context_change_preserves_unresolved_repair_feedback(self):
  import json
  from reviewforge import atomic_json
  from pipeline_recovery import UnitRevisionsPending
  ask,review,calls=self.service()
  with tempfile.TemporaryDirectory() as d:
   write_units(ask,self.payload(),Path(d),'writer',review,{'facts'},{'f1':('A',{})})
   folder=next((Path(d)/'argument_units').iterdir());path=folder/'u2.json';row=json.loads(path.read_text())
   row.update(accepted=False,stage='needs_repair',context_sha256='old-context',review={'issues':['Specific unresolved evidence']})
   atomic_json(path,row);atomic_json(folder/'u2.budget.json',{'epoch':'old','full_writes':4,'paragraph_patches':6})
   with self.assertRaises(UnitRevisionsPending):write_units(ask,self.payload(),Path(d),'writer',review,{'facts'},{'f1':('A',{})})
   saved=json.loads(path.read_text());self.assertEqual(saved['review']['issues'],['Specific unresolved evidence'])
   self.assertFalse(saved['accepted'])
 def test_repair_edits_current_unit_while_original_review_sources_stay_unchanged(self):
  from bounded_writing import repair_writer_payload
  local={'original_material':'Long legacy survey','canonical_studies':[{'citekey':'A'},{'citekey':'B'}]}
  body=r'Current result \cite{A}.';result=repair_writer_payload(local,{'latex':body},{'issues':['Fix scope']})
  self.assertEqual(result['original_material'],body);self.assertEqual(result['canonical_studies'],[{'citekey':'A'}])
  self.assertIsNone(result['previous_candidate']);self.assertEqual(local['original_material'],'Long legacy survey')
 def test_section_feedback_maps_exact_paragraphs_to_unit_without_audit_bulk(self):
  from bounded_writing import unit_repair_feedback
  unit='First evidence.\n\nSecond evidence.';whole='\\section{Evidence}\n\\subsection{First}\n'+unit+'\n\n\\subsection{Other}\nOther evidence.'
  options=paragraph_options(whole);local=paragraph_options(unit)
  feedback={'issues':['Important objection'],'checks':{'facts':False},'source_checks_inherited':['x'*100000],
            'paragraph_review':[{'paragraph_id':p['id'],'decision':'revise','destination':'main','reason':'Fix.'} for p in options]}
  result=unit_repair_feedback(feedback,whole,unit,'u1')
  self.assertEqual([p['paragraph_id'] for p in result['paragraph_review']],[p['id'] for p in local])
  self.assertEqual(result['issues'],feedback['issues']);self.assertNotIn('source_checks_inherited',result)
 def test_repair_checkpoint_fits_windows_path_and_keeps_full_binding(self):
  from bounded_writing import repair_checkpoint
  from reviewforge import atomic_json
  import json
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d)/('a'*70)/('b'*70)
   while len(str(folder.resolve()))<214:folder=folder/'more'
   folder.mkdir(parents=True)
   binding='a'*64;path=repair_checkpoint(folder,binding)
   self.assertLess(len(str(path.resolve())),260)
   atomic_json(path,{'repair_binding':binding,'unit_ids':['u1']})
   self.assertEqual(json.loads(path.read_text())['repair_binding'],binding)
 def test_repair_selection_retains_all_objections_without_passed_audit_bulk(self):
  from bounded_writing import repair_selection_payload
  issue={'paragraph_id':'p2','decision':'revise','destination':'main','reason':'Missing qualification'}
  feedback={'issues':['All objections remain'],'checks':{'facts':False},'scientific_conflicts':[{'paragraph_ids':['p2'],'reason':'Conflict'}],
            'paragraph_review':[{'paragraph_id':'p1','decision':'keep','destination':'main'},issue],
            'paragraph_changes_required':[issue],'source_checks_inherited':[{'huge':'x'*100000}]}
  result=repair_selection_payload(feedback,[{'id':'u1'}],'Exact complete section')
  self.assertEqual(result['candidate'],'Exact complete section')
  self.assertEqual(result['review']['issues'],feedback['issues']);self.assertEqual(result['review']['scientific_conflicts'],feedback['scientific_conflicts'])
  self.assertEqual(result['review']['paragraph_review'],[issue]);self.assertNotIn('source_checks_inherited',result['review'])
  self.assertEqual(len(feedback['paragraph_review']),2)
 def test_context_epoch_change_does_not_reset_spent_write_budget(self):
  import json
  from pipeline_recovery import UnitRevisionsPending
  ask,review,calls=self.service()
  def rejected(ask,payload,candidate,save,pending=None):
   if payload['unit_id']=='u1':
    r={'accepted':False,'checks':{'facts':False},'issues':['Unresolved fact'],'paragraph_review':[]};save(r);return r,[]
   return review(ask,payload,candidate,save,pending)
  def scoped(system,payload,required,role):
   if required=='unit_ids':return {'unit_ids':['u1']}
   return ask(system,payload,required,role)
  with tempfile.TemporaryDirectory() as d:
   for _ in range(2):
    with self.assertRaises(UnitRevisionsPending):write_units(scoped,self.payload(),Path(d),'writer',rejected,{'facts'},{'f1':('A',{})})
   before=calls.count(('latex','u1'))
   payload={**self.payload(),'repair_feedback':{'issues':['Same fact remains wrong']},'previous_candidate':'previous chapter','_repair_generation':4}
   with self.assertRaises(UnitRevisionsPending):write_units(scoped,payload,Path(d),'writer',rejected,{'facts'},{'f1':('A',{})})
   self.assertEqual(calls.count(('latex','u1')),before)
 def payload(self):
  return {'title':'Evidence','word_budget':5500,'original_material':r'\section{Old} First evidence \cite{A}.'+'\n\n'+r'Another comparison \cite{A}.','known_citekeys':['A'],'canonical_studies':[{'citekey':'A','facts':{'count':{'id':'f1','value':230}}}],'previous_paragraph_messages':[]}
 def service(self,fail=None):
  calls=[]
  def ask(system,payload,required,role):
   calls.append((required,payload.get('unit_id')))
   if required=='units':
    return {'units':[{'id':'u1','heading':'Changed inputs','source_blocks':['b001'],'citekeys':['A']},{'id':'u2','heading':'Prediction information','source_blocks':['b002'],'citekeys':['A']}]}
   if required=='latex':
    if fail and payload['unit_id']==fail[0]:fail[0]=None;raise TimeoutError('interrupted')
    return {'latex':r'Reported cohort evidence \cite{A}.','evidence_synthesis':[{'finding':'230 batches','citekeys':['A'],'fact_ids':['f1']}],'retained_analytical_examples':[],'removed_redundancy':[]}
   raise AssertionError(required)
  def review(ask,payload,candidate,save,pending=None):
   result={'accepted':True,'checks':{'facts':True},'issues':[],**keep(paragraph_options(candidate['latex']))};save(result);return result,[]
  return ask,review,calls
 def test_interrupt_reuses_previously_completed_unit(self):
  ask,review,calls=self.service(['u2'])
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(TimeoutError):write_units(ask,self.payload(),Path(d),'writer',review,{'facts'}, {'f1':('A',{})})
   result=write_units(ask,self.payload(),Path(d),'writer',review,{'facts'}, {'f1':('A',{})})
   self.assertEqual(calls.count(('latex','u1')),1);self.assertEqual(calls.count(('units',None)),1)
   self.assertIn(r'\section{Evidence}',result['latex']);self.assertEqual(len(result['_argument_units']),2)
 def test_missing_source_coverage_is_rejected_before_writing(self):
  ask,review,calls=self.service()
  def bad(system,payload,required,role):
   result=ask(system,payload,required,role)
   if required=='units':result['units'][1]['source_blocks']=['b001']
   return result
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(ValueError,'coverage'):write_units(bad,self.payload(),Path(d),'writer',review,{'facts'},{'f1':('A',{})})
  self.assertFalse(any(k=='latex' for k,u in calls))
 def test_blank_line_inside_equation_is_not_split(self):
  text='First.\n\n'+r'\begin{equation}'+'\na=1\n\n+b\n'+r'\end{equation}'+'\n\nLast.'
  blocks=source_blocks(text)
  self.assertEqual(len(blocks),3);self.assertIn('a=1\n\n+b',blocks[1]['text'])
 def test_invented_fact_id_is_never_cached_as_accepted(self):
  ask,review,calls=self.service()
  def bad(system,payload,required,role):
   if required=='evidence_synthesis':return {'evidence_synthesis':[{'finding':'unsupported','citekeys':['A'],'fact_ids':['fake']}]}
   result=ask(system,payload,required,role)
   if required=='latex':result['evidence_synthesis'][0]['fact_ids']=['fake']
   return result
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(ValueError,'unit'):write_units(bad,self.payload(),Path(d),'writer',review,{'facts'},{'f1':('A',{})})

 def test_review_contract_change_invalidates_unit_acceptance(self):
  ask,review,calls=self.service()
  with tempfile.TemporaryDirectory() as d:
   write_units(ask,self.payload(),Path(d),'writer',review,{'facts'},{'f1':('A',{})},'review-v1')
   write_units(ask,self.payload(),Path(d),'writer',review,{'facts'},{'f1':('A',{})},'review-v2')
   self.assertEqual(calls.count(('units',None)),2)
 def test_same_review_feedback_on_next_generation_repairs_again(self):
  ask,review,calls=self.service()
  def scoped(system,payload,required,role):
   if required=='unit_ids':return {'unit_ids':['u1']}
   result=ask(system,payload,required,role)
   if required=='latex' and payload.get('repair_feedback'):
    result['latex']+=' New supported comparison.'*calls.count(('latex','u1'))
   return result
  with tempfile.TemporaryDirectory() as d:
   result=write_units(scoped,self.payload(),Path(d),'writer',review,{'facts'},{'f1':('A',{})})
   for generation in [1,2]:
    payload={**self.payload(),'repair_feedback':{'issues':['Comparison still incomplete']},'previous_candidate':result['latex'],'_repair_generation':generation}
    result=write_units(scoped,payload,Path(d),'writer',review,{'facts'},{'f1':('A',{})})
   self.assertEqual(calls.count(('latex','u1')),3)
   self.assertEqual(calls.count(('latex','u2')),1)
 def test_analytical_unit_does_not_require_unrelated_citations(self):
  from bounded_writing import validate_plan,candidate_errors
  blocks=source_blocks('Reasoning.\n\nAnalysis.')
  plan={'units':[{'id':'u1','heading':'Reasoning','kind':'analytical','source_blocks':['b001'],'citekeys':[]},{'id':'u2','heading':'Analysis','kind':'analytical','source_blocks':['b002'],'citekeys':[]}]}
  validate_plan(plan,blocks,[])
  candidate={'latex':'Net accumulation does not uniquely identify opposing fluxes.','evidence_synthesis':[],'retained_analytical_examples':['Formation and loss nonuniqueness']}
  self.assertEqual(candidate_errors(candidate,[],{},'analytical'),[])
  self.assertTrue(candidate_errors(candidate,[],{},'empirical'))
 def test_display_math_blank_lines_stay_intact(self):
  for left,right in [(r'\[',r'\]'),('$$','$$')]:
   blocks=source_blocks('First.\n\n'+left+'a=1\n\n+b'+right+'\n\nLast.')
   self.assertEqual(len(blocks),3)
 def test_pending_reviewer_failure_does_not_rerun_writer(self):
  ask,review,calls=self.service();failed=[False]
  def interrupted(*args):
   if not failed[0]:failed[0]=True;raise TimeoutError('review connection')
   return review(*args)
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(TimeoutError):write_units(ask,self.payload(),Path(d),'writer',interrupted,{'facts'},{'f1':('A',{})})
   write_units(ask,self.payload(),Path(d),'writer',interrupted,{'facts'},{'f1':('A',{})})
   self.assertEqual(calls.count(('latex','u1')),1)
 def test_route_only_splits_substantial_long_sections(self):
  from major_revision import needs_argument_units
  self.assertFalse(needs_argument_units({'word_budget':5500,'original_material':'short'}))
  self.assertTrue(needs_argument_units({'word_budget':5500,'original_material':'word '*1900}))

 def test_upstream_change_discards_downstream_saved_pending_review(self):
  import json
  from study_registry import signature
  ask,review,calls=self.service()
  with tempfile.TemporaryDirectory() as d:
   write_units(ask,self.payload(),Path(d),'writer',review,{'facts'},{'f1':('A',{})})
   folder=next((Path(d)/'argument_units').iterdir())
   upstream=json.loads((folder/'u1.json').read_text())
   upstream['candidate']['evidence_synthesis'][0]['finding']='Corrected comparison of 230 batches'
   upstream['candidate_sha256']=signature(upstream['candidate'])
   (folder/'u1.json').write_text(json.dumps(upstream))
   downstream=json.loads((folder/'u2.json').read_text())
   downstream.update(accepted=False,stage='pending_review')
   (folder/'u2.json').write_text(json.dumps(downstream))
   reviewed=[]
   def verify(ask,payload,candidate,save,pending=None):
    reviewed.append(payload['unit_id']);self.assertIsNone(pending)
    return review(ask,payload,candidate,save,pending)
   write_units(ask,self.payload(),Path(d),'writer',verify,{'facts'},{'f1':('A',{})})
   self.assertEqual(reviewed,['u2']);self.assertEqual(calls.count(('latex','u2')),1)

 def test_evidence_metadata_repair_preserves_body_and_runs_full_review(self):
  ask,review,calls=self.service();reviewed=[]
  def metadata(system,payload,required,role):
   if required=='evidence_synthesis':return {'evidence_synthesis':[{'finding':'230 batches','citekeys':['A'],'fact_ids':['f1']}]}
   result=ask(system,payload,required,role)
   if required=='latex':result['evidence_synthesis'][0]['fact_ids']=[]
   return result
  def verify(ask,payload,candidate,save,pending=None):
   reviewed.append(candidate['latex']);return review(ask,payload,candidate,save,pending)
  with tempfile.TemporaryDirectory() as d:
   result=write_units(metadata,self.payload(),Path(d),'writer',verify,{'facts'},{'f1':('A',{})})
   self.assertEqual(calls.count(('latex','u1')),1)
   self.assertEqual(len(reviewed),2)
   self.assertTrue(all(text==r'Reported cohort evidence \cite{A}.' for text in reviewed))

 def test_metadata_repair_is_bounded_once_per_unit_invocation(self):
  ask,review,calls=self.service();patches=[]
  def invalid(system,payload,required,role):
   if required=='evidence_synthesis':
    patches.append(1);return {'evidence_synthesis':[{'finding':'unsupported','citekeys':['A'],'fact_ids':[]}]}
   result=ask(system,payload,required,role)
   if required=='latex':result['evidence_synthesis'][0]['fact_ids']=[]
   return result
  with tempfile.TemporaryDirectory() as d:
   for invocation in range(2):
    before=len(patches)
    with self.assertRaises(ValueError):write_units(invalid,self.payload(),Path(d),'writer',review,{'facts'},{'f1':('A',{})})
    self.assertEqual(len(patches)-before,2)  # one repair for each of the two deferred units

 def test_failed_unit_defers_without_blocking_other_unit(self):
  from pipeline_recovery import UnitRevisionsPending
  import json
  ask,review,calls=self.service()
  def reject_first(ask,payload,candidate,save,pending=None):
   if payload['unit_id']=='u1':
    report={'accepted':False,'checks':{'facts':False},'issues':['Needs evidence'],'paragraph_review':[]};save(report);return report,[]
   return review(ask,payload,candidate,save,pending)
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(UnitRevisionsPending):write_units(ask,self.payload(),Path(d),'writer',reject_first,{'facts'},{'f1':('A',{})})
   folder=next((Path(d)/'argument_units').iterdir())
   self.assertTrue(json.loads((folder/'u2.json').read_text())['accepted'])
   self.assertFalse(json.loads((folder/'u1.json').read_text())['accepted'])
   from study_registry import signature
   from reviewforge import atomic_json
   path=folder/'u1.json';row=json.loads(path.read_text())
   row['candidate']['latex']+=' Corrected qualification.'
   row.update(candidate_sha256=signature(row['candidate']),stage='pending_review',review=None)
   atomic_json(path,row)
   write_units(ask,self.payload(),Path(d),'writer',review,{'facts'},{'f1':('A',{})})
   self.assertEqual(calls.count(('latex','u2')),1)

 def test_small_review_fix_uses_patch_not_whole_unit_writer(self):
  ask,review,calls=self.service();patches=[];reviewed=[]
  def patching(system,payload,required,role):
   if required=='replacements':
    patches.append(1);row=payload['paragraphs'][0]
    return {'replacements':[{'paragraph_id':row['paragraph_id'],'latex':row['original'].replace(' Repeated text.','')}]}
   result=ask(system,payload,required,role)
   if required=='latex':result['latex']+= ' Repeated text.'
   return result
  def checking(ask,payload,candidate,save,pending=None):
   reviewed.append(payload['unit_id'])
   result={'accepted':True,'checks':{'facts':True},'issues':[],**keep(paragraph_options(candidate['latex']))}
   if payload['unit_id']=='u1' and 'Repeated text.' in candidate['latex']:
    result['accepted']=False;result['paragraph_review'][0].update(decision='revise',reason='Remove Repeated text.')
    changes=[result['paragraph_review'][0]]
   else:changes=[]
   save(result);return result,changes
  with tempfile.TemporaryDirectory() as d:
   write_units(patching,self.payload(),Path(d),'writer',checking,{'facts'},{'f1':('A',{})})
   self.assertEqual(calls.count(('latex','u1')),1);self.assertEqual(len(patches),1);self.assertEqual(reviewed.count('u1'),2)

 def test_patch_api_failure_does_not_trigger_full_unit_rewrite(self):
  import json
  for failure in [ValueError('Editorial response truncated'),json.JSONDecodeError('bad JSON','x',0)]:
   ask,review,calls=self.service()
   def broken(system,payload,required,role):
    if required=='replacements':raise failure
    return ask(system,payload,required,role)
   def needs_edit(ask,payload,candidate,save,pending=None):
    result={'accepted':False,'checks':{'facts':True},'issues':['Trim'],**keep(paragraph_options(candidate['latex']))}
    result['paragraph_review'][0].update(decision='revise',reason='Trim');save(result)
    return result,[result['paragraph_review'][0]]
   with tempfile.TemporaryDirectory() as d:
    with self.assertRaises(type(failure)):write_units(broken,self.payload(),Path(d),'writer',needs_edit,{'facts'},{'f1':('A',{})})
    self.assertEqual(calls.count(('latex','u1')),1)
 def test_full_write_budget_survives_process_recovery(self):
  from pipeline_recovery import UnitRevisionsPending
  ask,review,calls=self.service()
  def reject_first(ask,payload,candidate,save,pending=None):
   if payload['unit_id']=='u1':
    report={'accepted':False,'checks':{'facts':False},'issues':['Needs evidence'],'paragraph_review':[]};save(report);return report,[]
   return review(ask,payload,candidate,save,pending)
  with tempfile.TemporaryDirectory() as d:
   for invocation in range(3):
    with self.assertRaises(UnitRevisionsPending):write_units(ask,self.payload(),Path(d),'writer',reject_first,{'facts'},{'f1':('A',{})})
   self.assertEqual(calls.count(('latex','u1')),2) # identical rejected output stops before the old four-write cap
   self.assertEqual(calls.count(('latex','u2')),1)

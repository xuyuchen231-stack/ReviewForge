import tempfile, unittest
from pathlib import Path
from bounded_writing import write_units, source_blocks
from paragraph_review import paragraph_options
from test_paragraph_review import keep

class UnitWritingTests(unittest.TestCase):
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
   return ask(system,payload,required,role)
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

import json,tempfile,unittest
from pathlib import Path
from study_registry import signature
from reviewforge import atomic_json
from assembly_review import verified_units,cross_unit_review,review_assembly

class AssemblyReviewTests(unittest.TestCase):
 def test_global_findings_sent_once_without_mutating_approval_manifest(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);candidate,_=self.fixture(root)
   manifest=verified_units(candidate,root,'Evidence',['facts_consistent'])
   manifest[0]['findings']=['Exact qualified conclusion '*100]
   def ask(system,packet,*args):
    self.assertEqual(packet['units'][0]['findings'],manifest[0]['findings'])
    self.assertNotIn('findings',packet['source_approval_manifest'][0])
    self.assertEqual(packet['source_approval_manifest'][0]['review_sha256'],manifest[0]['review_sha256'])
    return {'examined_unit_ids':['u1','u2'],'status':'pass','reason':'Checked.','conflicts':[],'paragraph_requests':[]}
   cross_unit_review(ask,candidate,root,manifest,90000)
   self.assertTrue(manifest[0]['findings'])
 def test_oversized_source_followup_selects_fields_but_never_forces_acceptance(self):
  for verdict in (True,False):
   with self.subTest(verdict=verdict),tempfile.TemporaryDirectory() as t:
    root=Path(t);candidate,_=self.fixture(root);lookups=[]
    fact={'id':'f1','value':0.45,'qualification':'single calibration'}
    study={'citekey':'A','facts':{'n':fact,'unrelated':{'id':'f2','value':'x'*100000}}}
    def ask(system,packet,required,role):
     if required=='examined_unit_ids':return {'examined_unit_ids':['u1','u2'],'status':'pass','reason':'No conflict.','conflicts':[],'paragraph_requests':[]}
     if required=='fields_by_study':
      lookups.append(packet);return {'fields_by_study':[{'citekey':'A','paragraph_ids':[packet['concerns'][0]['paragraph_id']],'fields':['n']}]}
     provided=bool(packet.get('canonical_studies'))
     rows=[{'paragraph_id':p['id'],'function':'evidence','message':'Result.','adds':'Evidence.','decision':'keep','destination':'main','reason':'Checked.'} for p in packet['paragraph_options']]
     if provided:self.assertEqual(packet['canonical_studies'][0]['facts'],{'n':fact})
     accepted=provided and verdict
     if not accepted:rows[0].update(decision='revise',reason='Unresolved result.',severity='major',category='evidence_scope')
     return {'accepted':accepted,'issues':[] if accepted else ['Unresolved result.'],'checks':{'nonredundant_argument':accepted},'scientific_conflicts':[],'paragraph_review':rows}
    report,_=review_assembly(ask,{'title':'Evidence','canonical_studies':[study]},candidate,root,{'facts_consistent','nonredundant_argument'},lambda r:None)
    self.assertEqual(report['accepted'],verdict);self.assertEqual(len(lookups),1)
 def test_source_followup_keeps_local_findings_and_hashes_other_unit_context(self):
  from assembly_review import source_followup_context
  packet={'canonical_studies':[{'citekey':'A','facts':{'n':{'value':0.45}}}],
          'section_findings':[{'unit':'u1','findings':['Current claim']},{'unit':'u2','findings':['Large context '*5000]}]}
  result=source_followup_context(packet,{'u1'},{'status':'pass','reason':'All units checked.','examined_unit_ids':['u1','u2']})
  self.assertEqual(result['canonical_studies'],packet['canonical_studies'])
  self.assertEqual(result['section_findings'],[packet['section_findings'][0]])
  self.assertEqual(result['other_unit_finding_refs'][0]['unit'],'u2')
  self.assertEqual(len(packet['section_findings']),2)
 def fixture(self,path):
  units=[{'id':'u1','heading':'Evidence'},{'id':'u2','heading':'Implication'}];binding='a'*64;folder=path/'argument_units'/binding;folder.mkdir(parents=True)
  plan={'units':units};atomic_json(folder/'plan.json',{'plan':plan,'sha256':signature(plan)})
  bodies=[r'Reported data \cite{A}.','Supported interpretation.']
  for u,body in zip(units,bodies):
   c={'latex':body,'evidence_synthesis':[]};atomic_json(folder/(u['id']+'.json'),{'candidate':c,'candidate_sha256':signature(c),'accepted':True,'review':{'checks':{'facts_consistent':True,'nonredundant_argument':True}}})
  c={'latex':'\\section{Evidence}\n'+'\n\n'.join('\\subsection{'+u['heading']+'}\n'+b for u,b in zip(units,bodies)),'_argument_units':units,'_argument_units_binding':binding}
  return c,folder
 def test_assembly_evidence_objection_receives_exact_facts_before_rewrite(self):
  from paragraph_review import paragraph_options
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);candidate,_=self.fixture(root);calls=[];saved=[]
   study={'citekey':'A','facts':{'n':{'id':'f1','value':0.45,'qualification':'calibration only'}}}
   def ask(system,packet,required,role):
    if required=='examined_unit_ids':return {'examined_unit_ids':['u1','u2'],'status':'pass','reason':'No cross-unit conflict.','conflicts':[],'paragraph_requests':[]}
    calls.append(packet);provided=bool(packet.get('canonical_studies'))
    rows=[{'paragraph_id':p['id'],'function':'evidence','message':'Reported result.','adds':'Evidence.','decision':'keep','destination':'main','reason':'Verified.'} for p in packet['paragraph_options']]
    if not provided:rows[0].update(decision='revise',reason='The calibration number is not supplied.',severity='major',category='evidence_scope')
    else:self.assertEqual(packet['canonical_studies'],[study])
    return {'accepted':provided,'issues':[] if provided else ['Number not supplied.'],'checks':{'nonredundant_argument':provided},'scientific_conflicts':[],'paragraph_review':rows}
   result,changes=review_assembly(ask,{'title':'Evidence','canonical_studies':[study]},candidate,root,{'facts_consistent','nonredundant_argument'},saved.append)
   self.assertTrue(result['accepted']);self.assertEqual(changes,[]);self.assertEqual(len(calls),2)
 def test_unresolved_assembly_quote_requests_cannot_pass(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);candidate,_=self.fixture(root);calls=[]
   study={'citekey':'A','facts':{'n':{'id':'f1','value':0.45,'anchors':[{'excerpt':'m = 0.45'}]}}}
   def ask(system,packet,required,role):
    if required=='examined_unit_ids':return {'examined_unit_ids':['u1','u2'],'status':'pass','reason':'No conflict.','conflicts':[],'paragraph_requests':[]}
    calls.append(packet)
    return {'accepted':True,'issues':[],'checks':{'nonredundant_argument':True},'scientific_conflicts':[],
            'evidence_requests':['f1'],'paragraph_review':[{'paragraph_id':p['id'],'function':'evidence','message':'Claim.','adds':'Evidence.','decision':'keep','destination':'main','reason':'Still needs quote.'} for p in packet['paragraph_options']]}
   with self.assertRaisesRegex(ValueError,'unresolved'):review_assembly(ask,{'title':'Evidence','canonical_studies':[study]},candidate,root,{'facts_consistent','nonredundant_argument'},lambda r:None)
   self.assertEqual(len(calls),2);self.assertEqual(calls[1]['requested_primary_evidence'][0]['fact']['anchors'][0]['excerpt'],'m = 0.45')
 def test_exact_accepted_units_can_be_reused(self):
  with tempfile.TemporaryDirectory() as t:
   c,_=self.fixture(Path(t));self.assertEqual(len(verified_units(c,Path(t),'Evidence',['facts_consistent'])),2)
 def test_changed_assembly_or_unaccepted_child_cannot_inherit(self):
  with tempfile.TemporaryDirectory() as t:
   c,folder=self.fixture(Path(t))
   with self.assertRaises(ValueError):verified_units({**c,'latex':c['latex']+' Invented claim.'},Path(t),'Evidence',['facts_consistent'])
   row=json.loads((folder/'u1.json').read_text());row['accepted']=False;atomic_json(folder/'u1.json',row)
   with self.assertRaises(ValueError):verified_units(c,Path(t),'Evidence',['facts_consistent'])
 def test_distant_conflict_is_retained_after_exact_paragraph_retrieval(self):
  from paragraph_review import paragraph_records
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);c,folder=self.fixture(root);manifest=verified_units(c,root,'Evidence',['facts_consistent']);calls=[]
   pid=paragraph_records('Supported interpretation.')[0]['id']
   def ask(system,payload,*args):
    calls.append(payload)
    return {'examined_unit_ids':['u1','u2'],'status':'uncertain' if len(calls)==1 else 'fail','reason':'Conflicting conclusions.','conflicts':[] if len(calls)==1 else [{'unit_ids':['u1','u2'],'reason':'Opposite conclusions.'}],'paragraph_requests':[{'unit_id':'u2','paragraph_ids':[pid]}] if len(calls)==1 else []}
   report=cross_unit_review(ask,c,root,manifest,90000)
   self.assertEqual(report['status'],'fail');self.assertEqual(calls[1]['requested_exact_paragraphs'][0]['text'],'Supported interpretation.')
 def test_incomplete_global_coverage_never_passes(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);c,_=self.fixture(root);manifest=verified_units(c,root,'Evidence',['facts_consistent'])
   def ask(*args):return {'examined_unit_ids':['u1'],'status':'pass','reason':'Only one examined.','conflicts':[]}
   with self.assertRaises(ValueError):cross_unit_review(ask,c,root,manifest,90000)

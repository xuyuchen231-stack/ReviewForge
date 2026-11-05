import json,tempfile,unittest
from pathlib import Path
from study_registry import signature
from reviewforge import atomic_json
from assembly_review import verified_units,cross_unit_review

class AssemblyReviewTests(unittest.TestCase):
 def fixture(self,path):
  units=[{'id':'u1','heading':'Evidence'},{'id':'u2','heading':'Implication'}];binding='a'*64;folder=path/'argument_units'/binding;folder.mkdir(parents=True)
  plan={'units':units};atomic_json(folder/'plan.json',{'plan':plan,'sha256':signature(plan)})
  bodies=['Reported data.','Supported interpretation.']
  for u,body in zip(units,bodies):
   c={'latex':body,'evidence_synthesis':[]};atomic_json(folder/(u['id']+'.json'),{'candidate':c,'candidate_sha256':signature(c),'accepted':True,'review':{'checks':{'facts_consistent':True}}})
  c={'latex':'\\section{Evidence}\n'+'\n\n'.join('\\subsection{'+u['heading']+'}\n'+b for u,b in zip(units,bodies)),'_argument_units':units,'_argument_units_binding':binding}
  return c,folder
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

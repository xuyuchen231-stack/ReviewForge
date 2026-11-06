import copy,unittest
from source_field_lookup import select_source_fields

class SourceFieldLookupTests(unittest.TestCase):
 def fixture(self):
  studies=[{'citekey':'A','source_access':[{'document_access':'full_text'}],'facts':{'result':{'id':'f1','value':0.45,'qualification':'single calibration'},'unrelated':{'id':'f2','value':'x'*10000}}}]
  paragraphs=[{'id':'p1','text':r'Result \cite{A}.','citekeys':['A']}]
  return studies,paragraphs,[{'paragraph_id':'p1','reason':'Verify calibration value.'}]
 def test_selects_exact_requested_fields_without_mutating_full_evidence(self):
  studies,paragraphs,concerns=self.fixture();before=copy.deepcopy(studies)
  def ask(system,payload,required,role):
   self.assertEqual(required,'fields_by_study');self.assertNotIn('facts',payload['source_catalog'][0])
   return {'fields_by_study':[{'citekey':'A','paragraph_ids':['p1'],'fields':['result']}]}
  selected=select_source_fields(ask,studies,concerns,paragraphs)
  self.assertEqual(selected[0]['facts'],{'result':before[0]['facts']['result']})
  self.assertEqual(selected[0]['source_access'],before[0]['source_access'])
  self.assertIn('unrelated',selected[0]['unselected_known_fields']);self.assertEqual(studies,before)
 def test_unknown_fields_or_incomplete_concern_coverage_are_rejected(self):
  studies,paragraphs,concerns=self.fixture()
  for response in ({'fields_by_study':[{'citekey':'A','paragraph_ids':['p1'],'fields':['invented']}]},{'fields_by_study':[]}):
   with self.assertRaises(ValueError):select_source_fields(lambda *a:response,studies,concerns,paragraphs)
 def test_cannot_attach_a_different_study_to_a_paragraph(self):
  studies,paragraphs,concerns=self.fixture();studies.append({'citekey':'B','facts':{'result':{'id':'other','value':1}}})
  with self.assertRaises(ValueError):select_source_fields(lambda *a:{'fields_by_study':[{'citekey':'B','paragraph_ids':['p1'],'fields':['result']}]},studies,concerns,paragraphs)

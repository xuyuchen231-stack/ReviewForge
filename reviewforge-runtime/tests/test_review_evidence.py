import unittest
from review_evidence import ask_with_evidence,add_requested_evidence

class EvidenceRetrievalTests(unittest.TestCase):
 def fixture(self):return {'canonical_studies':[{'citekey':'A','facts':{'count':{'id':'f1','value':230,'anchors':[{'excerpt':'230 industrial batches','locator':'Table 2'}]}}}]}
 def test_requested_original_quote_is_supplied_without_mutation(self):
  payload=self.fixture();calls=[]
  def ask(system,packet,*args):
   calls.append(packet);return {'evidence_requests':['f1']} if len(calls)==1 else {'evidence_requests':[],'passages':[]}
  ask_with_evidence(ask,'review',payload,'passages')
  self.assertEqual(calls[1]['requested_primary_evidence'][0]['fact']['anchors'][0]['excerpt'],'230 industrial batches')
  self.assertNotIn('requested_primary_evidence',payload)
 def test_unresolved_or_unknown_requests_block(self):
  payload=self.fixture()
  with self.assertRaises(ValueError):ask_with_evidence(lambda *args:{'evidence_requests':['f1']},'review',payload,'passages')
  with self.assertRaises(ValueError):add_requested_evidence(payload,['f1','unknown'],payload['canonical_studies'])

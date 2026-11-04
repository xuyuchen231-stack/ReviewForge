import unittest
from evidence_transport import compact_evidence,expand_evidence

class EvidenceTransportTests(unittest.TestCase):
 def test_shared_anchors_roundtrip_without_changing_facts_or_qualifications(self):
  anchor={'span_id':'s1','excerpt':'exact evidence '*100,'locator':'p2','source_sha256':'x'}
  original={'canonical_studies':[{'citekey':'a','facts':{'x':{'id':'f1','anchors':[anchor],'qualification':'conditional'},'y':{'id':'f2','anchors':[anchor]}}}], 'previous_candidate':'unchanged'}
  wire=compact_evidence(original)
  self.assertEqual(expand_evidence(wire),original)
  self.assertEqual(original['canonical_studies'][0]['facts']['x']['anchors'],[anchor])
  self.assertNotIn('anchors',wire['canonical_studies'][0]['facts']['x'])
 def test_no_evidence_is_unchanged(self):
  self.assertEqual(compact_evidence({'text':'hi'}),{'text':'hi'})

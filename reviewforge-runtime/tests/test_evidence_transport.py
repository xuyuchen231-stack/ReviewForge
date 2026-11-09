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

 def test_v4_wire_preserves_each_exact_excerpt_and_qualification(self):
  import json
  from types import SimpleNamespace
  from reviewforge_v4 import client_chat

  excerpt='Exact methanol result with units and a condition. '*100
  entry={'excerpt':excerpt,'locator':'p. 4','limitations':'single batch'}
  payload={'body':'Retain complete prose','evidence_context':{
      'entries':[entry], 'canonical_facts':[{**entry,'citekey':'k'}]}}
  api=SimpleNamespace(chat=lambda system,user,role: user)
  encoded=client_chat(api,'Write',payload)
  wire=json.loads(encoded)
  context=wire['evidence_context']
  self.assertEqual(encoded.count(excerpt),1)
  for field in ('entries','canonical_facts'):
   row=context[field][0]
   self.assertEqual(context['shared_excerpts'][row['excerpt_ref']],excerpt)
   self.assertEqual(row['locator'],'p. 4')
   self.assertEqual(row['limitations'],'single batch')
  self.assertEqual(payload['evidence_context']['entries'][0],entry)
  self.assertLess(len(encoded),len(json.dumps(payload,ensure_ascii=False,separators=(',',':'))))

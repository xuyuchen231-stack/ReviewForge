import copy,json,unittest
from efficient_payload import project_payload,encoded_size,partition_writing,InputBudgetExceeded

class EfficientPayloadTests(unittest.TestCase):
 def test_primary_verification_still_receives_exact_quotes(self):
  anchor={'span_id':'s1','excerpt':'Exact primary text with a necessary qualification.','locator':'p2','source_sha256':'sha'}
  p={'facts':[{'id':'f1','anchors':[anchor]},{'id':'f2','anchors':[anchor]}]};wire=project_payload(p)
  self.assertEqual(len(wire['primary_quote_pool']),1)
  for fact in wire['facts']:self.assertEqual(wire['primary_quote_pool'][fact['anchor_refs'][0]],anchor)
 def study(self,key='A'):
  return {'citekey':key,'source_access':[{'document_access':'full_text','inspection_coverage':'complete_document'}],'facts':{'result':{'id':'f'+key,'value':{'n':230,'split':'20% untouched holdout'},'context':'industrial','semantic_status':'qualified','qualification':'same recipe only','anchors':[{'span_id':'s1','source_sha256':'sha','excerpt':'source text '*20000,'locator':'p2'}]}}}
 def test_exact_verified_values_and_qualifications_survive_without_repeating_quotes(self):
  p={'canonical_studies':[self.study()],'candidate':{'latex':'Evidence.'}};before=copy.deepcopy(p);wire=project_payload(p)
  c=wire['canonical_studies'][0]['facts']['result']
  self.assertEqual(c['value'],p['canonical_studies'][0]['facts']['result']['value']);self.assertEqual(c['qualification'],'same recipe only')
  self.assertEqual(wire['canonical_studies'][0]['source_access'],p['canonical_studies'][0]['source_access'])
  self.assertNotIn('anchors',c);self.assertEqual(wire['canonical_studies'][0]['primary_sources'][c['source_refs'][0]],'sha')
  self.assertEqual(p,before);self.assertLess(encoded_size(wire),encoded_size(p)/50)
 def test_singular_global_study_is_projected_too(self):
  s=self.study();self.assertNotIn('anchors',project_payload({'canonical_study':s})['canonical_study']['facts']['result'])
 def test_writer_partition_preserves_every_intact_source_block(self):
  paragraphs=[('Evidence '+str(i)+' '+('word '*500)+r'\cite{'+key+'}.') for i,key in enumerate(['A','B','C','D'])]
  p={'original_material':'\n\n'.join(paragraphs),'canonical_studies':[self.study(k) for k in 'ABCD'],'known_citekeys':list('ABCD'),'word_budget':2000}
  parts=partition_writing('system',p,9000)
  self.assertGreater(len(parts),1);self.assertEqual('\n\n'.join(x['original_material'] for x in parts),p['original_material'])
  self.assertTrue(all(encoded_size(project_payload(x))+len('system')<=9000 for x in parts))
 def test_single_indivisible_oversize_block_fails_without_truncation(self):
  with self.assertRaises(InputBudgetExceeded):partition_writing('s',{'original_material':'x'*50000,'canonical_studies':[]},1000)

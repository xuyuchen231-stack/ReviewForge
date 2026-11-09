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

 def test_review_versions_share_only_exact_unchanged_paragraphs(self):
  import json
  from evidence_transport import encode_context_payload

  paragraph='An unchanged scientific paragraph with source and qualification. '*20
  before=paragraph+'\n \nOriginal claim.\n\n'+paragraph
  after='Corrected claim.\n\n'+paragraph
  payload={'before':before,'body':after}
  encoded=encode_context_payload(payload,revised_field='body')
  wire=json.loads(encoded)
  for key in ('before','body'):
   restored=''.join(wire['shared_paragraphs'][str(part)] if isinstance(part,int) else part
                    for part in wire[key])
   self.assertEqual(restored,payload[key])
  self.assertEqual(encoded.count(paragraph),1)
  self.assertLess(len(encoded),len(json.dumps(payload)))

 def test_repeated_fact_metadata_is_shared_without_losing_anchor_order(self):
  import copy,json
  from evidence_transport import encode_context_payload
  claim='A qualified result retaining its complete conditions and units. '*40
  rows=[{'citekey':'study','claim':claim,'source_id':'doi:example',
         'locator':'page '+str(i),'excerpt':'Exact primary text '+str(i),
         'limitations':'one process only','qualification':{'status':'qualified','reason':'conditional'}}
        for i in range(40)]
  payload={'body':'Intact manuscript','evidence_context':{
      'entries':rows,'canonical_facts':[{**row,'canonical_fact_id':'fact1'} for row in rows]}}
  original=copy.deepcopy(payload)
  encoded=encode_context_payload(payload)
  context=json.loads(encoded)['evidence_context']
  self.assertTrue('evidence_row_tables' in context,'Repeated metadata was not factored')
  table=context['evidence_row_tables']
  for field in ('entries','canonical_facts'):
   restored=[{**table['metadata'][m],**table['anchors'][a]} for m,a in context[field]]
   if 'shared_excerpts' in context:
    for row in restored:
     if 'excerpt_ref' in row:row['excerpt']=context['shared_excerpts'][row.pop('excerpt_ref')]
   self.assertEqual(restored,payload['evidence_context'][field])
  self.assertEqual(payload,original)
  self.assertLess(len(encoded),len(json.dumps(payload,ensure_ascii=False))*.25)

 def test_distinct_sources_and_conflicting_qualifications_survive_grouping(self):
  import json
  from evidence_transport import encode_context_payload
  rows=[]
  for source,limit in [('doi:a','lab only'),('doi:b','industrial only')]:
   rows.extend({'citekey':'k','claim':'Shared wording '*70,'source_id':source,
                'limitations':limit,'locator':str(i),'excerpt':'Exact quote '+str(i)} for i in range(30))
  payload={'evidence_context':{'entries':rows}}
  ctx=json.loads(encode_context_payload(payload))['evidence_context']
  self.assertTrue('evidence_row_tables' in ctx,'Repeated metadata was not factored')
  table=ctx['evidence_row_tables'];restored=[{**table['metadata'][m],**table['anchors'][a]} for m,a in ctx['entries']]
  if 'shared_excerpts' in ctx:
   for row in restored:
    if 'excerpt_ref' in row:row['excerpt']=ctx['shared_excerpts'][row.pop('excerpt_ref')]
  self.assertEqual(restored,rows)

 def test_already_encoded_rows_with_unique_excerpts_are_unchanged(self):
  import json
  from evidence_transport import encode_context_payload
  payload={'evidence_context':{'entries':[
      {'claim':'Repeated complete claim '*80,'source_id':'doi:a',
       'excerpt':'unique '+str(i),'locator':str(i)} for i in range(30)]}}
  encoded=encode_context_payload(payload)
  wire=json.loads(encoded)
  self.assertTrue('evidence_row_tables' in wire['evidence_context'])
  self.assertNotIn('shared_excerpts',wire['evidence_context'])
  self.assertEqual(encode_context_payload(wire),encoded)

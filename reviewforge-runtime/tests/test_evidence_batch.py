import json,tempfile,unittest
from pathlib import Path

class EvidenceBatchTests(unittest.TestCase):
 def test_interrupted_second_batch_resumes_saved_first_card(self):
  from evidence_batch import extract_sources
  packets=[{'citekey':key,'chunks':[{'text':key,'locator':'p1'}]} for key in ('A','B')];calls=[]
  def index(p):return {'citekey':p['citekey'],'evidence_spans':[{'id':'s000','text':p['citekey'],'locator':'p1'}]}
  def ask(sources):
   calls.append(sources[0]['citekey'])
   if len(calls)==2:raise TimeoutError('simulated interruption')
   return {'studies':[{'citekey':source['citekey'],'fields':{}} for source in sources]}
  with tempfile.TemporaryDirectory() as t:
   args=dict(run=Path(t),unit_id='u',question='Q',axes=[],packets=packets,ask=ask,index_source=index,normalize=lambda r,a:r,materialize=lambda r,p:r,validate=lambda *args:True,batch_size=1)
   with self.assertRaises(TimeoutError):extract_sources(**args)
   self.assertEqual(set(extract_sources(**args)),{'A','B'});self.assertEqual(calls,['A','B','B'])
 def test_packet_limit_never_silently_truncates_source(self):
  from evidence_batch import bounded_batches
  with self.assertRaisesRegex(ValueError,'exceeds batch budget'):bounded_batches([{'citekey':'A','evidence_spans':[{'text':'x'*2000}]}],max_bytes=1000)
 def test_batches_save_good_rows_and_retry_only_missing_then_reuse_across_units(self):
  from evidence_batch import extract_sources
  packets=[{'citekey':k,'chunks':[{'text':'Evidence for '+k,'locator':'p1'}]} for k in ('A','B','C')];calls=[]
  def index(p):return {'citekey':p['citekey'],'evidence_spans':[{'id':'s000','text':p['chunks'][0]['text'],'locator':'p1'}]}
  def ask(sources):
   calls.append([p['citekey'] for p in sources]);chosen=sources[:2] if len(calls)==1 else sources
   return {'studies':[{'citekey':p['citekey'],'fields':{'axis':{'status':'supported','evidence_ids':[p['evidence_spans'][0]['id']]}}} for p in chosen]}
  def materialize(row,p):
   byid={s['id']:s for s in p['evidence_spans']};return {'citekey':row['citekey'],'fields':{'axis':{'excerpt':byid[row['fields']['axis']['evidence_ids'][0]]['text']}}}
  def valid(row,axes,p):
   if row['fields']['axis']['excerpt']!=p['chunks'][0]['text']:raise ValueError('wrong source')
   return True
  with tempfile.TemporaryDirectory() as t:
   args=dict(run=Path(t),question='Q',axes=['axis'],packets=packets,ask=ask,index_source=index,normalize=lambda r,a:r,materialize=materialize,validate=valid)
   result=extract_sources(unit_id='unit_001',**args);self.assertEqual(set(result),{'A','B','C'});self.assertEqual(calls,[['A','B','C'],['C']])
   extract_sources(unit_id='unit_002',**args);self.assertEqual(len(calls),2)
   extract_sources(unit_id='unit_003',**{**args,'question':'Different Q'});self.assertGreater(len(calls),2)
   changed=json.loads(json.dumps(packets));changed[1]['chunks'][0]['text']='Changed B evidence'
   extract_sources(unit_id='unit_004',**{**args,'packets':changed});self.assertEqual(calls[-1],['B'])
 def test_batch_span_ids_are_scoped_per_paper(self):
  from evidence_batch import bounded_batches,namespaced_source
  sources=[namespaced_source({'citekey':key,'evidence_spans':[{'id':'s000','text':'same'}]}) for key in ('A','B')]
  self.assertNotEqual(sources[0]['evidence_spans'][0]['id'],sources[1]['evidence_spans'][0]['id'])
  from autonomous_review import materialize_evidence
  with self.assertRaisesRegex(ValueError,'Invalid source evidence IDs'):
   materialize_evidence({'fields':{'axis':{'status':'supported','evidence_ids':[sources[0]['evidence_spans'][0]['id']]}}},sources[1])
  batches=bounded_batches(sources,max_sources=1,max_bytes=1000);self.assertEqual(len(batches),2)

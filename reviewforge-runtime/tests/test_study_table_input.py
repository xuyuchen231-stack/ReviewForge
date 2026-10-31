import copy,json,unittest

class StudyTableInputTests(unittest.TestCase):
 def payload(self):
  axes=["A long scientific comparison dimension requiring exact interpretation "+str(i) for i in range(8)]
  return {"body":r"\cite{A,B} preserve this text", "study_comparisons":[{"citekey":key,"source_type":"abstract_only","fields":{axis:{"status":"supported" if i%2 else "not_accessible","value":"Evidence bound conclusion "+str(i),"locator":"p. 2, source span "+str(i),"excerpt":"Verbatim source excerpt for dimension "+str(i),"explicit_in_abstract":bool(i%2)} for i,axis in enumerate(axes)}} for key in ["A","B","C","D"]],"evidence_context":{"semantic_verification":False,"unanchored_citekeys":[]}}
 def test_round_trip_preserves_all_values_and_does_not_mutate_input(self):
  from model_input import compact_study_tables,expand_study_tables
  p=self.payload();before=copy.deepcopy(p);packed=compact_study_tables(p)
  self.assertIn("_study_table_encoding",packed)
  self.assertEqual(expand_study_tables(packed),p);self.assertEqual(p,before)
  self.assertLess(len(json.dumps(packed)),len(json.dumps(p))*.9)
  self.assertEqual(compact_study_tables(packed),packed)
 def test_different_missing_and_null_fields_keep_distinct_schemas(self):
  from model_input import compact_study_tables,expand_study_tables
  p=self.payload();fields=p['study_comparisons'][0]['fields'];f=list(fields.values());f[0]['value']=None;f[1].pop('excerpt');f[2]['excerpt_ref']='q001';f[2].pop('excerpt');p['source_quotes']={'q001':{'excerpt':'exact quote'}}
  self.assertEqual(expand_study_tables(compact_study_tables(p)),p)
 def test_small_or_colliding_payload_is_unchanged(self):
  from model_input import compact_study_tables
  for p in [{'body':'short'}, {'study_comparisons':[{'fields':{'a':{'value':'x'}}}]}, {**self.payload(),'_study_table_encoding':{'existing':'do not overwrite'}}]:self.assertEqual(compact_study_tables(p),p)

 def test_checkpoint_sends_reversible_table_and_records_actual_wire_bytes(self):
  import tempfile,time
  from pathlib import Path
  from autonomous_review import checkpoint_call,compact_evidence_payload
  from model_input import expand_study_tables
  from reviewforge import encode_model_payload
  p=self.payload();seen=[]
  class API:
   max_tokens=1000
   def chat(self,system,user,role):seen.append(user);return 'saved response'
  with tempfile.TemporaryDirectory() as t:
   state={'deadline':time.time()+1200,'phase':'writing'}
   checkpoint_call(API(),state,Path(t)/'state.json','rules',p,'writer')
   sent=json.loads(seen[0]);self.assertIn('_study_table_encoding',sent)
   self.assertEqual(expand_study_tables(sent),compact_evidence_payload(p))
   self.assertEqual(state['request_payload_bytes'],len(seen[0].encode('utf-8')))
   self.assertGreater(state['request_table_bytes_saved'],0)

 def test_plain_input_override_leaves_original_evidence_untouched(self):
  from unittest.mock import patch
  from model_input import compact_study_tables
  p=self.payload()
  with patch.dict('os.environ',{'RF_STUDY_TABLE_INPUT':'0'}):self.assertIs(compact_study_tables(p),p)

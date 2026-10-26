import json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch

class EndToEndRegressions(unittest.TestCase):
 def test_reference_catalogue_ignores_commented_and_duplicate_labels(self):
  from manuscript_integrity import unique_label_targets
  source='\\label{active}\n% \\label{inactive}\n% \\label{active}\n\\label{duplicate}\\label{duplicate}\n'
  self.assertEqual(unique_label_targets(source),{'active'})
 def test_new_cross_reference_requires_a_validated_whole_document_target(self):
  from reviewforge_v4 import gate_block
  old='A bounded comparison of validation conditions. '*8;new=old+r' See \eqref{eq:known}.'
  self.assertFalse(gate_block(old,new)[0]);self.assertTrue(gate_block(old,new,known_reference_targets={'eq:known'})[0])
  self.assertFalse(gate_block(old,new.replace('eq:known','eq:invented'),known_reference_targets={'eq:known'})[0])
 def test_internal_source_locations_do_not_leak_into_manuscript_prose(self):
  from reviewforge_v4 import gate_block
  old='A bounded comparison of validation conditions. '*8
  self.assertFalse(gate_block(old,old+' (normalized source text offset 23400 + 279 chars)')[0])
  self.assertTrue(gate_block(old,old+' (p. 5; 279 observations)')[0])
 def test_assembly_retains_original_when_an_old_accepted_unit_is_malformed(self):
  from autonomous_review import bootstrap,assemble
  from synthesis_pipeline import initialize,units,digest,contract_digest,matrix_for_unit,unit_evidence,read
  from reviewforge import atomic_json
  from tests.test_synthesis_pipeline import SynthesisTests
  fixture=SynthesisTests()
  with tempfile.TemporaryDirectory() as t:
   ws=fixture.workspace(t);run,state=bootstrap(ws,9)
   # Bootstrap already initialized this isolated run. Fill only its local contract.
   plan=read(run/'synthesis_plan.json');u=units((run/'review_en.tex').read_text(encoding='utf-8'))[0];key=u['id']
   matrix=matrix_for_unit(run,key);arg=plan['units'][0];bad=u['body']+'\\begin{itemize}\n\\item Missing end.'
   folder=run/'synthesis_candidates/accepted';folder.mkdir(parents=True)
   (folder/(key+'.tex')).write_text(bad,encoding='utf-8')
   atomic_json(folder/(key+'.json'),{'status':'model_review_passed','source_sha256':digest((run/'review_en.tex').read_text(encoding='utf-8')),'unit_source_sha256':u['source_sha256'],'candidate_sha256':digest(bad),'contract_sha256':contract_digest(plan,matrix,unit_evidence(run,u,arg),key),'open_major_issues':[]})
   report=assemble(run,state);self.assertEqual(report['accepted_units'],0)
   self.assertIn(key,report['invalid_cached_candidates']);self.assertNotIn('Missing end.',Path(report['english']).read_text(encoding='utf-8'))
   atomic_json(folder/(key+'.json'),['invalid review object'])
   self.assertEqual(assemble(run,state)['accepted_units'],0)
 def test_all_supported_citation_commands_are_protected(self):
  from reviewforge_v4 import gate_block
  for command in ('citep','parencite','textcite','autocite','footcite','supercite'):
   with self.subTest(command=command):
    prose='A bounded comparison of validation conditions. '*8
    self.assertFalse(gate_block(prose+'\\'+command+'{OriginalStudy}',prose)[0])

 def test_unclosed_and_mismatched_environments_are_rejected_locally(self):
  from reviewforge_v4 import gate_block
  old='A bounded comparison of validation conditions. '*8
  for addition in ('\\begin{itemize}\n\\item Detail.','\\begin{itemize}\nDetail.\\end{enumerate}'):
   with self.subTest(addition=addition):self.assertFalse(gate_block(old,old+addition)[0])
  self.assertTrue(gate_block(old,old+'\\begin{itemize}\n\\item Detail.\\end{itemize}')[0])

 def test_reviewer_receives_only_the_current_draft_and_keeps_evidence(self):
  from tests.test_synthesis_pipeline import SynthesisTests
  from synthesis_pipeline import revise_unit
  fixture=SynthesisTests()
  with tempfile.TemporaryDirectory() as t:
   ws=fixture.workspace(t);u=fixture.prepared(ws);observed=[]
   def chat(system,payload,role):
    if role=='reviewer':
     observed.append(payload)
     self.assertNotIn('body',payload);self.assertNotIn('previous_candidate',payload)
     self.assertIn('candidate',payload);self.assertEqual(len(payload['study_comparisons']),2)
     self.assertTrue(payload['evidence_context']);self.assertEqual(payload['required_citation_keys'],['A','B'])
    return fixture.passing_chat(system,payload,role)
   self.assertEqual(revise_unit(ws,u['id'],chat,max_rounds=1)['status'],'model_review_passed')
   self.assertEqual(len(observed),1)

 def test_translation_reads_run_glossary_and_topic_but_keeps_output_cache(self):
  from autonomous_delivery import deliver_outputs
  with tempfile.TemporaryDirectory() as t:
   run=Path(t);out=run/'output';out.mkdir();(out/'review_en.tex').write_text('English',encoding='utf-8')
   (run/'translation_glossary.json').write_text(json.dumps({'growth':'specific term'}),encoding='utf-8')
   (run/'review_topic.txt').write_text('CUSTOM TOPIC',encoding='utf-8');seen=[]
   def translate(tex,workspace,ask,context,deadline):
    seen.append(json.loads(context));self.assertEqual(workspace,out);return 'Translated'
   with patch('reviewforge_v4.compile_tex',return_value={'status':'PASS'}),patch('translation_pipeline.translate_document',side_effect=translate):
    deliver_outputs(run,{'deadline':time.time()+1800},{'accepted_units':1},lambda *args:None,True)
   self.assertEqual(seen[0]['glossary'],{'growth':'specific term'});self.assertIn('CUSTOM TOPIC',seen[0]['brief'])

import json,tempfile,unittest
from pathlib import Path
from autonomous_review import bootstrap,coherence_review,read

class CoherenceBatchTests(unittest.TestCase):
 def test_self_conflict_can_be_anchored_inside_one_short_passage(self):
  class API:
   max_tokens=1000
   def chat(self,system,user,role):
    p=json.loads(user)['units'][0];return json.dumps({'issues':[{'unit_id':p['unit_id'],'id':'self','severity':'major','passage_id':p['passage_options'][0]['id'],'related_passage_ids':[],'self_conflict':True,'reason':'The two sentences specify opposite fixed splits.','required_change':'Reconcile the two clauses.'}]})
  with tempfile.TemporaryDirectory() as t:
   ws=Path(t);(ws/'review_en.tex').write_text('\\begin{document}\n\\subsection{Protocol}\nThe fixed split includes every test trajectory in training. The same fixed split excludes every test trajectory from training.\n\\end{document}',encoding='utf-8');run,state=bootstrap(ws,9);self.assertEqual(coherence_review(run,state,API()),[])
 def test_passage_ids_materialize_original_text_and_cross_unit_context(self):
  class API:
   calls=0;max_tokens=1000
   def chat(self,system,user,role):
    self.calls+=1;p=json.loads(user)['units']
    if self.calls>1:return json.dumps({'issues':[]})
    return json.dumps({'issues':[{'unit_id':p[0]['unit_id'],'id':'paired','severity':'major','passage_id':p[0]['passage_options'][0]['id'],'related_passage_ids':[p[1]['passage_options'][0]['id']],'reason':'Two anchored clauses conflict.','required_change':'Reconcile scope.'}]})
  with tempfile.TemporaryDirectory() as t:
   ws=Path(t);source=self.source(ws);run,state=bootstrap(ws,9);coherence_review(run,state,API());r=read(run/'reports/coherence_01.json');issue=r['verdict']['issues'][0]
   self.assertIn(issue['passage'],source);self.assertIn(issue['related_passages'][0]['passage'],source);self.assertNotEqual(issue['unit_id'],issue['related_passages'][0]['unit_id'])
 def source(self,ws):
  text='\\begin{document}\n'+''.join('\\subsection{Topic '+str(i)+'}\n'+('A bounded comparison considers validation and evidence limitations. '*35)+'\n' for i in range(20))+'\\end{document}'
  (ws/'review_en.tex').write_text(text,encoding='utf-8');return text
 def test_large_review_is_bounded_complete_and_resumable(self):
  requests=[]
  class API:
   max_tokens=1000
   def chat(self,system,user,role):
    if len(user)>43000:raise AssertionError('Monolithic coherence request')
    requests.append(json.loads(user));return json.dumps({'issues':[]})
  with tempfile.TemporaryDirectory() as t:
   ws=Path(t);source=self.source(ws);run,state=bootstrap(ws,9)
   self.assertEqual(coherence_review(run,state,API()),[])
   self.assertGreater(len(requests),1)
   complete=[p for r in requests if r['scope']=='complete_unit_windows' for p in r['units']]
   self.assertEqual({p['unit_id'] for p in complete},set(state['tasks']))
   self.assertTrue(all(p['text'] in source for p in complete))
   count=len(requests);coherence_review(run,state,API());self.assertEqual(len(requests),count)
 def test_unit_windows_cover_long_input_without_silent_truncation(self):
  from autonomous_review import coherence_batches
  text=''.join(chr(65+i%26) for i in range(70000));packets=[{'unit_id':'u','heading':'Heading','text':text}]
  batches=coherence_batches(packets)
  windows=[p for b in batches if b['scope']=='complete_unit_windows' for p in b['units']]
  covered=set()
  for p in windows:
   start=p['window_start'];end=p['window_end'];self.assertEqual(p['text'],text[start:end]);covered.update(range(start,end))
  self.assertEqual(len(covered),len(text));self.assertTrue(all(sum(len(p['text']) for p in b['units'])<=32000 for b in batches))
 def test_partial_failure_preserves_every_known_major_issue(self):
  from tests.test_synthesis_pipeline import SynthesisTests
  from synthesis_pipeline import revise_unit
  from reviewforge import atomic_json
  fixture=SynthesisTests()
  with tempfile.TemporaryDirectory() as t:
   ws=fixture.workspace(t);source=(ws/'review_en.tex').read_text(encoding='utf-8');source=source.replace(r'\end{document}',''.join('\\subsection{Extra '+str(i)+'}\n'+('A bounded comparison considers validation. '*80)+'\n' for i in range(20))+r'\end{document}');(ws/'review_en.tex').write_text(source,encoding='utf-8')
   u=fixture.prepared(ws);revise_unit(ws,u['id'],fixture.passing_chat,max_rounds=1)
   atomic_json(ws/'synthesis_candidates'/(u['id']+'.json'),['corrupt latest working report'])
   # Coherence consumes this already-reviewed snapshot directly.
   state={'deadline':__import__('time').time()+1000,'tasks':{p['id']:{'status':'completed' if p['id']==u['id'] else 'pending'} for p in __import__('synthesis_pipeline').units(source)}}
   class API:
    calls=0;max_tokens=1000
    def chat(self,system,user,role):
     self.calls+=1
     if self.calls>1:raise RuntimeError('API attempts failed: simulated later-batch outage')
     packets=json.loads(user)['units'];first=next(p for p in packets if p['unit_id']==u['id']);other=next(p for p in packets if p['unit_id']!=u['id'])
     return json.dumps({'issues':[{'unit_id':u['id'],'id':key,'severity':'major','passage_id':first['passage_options'][0]['id'],'related_passage_ids':[other['passage_options'][0]['id']],'reason':'A distinct concern '+key,'required_change':'Repair '+key} for key in ('A','B')]})
   with self.assertRaises(RuntimeError):coherence_review(ws,state,API())
   record=read(ws/'synthesis_candidates/accepted'/(u['id']+'.json'));self.assertEqual(len(record['open_major_issues']),2);self.assertEqual(state['tasks'][u['id']]['status'],'retry')
   report=read(ws/'reports/coherence_01.json');self.assertEqual(report['status'],'incomplete');self.assertEqual(report['completed_batches'],1)

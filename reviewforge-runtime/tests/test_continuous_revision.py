import tempfile,unittest
from pathlib import Path


class ContinuousTests(unittest.TestCase):
 def test_new_cooldown_survives_restart_and_status_changes(self):
  from continuous_revision import publish_worker_state,saved_cooldown,run_continuously
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);publish_worker_state(root,{'status':'WAITING_FOR_PROVIDER','retry_not_before_epoch':300},1)
   publish_worker_state(root,{'status':'STOPPED'},1)
   ticks=[];calls=[]
   run_continuously(lambda:calls.append(1),lambda e:{},lambda e:False,lambda:'same',
       lambda state:publish_worker_state(root,state,2),lambda:bool(ticks),sleep=lambda s:ticks.append(s),
       now=lambda:0,not_before=lambda:saved_cooldown(root))
   self.assertEqual(calls,[]);self.assertEqual(saved_cooldown(root),300)
 def test_unresolved_normal_result_does_not_exit_or_claim_completion(self):
  from continuous_revision import run_continuously
  states=[];ticks=[]
  result=run_continuously(lambda:{'status':'NEEDS_REVISION'},lambda e:{'category':'scientific_revision_required'},lambda e:False,
      lambda:'same',states.append,lambda:bool(ticks),sleep=lambda s:ticks.append(s))
  self.assertEqual(result['status'],'STOPPED')
  self.assertNotIn('COMPLETED',[s['status'] for s in states])
 def test_saved_provider_cooldown_prevents_all_requests(self):
  from continuous_revision import run_continuously
  ticks=[];calls=[]
  run_continuously(lambda:calls.append(1),lambda e:{},lambda e:False,lambda:'same',lambda s:None,
      lambda:len(ticks)>1,sleep=lambda s:ticks.append(s),now=lambda:0,not_before=lambda:100)
  self.assertEqual(calls,[])
 def repair_fixture(self,root):
  from reviewforge import atomic_json
  from study_registry import signature
  from paragraph_review import paragraph_options
  units=[{'id':'u1','heading':'Evidence'},{'id':'u2','heading':'Scope'}];binding='a'*64
  folder=root/'argument_units'/binding;folder.mkdir(parents=True)
  body=r'Reported 2 batches \cite{A}.'
  for u in units:
   c={'latex':body,'evidence_synthesis':[]}
   atomic_json(folder/(u['id']+'.json'),{'candidate':c,'candidate_sha256':signature(c),'accepted':True,'stage':'reviewed'})
   atomic_json(folder/(u['id']+'.budget.json'),{'full_writes':4,'paragraph_patches':6})
  whole='\\section{Evidence}\n'+'\n\n'.join('\\subsection{'+u['heading']+'}\n'+body for u in units)
  rows=[{'paragraph_id':p['id'],'function':'evidence','message':'Evidence','adds':'Result','decision':'revise' if i==0 else 'keep','destination':'main','reason':'Add inference' if i==0 else 'Checked'} for i,p in enumerate(paragraph_options(whole))]
  atomic_json(root/'3_test.json',{'candidate':{'latex':whole,'_argument_units':units,'_argument_units_binding':binding},'review':{'paragraph_review':rows,'issues':['Add inference']},'attempt':10})
  atomic_json(root/'progress.json',{'sections_completed':2})
  return folder,body

 def test_structural_repair_saves_unaccepted_draft_without_resetting_spend(self):
  import json
  from continuous_revision import repair_pending_section
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);folder,body=self.repair_fixture(root)
   before=(folder/'u1.budget.json').read_bytes()
   self.assertTrue(repair_pending_section(root,lambda *args:{'latex':body+' The scope is conditional.'}))
   row=json.loads((folder/'u1.json').read_text());self.assertFalse(row['accepted'])
   self.assertEqual(row['stage'],'pending_review');self.assertIsNone(row['review'])
   self.assertEqual(before,(folder/'u1.budget.json').read_bytes())
   self.assertEqual(len(list((root/'structural_repair_archive').glob('*.json'))),1)

 def test_numeric_change_is_rejected_and_same_issue_not_sent_again(self):
  import json
  from continuous_revision import repair_pending_section
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);folder,body=self.repair_fixture(root);calls=[]
   def ask(*args):calls.append(1);return {'latex':body.replace('2','3')}
   self.assertTrue(repair_pending_section(root,ask))
   self.assertFalse(repair_pending_section(root,ask))
   self.assertEqual(len(calls),1);self.assertEqual(json.loads((folder/'u1.json').read_text())['candidate']['latex'],body)
 def test_transport_failure_can_resume_once_without_erasing_reservations(self):
  import json
  from continuous_revision import repair_pending_section
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);folder,body=self.repair_fixture(root)
   def fail(*args):raise TimeoutError('timed out')
   with self.assertRaises(TimeoutError):repair_pending_section(root,fail)
   self.assertTrue(repair_pending_section(root,lambda *args:{'latex':body+' Qualified.'}))
   budget=json.loads((root/'structural_repairs.json').read_text())
   self.assertEqual(budget['calls'],2)
   self.assertEqual(next(iter(budget['issues'].values()))['attempts'],2)
 def test_worker_lock_prevents_duplicates_and_releases_on_close(self):
  from continuous_revision import claim_worker
  with tempfile.TemporaryDirectory() as t:
   first=claim_worker(Path(t))
   try:
    with self.assertRaises(RuntimeError):claim_worker(Path(t))
   finally:first.close()
   second=claim_worker(Path(t));second.close()
 def test_scientific_repair_continues_to_real_completion(self):
  from continuous_revision import run_continuously
  attempts=[];repairs=[];states=[]
  def operation():
   attempts.append(1)
   if len(attempts)==1:raise ValueError('Scientific revision required')
   return {'status':'PROVISIONAL_MODEL_PASS','exports':{'english':'PASS','chinese':'PASS'}}
  result=run_continuously(operation,lambda e:{'category':'scientific_revision_required'},lambda e:repairs.append(1) or True,
       lambda:'same',states.append,lambda:False,sleep=lambda s:None)
  self.assertEqual(result['status'],'PROVISIONAL_MODEL_PASS');self.assertEqual(len(repairs),1)

 def test_unchanged_rejection_waits_without_repeated_requests(self):
  from continuous_revision import run_continuously
  calls=[];ticks=[];states=[]
  def operation():calls.append(1);raise ValueError('Unresolved')
  result=run_continuously(operation,lambda e:{'category':'validation_failure'},lambda e:False,
       lambda:'same',states.append,lambda:len(ticks)>=3,sleep=lambda s:ticks.append(s))
  self.assertEqual(len(calls),1);self.assertEqual(result['status'],'STOPPED')
  self.assertTrue(any(s['status']=='WAITING_FOR_DIAGNOSIS' for s in states))

 def test_changed_checkpoint_resumes_without_resetting_budgets(self):
  from continuous_revision import run_continuously
  ticks=[];calls=[]
  def operation():
   calls.append(1)
   if len(calls)==1:raise ValueError('Unresolved')
   return {'status':'PROVISIONAL_MODEL_PASS','exports':{'english':'PASS','chinese':'PASS'}}
  result=run_continuously(operation,lambda e:{'category':'validation_failure'},lambda e:False,
       lambda:str(len(ticks)),lambda s:None,lambda:False,sleep=lambda s:ticks.append(s))
  self.assertEqual(result['status'],'PROVISIONAL_MODEL_PASS');self.assertEqual(len(calls),2)

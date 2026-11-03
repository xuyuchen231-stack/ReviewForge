import unittest,tempfile
from pathlib import Path
from local_paragraph_repair import repair_paragraphs
from paragraph_review import paragraph_records
from pipeline_recovery import run_with_recovery
class RepairRecoveryTests(unittest.TestCase):
 def test_patch_preserves_other_paragraphs_and_math(self):
  original=r'The estimate is $x=1$ for 23 batches. Needless closing words.'+'\n\n'+r'Another finding \cite{A}.'
  rows=paragraph_records(original);candidate={'latex':original,'evidence_synthesis':[{'finding':'23','citekeys':['A'],'fact_ids':['f1']}]}
  review={'paragraph_review':[{'paragraph_id':rows[0]['id'],'decision':'revise','destination':'main','reason':'Trim closing words'}]}
  def ask(system,payload,required,role):return {'replacements':[{'paragraph_id':rows[0]['id'],'latex':r'The estimate is $x=1$ for 23 batches.'}]}
  result=repair_paragraphs(ask,candidate,review,{'known_citekeys':['A']})
  self.assertEqual(result['latex'],r'The estimate is $x=1$ for 23 batches.'+'\n\n'+r'Another finding \cite{A}.')
 def test_patch_cannot_change_numeric_or_math_content(self):
  original=r'The estimate is $x=1$ for 23 batches.';row=paragraph_records(original)[0]
  candidate={'latex':original};review={'paragraph_review':[{'paragraph_id':row['id'],'decision':'revise','destination':'main','reason':'Tighten'}]}
  for text in [r'The estimate is $x=2$ for 23 batches.',r'The estimate is $x=1$ for 24 batches.']:
   with self.assertRaises(ValueError):repair_paragraphs(lambda *a:{'replacements':[{'paragraph_id':row['id'],'latex':text}]},candidate,review,{'known_citekeys':[]})
 def test_network_recovery_runs_without_repeating_prior_stages(self):
  attempts=[];delays=[]
  def operation():
   attempts.append(1)
   if len(attempts)<2:raise TimeoutError('fixture')
   return 'done'
  result=run_with_recovery(operation,lambda e:{'category':'connection_failure'},lambda e,n:None,sleep=delays.append)
  self.assertEqual(result,'done');self.assertEqual(delays,[10])
 def test_scientific_rejection_not_classified_as_network_retry(self):
  calls=[]
  def operation():calls.append(1);raise ValueError('scientific rejection')
  with self.assertRaises(ValueError):run_with_recovery(operation,lambda e:{'category':'validation_failure'},lambda e,n:None,sleep=lambda _:None)
  self.assertEqual(len(calls),1)
 def test_recovery_has_hard_attempt_limit(self):
  attempts=[]
  def operation():attempts.append(1);raise TimeoutError('fixture')
  with self.assertRaises(TimeoutError):run_with_recovery(operation,lambda e:{'category':'connection_failure'},lambda e,n:None,sleep=lambda _:None,max_retries=2)
  self.assertEqual(len(attempts),3)

import unittest
from paragraph_review import paragraph_records


class IssueHistoryTests(unittest.TestCase):
 def test_diagnosed_resume_is_explicit_bound_and_never_resets_spend(self):
  import json
  from study_registry import signature
  from review_convergence import block_repair,repair_blocked
  budget={'full_writes':3,'paragraph_patches':5};candidate={'latex':'Claim.'}
  block_repair(budget,candidate,'No progress')
  budget=json.loads(json.dumps(budget));self.assertTrue(repair_blocked(budget,candidate))
  with self.assertRaises(ValueError):repair_blocked(budget,candidate,{'reason':'retry'})
  diagnosis={'block_sha256':signature(budget['convergence_block']),'reason':'Source qualification inspected','action':'Correct the quoted independence claim'}
  self.assertFalse(repair_blocked(budget,candidate,diagnosis))
  self.assertEqual(budget['full_writes'],3);self.assertEqual(budget['paragraph_patches'],5)
  block_repair(budget,candidate,'No progress')
  self.assertTrue(repair_blocked(budget,candidate,diagnosis))

 def test_real_candidate_change_unblocks_without_erasing_history(self):
  from review_convergence import block_repair,repair_blocked
  budget={};block_repair(budget,{'latex':'Old.'},'No progress')
  self.assertFalse(repair_blocked(budget,{'latex':'Corrected.'}))
  self.assertEqual(len(budget['convergence_block_history']),1)
 def report(self,reason='Missing qualification'):
  return {'accepted':False,'checks':{'facts':False},'issues':[reason,reason],
          'paragraph_review':[{'paragraph_id':paragraph_records('Claim.')[0]['id'],
           'decision':'revise','destination':'main','category':'factual','severity':'major','reason':reason}]}

 def test_history_coalesces_duplicates_and_retains_exact_requirement(self):
  from review_convergence import track_review
  budget={};track_review(budget,self.report(),'Claim.')
  rows=list(budget['review_convergence']['issues'].values())
  self.assertEqual(len(rows),1);self.assertEqual(rows[0]['requirement'],'Missing qualification')
  self.assertEqual(rows[0]['paragraph_anchor'],'Claim.')
  self.assertFalse(rows[0]['resolved'])

 def test_stall_persists_across_serialization_and_changes_do_not_reset_budgets(self):
  import json
  from review_convergence import track_review
  budget={'full_writes':3,'paragraph_patches':5}
  self.assertFalse(track_review(budget,self.report(),'Claim.'))
  budget=json.loads(json.dumps(budget))
  self.assertFalse(track_review(budget,self.report(),'Claim.'))
  self.assertTrue(track_review(budget,self.report(),'Claim.'))
  self.assertFalse(track_review(budget,self.report('Wrong number'),'Claim.'))
  self.assertEqual(budget['full_writes'],3);self.assertEqual(budget['paragraph_patches'],5)

 def test_unbound_false_gate_still_counts_and_optional_style_does_not(self):
  from review_convergence import track_review
  budget={};r={'accepted':False,'checks':{'facts':False},'issues':['Unresolved source'],'paragraph_review':[]}
  for _ in range(3):stalled=track_review(budget,r,'Claim.')
  self.assertTrue(stalled)
  optional=self.report();optional['paragraph_review'][0].update(severity='minor',category='style')
  b={};track_review(b,optional,'Claim.')
  self.assertEqual(b['review_convergence']['active_issue_ids'],[])

 def test_whitespace_only_duplicate_requirements_share_an_id(self):
  from review_convergence import track_review
  b={};track_review(b,self.report('Missing  qualification'),'Claim.')
  track_review(b,self.report('Missing qualification'),'Claim.')
  self.assertEqual(len(b['review_convergence']['issues']),1)


class OptionalRepairTests(unittest.TestCase):
 def test_optional_style_is_not_sent_for_repair(self):
  from local_paragraph_repair import repair_paragraphs
  body='Evidence.\n\nContext.';rows=paragraph_records(body);seen=[]
  review={'paragraph_review':[
   {'paragraph_id':rows[0]['id'],'decision':'revise','destination':'main','severity':'major','category':'factual','reason':'Clarify scope'},
   {'paragraph_id':rows[1]['id'],'decision':'revise','destination':'main','severity':'minor','category':'style','reason':'Prefer another word'}]}
  def ask(system,packet,*args):
   seen.extend(p['paragraph_id'] for p in packet['paragraphs'])
   return {'replacements':[{'paragraph_id':rows[0]['id'],'latex':'Qualified evidence.'}]}
  result=repair_paragraphs(ask,{'latex':body},review,{'known_citekeys':[],'canonical_studies':[]})
  self.assertEqual(seen,[rows[0]['id']]);self.assertTrue(result['latex'].endswith('Context.'))

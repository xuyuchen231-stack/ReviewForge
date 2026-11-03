import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('campaign_state',Path(__file__).resolve().parents[2]/'reviewforge/scripts/campaign_state.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class CampaignTests(unittest.TestCase):
 def snapshot(self):return {'revision':'r1','reviewed_revision':'r1','checks':{'facts':'PASS','citations':'PASS'},'issues':[],'history':[]}
 def test_score_cannot_overrule_open_major(self):
  s=self.snapshot();s.update(score=9,accepted=True,issues=[{'id':'i1','severity':'MAJOR','status':'OPEN'}]);r=m.assess(s)
  self.assertEqual(r['status'],'BLOCKED');self.assertEqual(r['next_action'],'REPAIR_BLOCKING_ISSUES');self.assertFalse(r['submission_ready'])
 def test_cooldown_is_not_stagnation(self):
  s=self.snapshot();s.update(wait_until_epoch=1000,history=[{'kind':'provider_wait'},{'kind':'provider_wait'}]);r=m.assess(s,now=500)
  self.assertEqual(r['next_action'],'WAIT_PROVIDER');self.assertEqual(r['stale_completed_reviews'],0)
 def test_two_completed_no_gain_reviews_request_a_new_strategy(self):
  s=self.snapshot();s['issues']=[{'id':'style','severity':'MINOR','status':'OPEN'}];s['history']=[{'kind':'completed_review','review_id':str(i),'new_findings':[],'closed_issue_ids':[]} for i in range(2)]
  self.assertEqual(m.assess(s)['next_action'],'CHANGE_REPAIR_STRATEGY')
 def test_four_completed_no_gain_reviews_escalate_without_acceptance(self):
  s=self.snapshot();s['issues']=[{'id':'style','severity':'MINOR','status':'OPEN'}];s['history']=[{'kind':'completed_review','review_id':str(i)} for i in range(4)]
  r=m.assess(s);self.assertEqual(r['next_action'],'REPORT_PERSISTENT_BLOCKER');self.assertNotEqual(r['status'],'PROVISIONAL_MODEL_PASS')
 def test_changed_source_invalidates_completion(self):
  s=self.snapshot();s['revision']='r2';self.assertEqual(m.assess(s)['status'],'INCOMPLETE')
 def test_closed_issue_without_resolution_is_not_closed(self):
  s=self.snapshot();s['issues']=[{'id':'major','severity':'MAJOR','status':'CLOSED'}];self.assertEqual(m.assess(s)['status'],'BLOCKED')
 def test_actual_supported_gain_resets_stall(self):
  s=self.snapshot();s['history']=[{'kind':'completed_review','review_id':'a'},{'kind':'completed_review','review_id':'b','new_findings':['f1']},{'kind':'provider_wait'}]
  self.assertEqual(m.assess(s)['stale_completed_reviews'],0)
 def test_unknown_checks_are_not_passed(self):
  s=self.snapshot();s['checks']['layout']='UNKNOWN';self.assertEqual(m.assess(s)['status'],'INCOMPLETE')
 def test_complete_checks_are_only_provisional(self):
  r=m.assess(self.snapshot());self.assertEqual(r['status'],'PROVISIONAL_MODEL_PASS');self.assertFalse(r['expert_verified'])

 def test_unknown_or_whitespace_severity_cannot_sneak_past_acceptance(self):
  for severity in ['MAJOR ','strange']:
   s=self.snapshot();s['issues']=[{'id':'i','severity':severity,'status':'OPEN','required':False}]
   self.assertEqual(m.assess(s)['status'],'BLOCKED')
 def test_duplicate_review_is_not_another_round(self):
  s=self.snapshot();s['issues']=[{'id':'i','severity':'MINOR','status':'OPEN'}];s['history']=[{'kind':'completed_review','review_id':'same'}]*4
  r=m.assess(s);self.assertEqual(r['stale_completed_reviews'],1);self.assertEqual(r['next_action'],'LOCAL_PATCH_THEN_REVIEW')
 def test_other_task_or_evidence_scope_is_not_a_comparable_round(self):
  s=self.snapshot();s.update(task_id='t1',evidence_scope='e1',history=[{'kind':'completed_review','review_id':'a','task_id':'other','evidence_scope':'e1'},{'kind':'completed_review','review_id':'b','task_id':'t1','evidence_scope':'other'}])
  self.assertEqual(m.assess(s)['stale_completed_reviews'],0)

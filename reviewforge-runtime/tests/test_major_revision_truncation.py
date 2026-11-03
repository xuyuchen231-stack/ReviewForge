import unittest
from major_revision import provider_request
from editorial_refinement import resilient_request
class TruncationBudgetTests(unittest.TestCase):
 def test_budget_can_recover_above_old_24k_ceiling(self):
  class API:
   last_finish_reason=None
   def __init__(self):self.budgets=[]
   def chat(self,system,user,role):
    self.budgets.append(self.max_tokens)
    self.last_finish_reason='length' if self.max_tokens<=24000 else 'stop'
    return '{"latex":"complete"}'
  api=API()
  result=provider_request(api,'system',{},'latex','writer',retry=lambda request,deadline:resilient_request(request,deadline,sleep=lambda _:None))
  self.assertEqual(result,{'latex':'complete'})
  self.assertEqual(api.budgets,[18000,36000])
 def test_persistent_truncation_still_stops_and_never_accepts_partial(self):
  class API:
   last_finish_reason='length'
   def __init__(self):self.budgets=[]
   def chat(self,system,user,role):self.budgets.append(self.max_tokens);return '{"latex":"partial"}'
  api=API()
  with self.assertRaises(ValueError):provider_request(api,'system',{},'latex','writer',retry=lambda request,deadline:resilient_request(request,deadline,sleep=lambda _:None))
  self.assertEqual(api.budgets,[18000,36000,48000])

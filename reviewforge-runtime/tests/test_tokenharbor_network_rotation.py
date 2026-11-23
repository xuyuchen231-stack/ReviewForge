import json,tempfile,time,unittest
from pathlib import Path
from io import BytesIO
from unittest.mock import patch
from reviewforge import CompatibleAPI

class NetworkRotationTests(unittest.TestCase):
 def test_network_failed_weekly_priority_key_is_not_reselected_for_fallback(self):
  with tempfile.TemporaryDirectory() as d:
   env={'RF_API_KEYS':'alpha,beta','RF_BASE_URL':'https://tokenharbor.ai/v1','RF_WRITER_MODEL':'writer:free','RF_REVIEWER_MODEL':'reviewer:free','RF_FALLBACK_MODEL':'fallback:free','RF_TOKENHARBOR_CYCLES_FILE':str(Path(d)/'cycles.json'),'RF_ACCOUNT_HEALTH_FILE':str(Path(d)/'health.json'),'RF_PROVIDER_FILE':str(Path(d)/'absent.json')}
   seen=[]
   class Response:
    def __enter__(self):return BytesIO(b'{"choices":[{"message":{"content":"OK"}}]}')
    def __exit__(self,*a):return False
   def send(req,timeout):
    seen.append(req.get_header('Authorization'))
    if len(seen)==1:raise TimeoutError('read stalled after send')
    return Response()
   with patch.dict('os.environ',env),patch('reviewforge.open_chat_response',side_effect=send):
    api=CompatibleAPI();self.assertEqual(api.chat('system','evidence'),'OK')
    self.assertEqual(seen,['Bearer alpha','Bearer beta'])
    again=CompatibleAPI();self.assertEqual(again.key_statuses[0],'temporary_network_failure')
    self.assertGreater(again.key_cooldowns[0],time.time())
    self.assertEqual(again.chat('system','next evidence'),'OK')
    self.assertEqual(seen[-1],'Bearer beta')
    state=json.loads(Path(d,'cycles.json').read_text())
    self.assertFalse(any(r.get('exhausted_until') for r in state['accounts'].values()))
 def test_all_network_cooled_accounts_are_not_reported_as_quota_exhausted(self):
  from editorial_refinement import request_failure
  with tempfile.TemporaryDirectory() as d:
   env={'RF_API_KEYS':'alpha,beta','RF_BASE_URL':'https://tokenharbor.ai/v1','RF_WRITER_MODEL':'writer:free','RF_REVIEWER_MODEL':'reviewer:free','RF_FALLBACK_MODEL':'fallback:free','RF_TOKENHARBOR_CYCLES_FILE':str(Path(d)/'cycles.json'),'RF_ACCOUNT_HEALTH_FILE':str(Path(d)/'health.json'),'RF_PROVIDER_FILE':str(Path(d)/'absent.json')}
   with patch.dict('os.environ',env),patch('reviewforge.open_chat_response',side_effect=TimeoutError('read stalled')):
    api=CompatibleAPI()
    with self.assertRaises(ConnectionError) as result:api.chat('system','evidence')
    self.assertEqual(request_failure(result.exception)['category'],'connection_failure')
    self.assertEqual(set(api.key_statuses.values()),{'temporary_network_failure'})
if __name__=='__main__':unittest.main()

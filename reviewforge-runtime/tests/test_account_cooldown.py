import json,tempfile,time,unittest,urllib.error
from pathlib import Path
from unittest.mock import patch
from io import BytesIO
from reviewforge import CompatibleAPI

class AccountCooldownTests(unittest.TestCase):
 def test_rate_limited_key_rotates_and_remains_temporarily_cooled_after_restart(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'health.json'
   env={'RF_API_KEYS':'first-test,second-test','RF_BASE_URL':'https://example.invalid/v1','RF_MODEL':'test','RF_FALLBACK_MODEL':'test','RF_ALLOW_RATE_LIMIT_FAILOVER':'1','RF_ACCOUNT_COOLDOWN_SECONDS':'36000','RF_ACCOUNT_HEALTH_FILE':str(path)}
   class Response:
    def __enter__(self):return BytesIO(b'{"choices":[{"message":{"content":"ok"}}]}')
    def __exit__(self,*args):return False
   calls=[]
   def open_request(req,timeout):
    calls.append(req.get_header('Authorization'))
    if calls[-1]=='Bearer first-test':raise urllib.error.HTTPError(req.full_url,429,'limited',{'Retry-After':'3600'},None)
    return Response()
   with patch.dict('os.environ',env),patch('reviewforge.urllib.request.urlopen',side_effect=open_request):
    self.assertEqual(CompatibleAPI().chat('s','u'),'ok')
    self.assertTrue(path.exists())
    data=path.read_text();self.assertNotIn('first-test',data)
    a=CompatibleAPI();self.assertGreater(a.key_cooldowns[0],time.time()+35900)
    self.assertEqual(a.chat('s','u'),'ok')
   self.assertEqual(calls,['Bearer first-test','Bearer second-test','Bearer second-test'])

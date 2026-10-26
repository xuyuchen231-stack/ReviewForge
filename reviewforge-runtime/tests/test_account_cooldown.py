import json,tempfile,time,unittest,urllib.error
from pathlib import Path
from unittest.mock import patch
from io import BytesIO
from reviewforge import CompatibleAPI

class AccountCooldownTests(unittest.TestCase):
 def test_quota_exhausted_account_is_skipped_for_following_requests(self):
  with tempfile.TemporaryDirectory() as t:
   env={'RF_API_KEYS':'used,available','RF_BASE_URL':'https://example.invalid/v1','RF_WRITER_MODEL':'test','RF_FALLBACK_MODEL':'test','RF_ALLOW_BILLING_FAILOVER':'1','RF_ACCOUNT_HEALTH_FILE':str(Path(t)/'health.json')};seen=[]
   class Response:
    def __enter__(self):return BytesIO(b'{"choices":[{"message":{"content":"ok"}}]}')
    def __exit__(self,*a):return False
   def request(req,timeout):
    key=req.get_header('Authorization');seen.append(key)
    if key=='Bearer used':raise urllib.error.HTTPError(req.full_url,402,'quota depleted',{},None)
    return Response()
   with patch.dict('os.environ',env),patch('reviewforge.urllib.request.urlopen',side_effect=request):
    api=CompatibleAPI();api.chat('s','u');api.key_index=0;api.chat('s','u');CompatibleAPI().chat('s','u')
   self.assertEqual(seen,['Bearer used','Bearer available','Bearer available','Bearer available'])
 def setUp(self):
  from unittest.mock import patch
  directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
  environment=patch.dict('os.environ',{'RF_PROVIDER_FILE':str(Path(directory.name)/'not_configured.json')});environment.start();self.addCleanup(environment.stop)
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

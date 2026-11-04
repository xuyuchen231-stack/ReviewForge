import json,tempfile,unittest,urllib.error
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from reviewforge import CompatibleAPI

class BeatAPIProviderTests(unittest.TestCase):
 def config(self):
  return {'name':'beatapi','RF_BASE_URL':'https://api.beatapi.io/v1','RF_API_KEY':'beat-secret','RF_WRITER_MODEL':'deepseek-v4.1-flash-free','RF_REVIEWER_MODEL':'deepseek-v4.1-flash-free','RF_FALLBACK_MODEL':'glm-5.3-flash-free','RF_BEATAPI_FREE_ONLY':'1'}
 def test_paid_model_is_rejected(self):
  for changed in ({'RF_WRITER_MODEL':'deepseek-v4.1-flash'},{'RF_BEATAPI_FREE_ONLY':'0'}):
   with self.assertRaises(ValueError):CompatibleAPI({**self.config(),**changed})
 def test_free_endpoint_and_success_persists_minute_window(self):
  from beatapi_provider import allowed_beatapi
  with tempfile.TemporaryDirectory() as t,patch.dict('os.environ',{'RF_ACCOUNT_HEALTH_FILE':str(Path(t)/'health.json')}):
   api=CompatibleAPI(self.config());self.assertTrue(allowed_beatapi(api));self.assertIsNone(api.weekly_accounts)
   def request(req,timeout):
    self.assertEqual(req.full_url,'https://api.beatapi.io/v1/chat/completions')
    self.assertEqual(json.loads(req.data)['model'],'deepseek-v4.1-flash-free')
    return BytesIO(b'{"choices":[{"message":{"content":"OK"},"finish_reason":"stop"}],"model":"deepseek-v4.1-flash-free"}')
   with patch('reviewforge.urllib.request.urlopen',side_effect=request):self.assertEqual(api.chat('s','u'),'OK')
   self.assertGreater(api.key_cooldowns[0],0)
   self.assertTrue(Path(t,'health.json').exists())
 def test_429_uses_server_delay_not_tokenharbor_ten_hours(self):
  with tempfile.TemporaryDirectory() as t,patch.dict('os.environ',{'RF_ACCOUNT_HEALTH_FILE':str(Path(t)/'health.json')}):
   api=CompatibleAPI(self.config())
   error=urllib.error.HTTPError('https://api.beatapi.io/v1/chat/completions',429,'limit',{'Retry-After':'60'},BytesIO(b'{}'))
   with patch('reviewforge.urllib.request.urlopen',side_effect=error):
    with self.assertRaisesRegex(RuntimeError,'Retry-After: 6[01]'):api.chat('s','u')
 def test_save_keeps_existing_accounts_and_disables_paid_fallback(self):
  from configure_beatapi import save_profile
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/'profiles.json';path.write_text(json.dumps({'providers':[{'name':'freeai','enabled':True},{'name':'apimaster','enabled':False}]}))
   save_profile(path,'sk_beat_test_secret_123')
   rows=json.loads(path.read_text())['providers'];self.assertEqual(len(rows),3)
   self.assertFalse(rows[1]['enabled']);self.assertEqual(rows[2]['RF_BEATAPI_FREE_ONLY'],'1')

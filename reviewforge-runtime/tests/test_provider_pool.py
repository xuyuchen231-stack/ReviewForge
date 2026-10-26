import json,tempfile,unittest,time
from pathlib import Path
from unittest.mock import patch
from reviewforge import CompatibleAPI

class ProviderPoolTests(unittest.TestCase):
 def test_first_model_cannot_consume_entire_fallback_budget(self):
  from io import BytesIO
  with tempfile.TemporaryDirectory() as t,patch.dict('os.environ',{'RF_BASE_URL':'https://primary.example/v1','RF_API_KEY':'first-key','RF_API_KEYS':'','RF_PROVIDER_FILE':str(Path(t)/'absent.json'),'RF_ACCOUNT_HEALTH_FILE':str(Path(t)/'health.json'),'RF_WRITER_MODEL':'first','RF_FALLBACK_MODEL':'second'}):
   api=CompatibleAPI();api.call_timeout=180;api.request_timeout=150;timeouts=[]
   class Response:
    def __enter__(self):return BytesIO(b'{"choices":[{"message":{"content":"ok"}}]}')
    def __exit__(self,*args):return False
   def request(req,timeout):
    timeouts.append(timeout)
    if len(timeouts)==1:raise TimeoutError('simulated first model stall')
    return Response()
   with patch('reviewforge.urllib.request.urlopen',side_effect=request):self.assertEqual(api.chat('s','u'),'ok')
   self.assertLessEqual(timeouts[0],91);self.assertEqual(api.last_model,'second')
 def test_preferred_provider_is_used_for_writing_but_preparation_can_use_primary(self):
  with tempfile.TemporaryDirectory() as t,patch.dict('os.environ',{'RF_BASE_URL':'https://primary.example/v1','RF_API_KEY':'first-key','RF_API_KEYS':'','RF_PROVIDER_FILE':str(Path(t)/'profiles.json'),'RF_ACCOUNT_HEALTH_FILE':str(Path(t)/'health.json')}):
   Path(t,'profiles.json').write_text(json.dumps({'preferred_provider':'apimaster','providers':[{'name':'apimaster','RF_BASE_URL':'https://apimaster.ai/v1','RF_API_KEY':'second-key'}]}))
   api=CompatibleAPI();seen=[]
   def request(client,*args):seen.append(client.provider_name);return 'ok'
   with patch.object(CompatibleAPI,'_chat',request):
    api.chat('s','u');api.request_stage='preparation';api.chat('s','u');api.request_stage='coherence';api.chat('s','u')
   self.assertEqual(seen,['apimaster','primary','primary'])
 def test_all_providers_cooling_retains_retry_after(self):
  with tempfile.TemporaryDirectory() as t,patch.dict('os.environ',{'RF_BASE_URL':'https://primary.example/v1','RF_API_KEY':'first-key','RF_API_KEYS':'','RF_PROVIDER_FILE':str(Path(t)/'absent.json'),'RF_ACCOUNT_HEALTH_FILE':str(Path(t)/'health.json')}):
   api=CompatibleAPI();api.providers=[CompatibleAPI({'name':'apimaster','RF_BASE_URL':'https://apimaster.ai/v1','RF_API_KEY':'second-key'})]
   with patch.object(CompatibleAPI,'_chat',side_effect=RuntimeError('Provider rate limit (429); respect Retry-After: 36000')):
    with self.assertRaisesRegex(RuntimeError,'Retry-After: 36000'):api.chat('s','u')
 def test_setup_preserves_other_provider_and_does_not_duplicate_apimaster(self):
  from configure_apimaster import save_profile
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/'profiles.json';path.write_text(json.dumps({'providers':[{'name':'other','RF_API_KEY':'other-secret'}]}))
   save_profile(path,'first','writer','reviewer');save_profile(path,'replacement','writer2','reviewer2')
   rows=json.loads(path.read_text(encoding='utf-8'))['providers'];self.assertEqual(len(rows),2);self.assertEqual(rows[0]['RF_API_KEY'],'other-secret');self.assertEqual(rows[1]['RF_API_KEY'],'replacement');self.assertEqual(rows[1]['RF_BASE_URL'],'https://apimaster.ai/v1')
 def test_backup_keeps_keys_models_and_base_isolated(self):
  with tempfile.TemporaryDirectory() as t:
   profiles=Path(t)/'providers.json';profiles.write_text(json.dumps({'providers':[{'name':'apimaster','RF_BASE_URL':'https://apimaster.ai/v1','RF_API_KEY':'second-key','RF_WRITER_MODEL':'writer-two','RF_REVIEWER_MODEL':'review-two','RF_FALLBACK_MODEL':'review-two'}]}))
   with patch.dict('os.environ',{'RF_BASE_URL':'https://primary.example/v1','RF_API_KEY':'first-key','RF_API_KEYS':'','RF_PROVIDER_FILE':str(profiles),'RF_ACCOUNT_HEALTH_FILE':str(Path(t)/'health.json')},clear=False):
    api=CompatibleAPI();seen=[]
    def request(client,system,user,role):
     seen.append((client.base,client.key,client.model,client.call_timeout,role))
     if client.base!='https://apimaster.ai/v1':raise RuntimeError('API attempts failed: HTTP 429')
     client.last_model=client.reviewer_model;client.last_key_slot=1;return 'backup result'
    api.call_timeout=600;api.deadline=time.time()+600
    with patch.object(CompatibleAPI,'_chat',request):self.assertEqual(api.chat('system','private payload','reviewer'),'backup result')
    self.assertEqual(seen[0][:3],('https://primary.example/v1','first-key',api.model));self.assertEqual(seen[1][:3],('https://apimaster.ai/v1','second-key','writer-two'))
    self.assertLessEqual(seen[0][3],301);self.assertEqual(api.last_provider,'apimaster');self.assertEqual(api.last_model,'review-two');self.assertEqual(api.call_timeout,600)
 def test_successful_primary_does_not_contact_backup(self):
  with tempfile.TemporaryDirectory() as t,patch.dict('os.environ',{'RF_BASE_URL':'https://primary.example/v1','RF_API_KEY':'first-key','RF_API_KEYS':'','RF_PROVIDER_FILE':str(Path(t)/'absent.json'),'RF_ACCOUNT_HEALTH_FILE':str(Path(t)/'health.json')},clear=False):
   api=CompatibleAPI()
   with patch.object(CompatibleAPI,'_chat',return_value='ok') as request:self.assertEqual(api.chat('s','u'),'ok')
   self.assertEqual(request.call_count,1)

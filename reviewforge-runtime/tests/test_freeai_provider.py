import json,tempfile,unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from reviewforge import CompatibleAPI

class FreeAIProviderTests(unittest.TestCase):
 def test_freeai_402_tries_second_account_without_paid_model(self):
  import urllib.error
  with tempfile.TemporaryDirectory() as t,patch.dict('os.environ',{'RF_ACCOUNT_HEALTH_FILE':str(Path(t)/'health.json')}):
   api=CompatibleAPI(self.config());seen=[]
   def request(req,timeout):
    seen.append((req.headers.get('Authorization'),json.loads(req.data)['model']))
    if len(seen)==1:raise urllib.error.HTTPError(req.full_url,402,'quota',{},BytesIO(b'{}'))
    return BytesIO(b'{"choices":[{"message":{"content":"OK"},"finish_reason":"stop"}]}')
   with patch('reviewforge.open_chat_response',side_effect=request):self.assertEqual(api.chat('s','u'),'OK')
   self.assertEqual(seen,[('Bearer first-secret','qwen7b'),('Bearer second-secret','qwen7b')])
   self.assertIsNone(api.weekly_accounts)
 def config(self):
  return {'name':'freeai','RF_BASE_URL':'https://api.free.ai/v1','RF_API_KEYS':'first-secret,second-secret','RF_WRITER_MODEL':'qwen7b','RF_REVIEWER_MODEL':'qwen7b','RF_FALLBACK_MODEL':'qwen7b','RF_FREEAI_SELF_HOSTED_ONLY':'1'}
 def test_endpoint_and_usage_and_no_tokenharbor_cycle(self):
  from freeai_provider import allowed_freeai
  with tempfile.TemporaryDirectory() as t,patch.dict('os.environ',{'RF_ACCOUNT_HEALTH_FILE':str(Path(t)/'health.json')}):
   api=CompatibleAPI(self.config());self.assertTrue(allowed_freeai(api));self.assertIsNone(api.weekly_accounts)
   def request(req,timeout):
    self.assertEqual(req.full_url,'https://api.free.ai/v1/chat/')
    body=json.loads(req.data);self.assertEqual(body['model'],'qwen7b')
    return BytesIO(json.dumps({'choices':[{'message':{'content':'OK'},'finish_reason':'stop'}],'free_ai_usage':{'tokens_used':12,'tokens_charged':12,'source':'self_hosted','model':'qwen7b'}}).encode())
   with patch('reviewforge.open_chat_response',side_effect=request):self.assertEqual(api.chat('s','u'),'OK')
   self.assertEqual(api.last_free_ai_usage['tokens_charged'],12)
 def test_premium_or_unapproved_freeai_is_rejected_before_request(self):
  for changed in ({'RF_WRITER_MODEL':'openai/gpt-4o'},{'RF_FREEAI_SELF_HOSTED_ONLY':'0'}):
   with self.assertRaises(ValueError):CompatibleAPI({**self.config(),**changed})
 def test_oversized_freeai_backup_does_not_reduce_primary_request_time(self):
  with tempfile.TemporaryDirectory() as t,patch.dict('os.environ',{'RF_ACCOUNT_HEALTH_FILE':str(Path(t)/'health.json'),'RF_PROVIDER_FILE':str(Path(t)/'missing')}):
   api=CompatibleAPI({'RF_BASE_URL':'https://tokenharbor.ai/v1','RF_API_KEY':'primary-secret','RF_WRITER_MODEL':'x:free'})
   api.providers=[CompatibleAPI(self.config())];api.call_timeout=360
   seen=[]
   def request(client,*args):seen.append((client.provider_name,client.call_timeout));return 'OK'
   with patch.object(CompatibleAPI,'_chat',request):api.chat('s','x'*70000)
   self.assertEqual(len(seen),1);self.assertGreater(seen[0][1],350)
 def test_profile_saves_two_keys_without_touching_other_providers(self):
  from configure_freeai import save_profile
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/'providers.json';path.write_text(json.dumps({'providers':[{'name':'apimaster','enabled':False}]}))
   save_profile(path,['sk-free-one','sk-free-two'])
   data=json.loads(path.read_text());self.assertFalse(data['providers'][0]['enabled'])
   row=data['providers'][1];self.assertEqual(row['RF_API_KEYS'],'sk-free-one,sk-free-two')
   self.assertEqual(row['RF_FREEAI_SELF_HOSTED_ONLY'],'1')

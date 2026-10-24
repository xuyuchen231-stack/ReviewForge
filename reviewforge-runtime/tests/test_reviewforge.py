import json
import tempfile
import unittest
from pathlib import Path
from reviewforge import validate_ledger, extract_json, run

SOURCES=[{'id':'S1','title':'Example','excerpts':[{'locator':'p1','text':'This is an exact supporting excerpt from the original document.'}]}]
CLAIM=[{'claim':'Example claim','source_id':'S1','locator':'p1','quote':'This is an exact supporting excerpt','status':'supported'}]
class TestEvidence(unittest.TestCase):
    def test_valid_quote(self):
        self.assertTrue(validate_ledger(CLAIM,SOURCES)[0])
    def test_fabricated_quote(self):
        fake=[dict(CLAIM[0],quote='This excerpt never appeared in the document')]
        self.assertFalse(validate_ledger(fake,SOURCES)[0])
    def test_empty_ledger(self):
        self.assertFalse(validate_ledger([],SOURCES)[0])
    def test_json_fence(self):
        self.assertEqual(extract_json('```json\n{"a": 1}\n```')['a'],1)
    def test_checkpoint_resume(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); (p/'manuscript.md').write_text('# Test\nSome text here.')
            (p/'sources.json').write_text('[]')
            a=run(p,minutes=0,dry_run=True)
            b=run(p,minutes=0,dry_run=True,resume=True)
            self.assertEqual(a['original_sha256'],b['original_sha256'])
            self.assertTrue((p/'state.json').exists())
    def test_refuse_changed_original(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); (p/'manuscript.md').write_text('# Test\nSome text here.')
            (p/'sources.json').write_text('[]')
            run(p,minutes=0,dry_run=True)
            (p/'manuscript.md').write_text('CHANGED')
            with self.assertRaises(ValueError):run(p,minutes=0,dry_run=True,resume=True)
if __name__ == '__main__': unittest.main()

class TestLiveLoopMock(unittest.TestCase):
    def test_accept_and_checkpoint(self):
        from unittest.mock import patch
        from reviewforge import CompatibleAPI
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            (p/'manuscript.md').write_text('# Review\nA preliminary argument needs synthesis.')
            (p/'sources.json').write_text(json.dumps(SOURCES))
            revised='# Review\nA more carefully contextualized argument needs synthesis. Source S1 supports a limited observation.'
            proposal=json.dumps({'manuscript':revised,'ledger':CLAIM,'change_summary':'Contextualized argument'})
            verdict=json.dumps({'accept':True,'major_issues':[],'rationale':'Improved argument'})
            with patch('reviewforge.CompatibleAPI') as api:
                api.return_value.chat.side_effect=[proposal,verdict]
                with patch.dict('os.environ',{'RF_MAX_CALLS':'2'}):
                    result=run(p,minutes=1)
            self.assertEqual(result['iteration'],1)
            self.assertEqual(result['best_file'],'revisions/revision_0001.md')
            self.assertTrue((p/'reports/iteration_0001.json').exists())

class TestModelRouting(unittest.TestCase):
    def test_empty_reviewer_response_uses_available_writer_as_labeled_fallback(self):
        from unittest.mock import patch
        from io import BytesIO
        from reviewforge import CompatibleAPI
        calls=[]
        class Response:
            def __init__(self,content):self.content=content
            def __enter__(self):return BytesIO(json.dumps({'choices':[{'message':{'content':self.content}}]}).encode())
            def __exit__(self,*args):return False
        def opener(req,timeout):
            model=json.loads(req.data)['model'];calls.append(model)
            return Response('' if model=='critic' else 'ok')
        env={'RF_API_KEYS':'test-routing','RF_API_KEY':'test-routing','RF_BASE_URL':'https://routing.invalid','RF_WRITER_MODEL':'writer','RF_REVIEWER_MODEL':'critic','RF_FALLBACK_MODEL':'critic'}
        with patch.dict('os.environ',env),patch('reviewforge.urllib.request.urlopen',side_effect=opener):
            api=CompatibleAPI();self.assertEqual(api.chat('s','u',role='reviewer'),'ok')
            self.assertEqual(api.last_model,'writer')
        self.assertEqual(calls,['critic','writer'])
    def test_writer_and_reviewer_models(self):
        from unittest.mock import patch
        from io import BytesIO
        from reviewforge import CompatibleAPI
        calls = []
        class FakeResponse:
            def __enter__(self): return BytesIO(b'{"choices":[{"message":{"content":"ok"}}]}')
            def __exit__(self, *args): return False
        def opener(req, timeout):
            calls.append(json.loads(req.data.decode())['model'])
            return FakeResponse()
        env={'RF_API_KEY':'test-not-real','RF_BASE_URL':'https://example.invalid/v1','RF_WRITER_MODEL':'mimo-v2.6-flash:free','RF_REVIEWER_MODEL':'deepseek-v4.1-flash:free'}
        with patch.dict('os.environ',env), patch('reviewforge.urllib.request.urlopen',side_effect=opener):
            api=CompatibleAPI()
            self.assertEqual(api.chat('system','user',role='writer'),'ok')
            self.assertEqual(api.chat('system','user',role='reviewer'),'ok')
        self.assertEqual(calls,['mimo-v2.6-flash:free','deepseek-v4.1-flash:free'])

class TestEmptyDiagnostics(unittest.TestCase):
 def test_empty_response_reports_safe_metadata(self):
  from unittest.mock import patch
  from io import BytesIO
  from reviewforge import CompatibleAPI
  class Response:
   def __enter__(self):return BytesIO(json.dumps({'choices':[{'finish_reason':'length','message':{'content':'','reasoning_content':'private reasoning'}}]}).encode())
   def __exit__(self,*a):pass
  env={'RF_API_KEYS':'diagnostic-test','RF_BASE_URL':'https://example.invalid','RF_WRITER_MODEL':'model','RF_FALLBACK_MODEL':'model'}
  with patch.dict('os.environ',env),patch('reviewforge.urllib.request.urlopen',return_value=Response()):
   with self.assertRaisesRegex(RuntimeError,'finish_reason=length') as caught:CompatibleAPI().chat('s','u')
   self.assertNotIn('private reasoning',str(caught.exception))

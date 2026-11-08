import json,tempfile,unittest
from pathlib import Path
from study_registry import signature


class StableDeliveryTests(unittest.TestCase):
 def test_existing_run_worker_blocks_stable_route(self):
  from stable_delivery import run_stable
  from continuous_revision import claim_worker
  with tempfile.TemporaryDirectory() as t:
   ws=Path(t);run=ws/'autonomous_runs/test';run.mkdir(parents=True);self.fixture(run)
   (ws/'autonomous_active.json').write_text(json.dumps({'run_directory':'autonomous_runs/test'}))
   lock=claim_worker(run)
   try:
    with self.assertRaises(RuntimeError):run_stable(ws,4)
   finally:lock.close()
 def test_complete_route_exports_only_new_reading_copies_under_fixed_deadline(self):
  import types
  from unittest.mock import patch
  from stable_delivery import run_stable
  with tempfile.TemporaryDirectory() as t:
   ws=Path(t);run=ws/'autonomous_runs/test';run.mkdir(parents=True);source=self.fixture(run)
   (ws/'autonomous_active.json').write_text(json.dumps({'run_directory':'autonomous_runs/test'}))
   before=source.read_bytes();captured=[]
   def export(run,result,deadline,chat=None):
    from continuous_revision import claim_worker
    with self.assertRaises(RuntimeError):claim_worker(run)
    captured.append(deadline-result['run_started_epoch'])
    out=Path(result['versions']['condense']['path']).parent/'short/output/output';out.mkdir(parents=True)
    for name in ('review_en.pdf','review_zh.pdf'):(out/name).write_bytes(b'test fixture')
    result['exports']={'condense':{'status':'READY_FOR_READING','report':{'review_en_build':{'status':'PASS'},'review_zh_build':{'status':'PASS'}}}}
    return result
   fake=types.SimpleNamespace(base='https://example.test',model='free',reviewer_model='free',fallback_model='free',providers=[])
   with patch('reviewforge.load_env'),patch('reviewforge.CompatibleAPI',return_value=fake),patch('account_cycles.is_tokenharbor_free',return_value=True),patch('editorial_export.finalize_versions',side_effect=export):
    state=run_stable(ws,4)
   self.assertEqual(state['status'],'READING_COPIES_BUILT');self.assertFalse(state['submission_ready'])
   self.assertEqual(captured,[14400]);self.assertEqual(source.read_bytes(),before)
   self.assertNotEqual(Path(state['job']),source.parent)
 def fixture(self,root):
  from editorial_refinement import sha
  folder=root/'editorial/complete';folder.mkdir(parents=True)
  source=folder/'refined.tex';source.write_text('Complete manuscript',encoding='utf-8')
  (folder/'status.json').write_text(json.dumps({'status':'COMPLETE','versions':{'condense':{'path':str(source),'sha256':sha('Complete manuscript')}}}))
  return source
 def test_only_hash_verified_complete_manuscript_is_used(self):
  from stable_delivery import completed_baseline
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);source=self.fixture(root)
   self.assertEqual(completed_baseline(root)[0],source.resolve())
   source.write_text('Changed')
   with self.assertRaises(ValueError):completed_baseline(root)
 def test_incomplete_baseline_cannot_be_presented_as_complete(self):
  from stable_delivery import completed_baseline
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);source=self.fixture(root);p=source.parent/'status.json'
   d=json.loads(p.read_text());d['status']='PAUSED';p.write_text(json.dumps(d))
   with self.assertRaises(ValueError):completed_baseline(root)

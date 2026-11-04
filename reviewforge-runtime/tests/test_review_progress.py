import json
from pathlib import Path
import tempfile
import unittest
from review_progress import progress


class ReviewProgressTests(unittest.TestCase):
    def test_rate_limit_reports_cause_and_saved_deadline(self):
        with tempfile.TemporaryDirectory() as d:
            runtime,run,root=self.fixture(d)
            (run/'major_revision/running.log').write_text(json.dumps({'status':'PAUSED','details':str(root),'error_type':'RuntimeError','request_failure':{'category':'rate_limit'}}))
            (root/'monitor_wait.json').write_text(json.dumps({'retry_not_before_epoch':1893456000}))
            data=progress(runtime)
            self.assertIn('接口限流',data['reason'])
            self.assertIn('Pacific/Auckland',data['reason'])
            self.assertNotIn('RuntimeError',data['reason'])

    def fixture(self,d):
        runtime=Path(d);ws=runtime/'workspace';run=ws/'autonomous_runs/test';root=run/'major_revision/version';root.mkdir(parents=True)
        (ws/'autonomous_active.json').write_text(json.dumps({'run_directory':'autonomous_runs/test'}))
        (root/'plan.json').write_text('{}')
        return runtime,run,root

    def test_major_pause_is_visible_without_old_editorial_files(self):
        with tempfile.TemporaryDirectory() as d:
            runtime,run,root=self.fixture(d)
            (root/'progress.json').write_text(json.dumps({'stage':'facts','study':'Du2022','studies_processed':19,'studies_total':86}))
            (run/'major_revision/running.log').write_text(json.dumps({'status':'PAUSED','details':str(root),'reason':'Invalid evidence IDs','study':'Du2022'}))
            data=progress(runtime)
            self.assertEqual(data['kind'],'major_revision');self.assertEqual(data['state'],'已暂停')
            self.assertEqual((data['completed'],data['total']),(19,86))
            self.assertIn('Invalid evidence IDs',data['reason']);self.assertFalse(data['english'])

    def test_running_major_ignores_stale_failure_and_old_pdfs(self):
        with tempfile.TemporaryDirectory() as d:
            runtime,run,root=self.fixture(d)
            (root/'failure.json').write_text(json.dumps({'status':'PAUSED','reason':'Old failure'}))
            (root/'progress.json').write_text(json.dumps({'stage':'reconstruction','sections_completed':2,'sections_total':7}))
            (run/'major_revision/running.log').write_text('[major-revision] request role=writer\n[major-revision] waiting role=writer elapsed=20s request_limit=600s')
            data=progress(runtime)
            self.assertNotEqual(data['state'],'已暂停');self.assertEqual(data['completed'],2)
            self.assertFalse(data['english']);self.assertIn('20s',data['activity'])

    def test_major_export_end_requires_actual_bilingual_export(self):
        with tempfile.TemporaryDirectory() as d:
            runtime,run,root=self.fixture(d)
            out=root/'delivery/output/output';out.mkdir(parents=True);(out/'review_en.pdf').touch()
            (run/'major_revision/running.log').write_text(json.dumps({'status':'PROVISIONAL_MODEL_PASS','candidate':str(root/'reconstructed.tex'),'exports':{'english':'PASS','chinese':'FAILED'}}))
            data=progress(runtime)
            self.assertNotIn('已完成',data['state']);self.assertTrue(data['english']);self.assertFalse(data['chinese'])

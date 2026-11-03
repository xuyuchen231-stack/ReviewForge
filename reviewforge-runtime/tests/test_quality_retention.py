import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from result_retention import publish_latest
import test_result_retention as retention_fixtures
from study_registry import signature,registry_digest,empty_registry


class QualityRetentionTests(unittest.TestCase):
    def test_locked_build_debris_does_not_relabel_successful_publication_as_failed(self):
        from unittest.mock import patch
        from autonomous_delivery import _compact_publication
        with tempfile.TemporaryDirectory() as d:
            run=Path(d)/'workspace/autonomous_runs/run';out=run/'output';out.mkdir(parents=True)
            with patch('result_retention.publish_latest',return_value={'status':'PUBLISHED'}),patch('result_retention.prune_build_artifacts',side_effect=PermissionError('locked')):
                result=_compact_publication(run,out,{})
            self.assertEqual(result['compact_results']['status'],'PUBLISHED')
            self.assertEqual(result['build_cleanup']['status'],'DEFERRED')

    def test_completed_comparison_is_cached_and_bound_to_exact_pair(self):
        from result_retention import compare_completed_versions,IMPROVEMENT_CHECKS
        with tempfile.TemporaryDirectory() as d:
            run,out,report,old=self.setup(d);calls=[]
            def chat(system,payload,role):
                calls.append(role);return {'decision':'improved','checks':{c:True for c in IMPROVEMENT_CHECKS},'unresolved':[],'reason':'Candidate preserves the scoped findings and improves synthesis and clarity.'}
            review=compare_completed_versions(run,out,report,chat)
            report['supersession_review']=review
            self.assertEqual(compare_completed_versions(run,out,report,chat),review);self.assertEqual(calls,['reviewer'])
            self.assertEqual(review['reference_source_sha256'],old['source_sha256'])
            self.assertEqual(publish_latest(run,report,started=1700004000,finished=1700007600)['status'],'PUBLISHED')

    def setup(self,d):
        run,out,report=retention_fixtures.ResultRetentionTests().setup_run(d)
        previous=publish_latest(run,report,started=1700000000,finished=1700003600)
        policy=run.parent.parent/'retention_policy.json';policy.write_text(json.dumps({'require_improvement_before_replacement':True}))
        for lang in ('en','zh'):
            source=out/('review_'+lang+'.tex');source.write_text('Improved '+lang)
            pdf=out/'output'/('review_'+lang+'.pdf');pdf.write_bytes(('Improved PDF '+lang).encode())
            report['review_'+lang+'_build'].update(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),visual_status='PASS')
        (out/'translation_provenance.json').write_text(json.dumps({'english_sha256':report['review_en_build']['source_sha256'],'chinese_sha256':report['review_zh_build']['source_sha256']}))
        report['publication_acceptance']={'delivery_ready':True};report['scientific_quality']={'status':'PROVISIONAL_MODEL_PASS','manuscript_sha256':signature('Improved en'),'registry_digest':registry_digest(empty_registry(),set()),'unresolved':[],'cross_section_uncovered':[]}
        return run,out,report,previous

    def test_newer_valid_pdf_does_not_replace_old_pair_without_quality_comparison(self):
        with tempfile.TemporaryDirectory() as d:
            run,out,report,old=self.setup(d);archive=Path(old['source_archive']).read_bytes()
            result=publish_latest(run,report)
            self.assertEqual(result['status'],'WAITING_FOR_IMPROVEMENT_REVIEW')
            self.assertEqual(Path(old['source_archive']).read_bytes(),archive)
            self.assertTrue(all((Path(old['directory'])/n).exists() for n in old['files'].values()))

    def test_only_source_bound_improvement_with_current_science_allows_replacement(self):
        from result_retention import IMPROVEMENT_CHECKS
        with tempfile.TemporaryDirectory() as d:
            run,out,report,old=self.setup(d)
            report['supersession_review']={'decision':'improved','reference_source_sha256':old['source_sha256'],'candidate_source_sha256':{lang:report['review_'+lang+'_build']['source_sha256'] for lang in ('en','zh')},'checks':{c:True for c in IMPROVEMENT_CHECKS},'unresolved':[]}
            report['supersession_review']['candidate_source_sha256']['en']='wrong'
            self.assertEqual(publish_latest(run,report)['status'],'WAITING_FOR_IMPROVEMENT_REVIEW')
            report['supersession_review']['candidate_source_sha256']['en']=report['review_en_build']['source_sha256']
            report['scientific_quality']['manuscript_sha256']='stale'
            self.assertEqual(publish_latest(run,report)['status'],'WAITING_FOR_IMPROVEMENT_REVIEW')
            report['scientific_quality']['manuscript_sha256']=signature('Improved en')
            result=publish_latest(run,report,started=1700004000,finished=1700007600)
            self.assertEqual(result['status'],'PUBLISHED')
            self.assertTrue(all(not (Path(old['directory'])/n).exists() for n in old['files'].values()))

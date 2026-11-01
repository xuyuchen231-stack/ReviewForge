import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from result_retention import publish_latest,cleanup_validation


class ResultRetentionTests(unittest.TestCase):
    def setup_run(self,folder):
        run=Path(folder)/'workspace/autonomous_runs/run';out=run/'output';(out/'output').mkdir(parents=True)
        for language in ('en','zh'):
            (out/('review_'+language+'.tex')).write_text('Source '+language,encoding='utf-8')
            (out/'output'/('review_'+language+'.pdf')).write_bytes(b'PDF '+language.encode())
        (out/'translation_provenance.json').write_text(json.dumps({'english_sha256':hashlib.sha256(b'Source en').hexdigest(),'chinese_sha256':hashlib.sha256(b'Source zh').hexdigest()}),encoding='utf-8')
        report={key:{'status':'PASS','layout_status':'PASS','pdf':'output/review_'+language+'.pdf'} for key,language in (('review_en_build','en'),('review_zh_build','zh'))}
        for language in ('en','zh'):
            report['review_'+language+'_build'].update(source_sha256=hashlib.sha256((out/('review_'+language+'.tex')).read_bytes()).hexdigest(),pdf_sha256=hashlib.sha256((out/'output'/('review_'+language+'.pdf')).read_bytes()).hexdigest())
        return run,out,report

    def test_only_latest_fresh_bilingual_pair_is_visible(self):
        with tempfile.TemporaryDirectory() as folder:
            run,out,report=self.setup_run(folder)
            a=publish_latest(run,report,started=1700000000,finished=1700003600)
            self.assertEqual(a['status'],'PUBLISHED')
            b=publish_latest(run,report,started=1700004000,finished=1700007600)
            root=Path(b['directory'])
            self.assertEqual(len(list(root.glob('*.pdf'))),2)
            self.assertTrue(Path(b['source_archive']).exists())
            self.assertIn('2023',next(root.glob('*.pdf')).name)

    def test_stale_or_missing_chinese_does_not_replace_previous_pair(self):
        with tempfile.TemporaryDirectory() as folder:
            run,out,report=self.setup_run(folder)
            a=publish_latest(run,report,started=1700000000,finished=1700003600)
            before={p.name:p.read_bytes() for p in Path(a['directory']).glob('*.pdf')}
            (out/'review_zh.tex').write_text('Changed without translation provenance',encoding='utf-8')
            self.assertEqual(publish_latest(run,report)['status'],'WAITING_FOR_CHINESE')
            self.assertEqual(before,{p.name:p.read_bytes() for p in Path(a['directory']).glob('*.pdf')})

    def test_replaced_pdf_is_rejected_despite_valid_source_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            run,out,report=self.setup_run(folder)
            (out/'output/review_zh.pdf').write_bytes(b'Stale unrelated Chinese PDF')
            self.assertEqual(publish_latest(run,report)['status'],'WAITING_FOR_CHINESE')

    def test_copy_failure_keeps_previous_pair_and_its_source_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            run,out,report=self.setup_run(folder)
            initial=publish_latest(run,report,started=1700000000,finished=1700003600)
            before=Path(initial['source_archive']).read_bytes()
            import shutil
            original=shutil.copyfile
            def copy(source,target):
                if Path(source).name=='review_zh.pdf':raise OSError('No space left')
                return original(source,target)
            with patch('result_retention.shutil.copyfile',side_effect=copy),self.assertRaises(OSError):
                publish_latest(run,report,started=1700004000,finished=1700007600)
            self.assertEqual(Path(initial['source_archive']).read_bytes(),before)
            self.assertEqual(len(list(Path(initial['directory']).glob('*.pdf'))),2)

    def test_source_archive_does_not_collect_private_configuration(self):
        with tempfile.TemporaryDirectory() as folder:
            run,out,report=self.setup_run(folder);project=out/'overleaf';project.mkdir()
            (project/'.env').write_text('PRIVATE',encoding='utf-8');(project/'main.tex').write_text('Paper',encoding='utf-8')
            report['overleaf']={'directory':str(project)}
            result=publish_latest(run,report)
            import zipfile
            with zipfile.ZipFile(result['source_archive']) as archive:self.assertFalse(any('.env' in name for name in archive.namelist()))

    def test_editable_archive_contains_fresh_bilingual_sources_assets_and_times(self):
        with tempfile.TemporaryDirectory() as folder:
            run,out,report=self.setup_run(folder);(out/'figures').mkdir();(out/'figures/plot.pdf').write_bytes(b'Plot asset')
            source=r'\includegraphics{figures/plot.pdf}';(out/'review_en.tex').write_text(source,encoding='utf-8')
            report['review_en_build']['source_sha256']=hashlib.sha256(source.encode()).hexdigest()
            provenance=json.loads((out/'translation_provenance.json').read_text(encoding='utf-8'));provenance['english_sha256']=report['review_en_build']['source_sha256']
            (out/'translation_provenance.json').write_text(json.dumps(provenance),encoding='utf-8')
            result=publish_latest(run,report)
            import zipfile
            with zipfile.ZipFile(result['source_archive']) as archive:
                self.assertEqual(archive.read('overleaf/figures/plot.pdf'),b'Plot asset')
                self.assertEqual(archive.read('overleaf/main.tex').decode(),source)
                self.assertEqual(archive.read('overleaf/review_zh.tex').decode(),'Source zh')
                self.assertIn('finished_at',json.loads(archive.read('run.json')))

    def test_cleanup_only_targets_verified_generated_validation_folders(self):
        with tempfile.TemporaryDirectory() as folder:
            ws=Path(folder);generated=ws/'layout_route_validation';generated.mkdir()
            (generated/'sample.tex').write_text('A recoverable validation source',encoding='utf-8')
            (generated/'page-001.png').write_bytes(b'regenerable image')
            (generated/'experiment.log').write_text('Unique model responses and failures',encoding='utf-8')
            (generated/'results.out').write_text('Unique numerical outputs',encoding='utf-8')
            original=ws/'primary_sources';original.mkdir();(original/'source.pdf').write_bytes(b'original')
            preview=cleanup_validation(ws,execute=False)
            self.assertTrue(generated.exists());self.assertTrue(preview['targets'])
            result=cleanup_validation(ws,execute=True)
            self.assertFalse(generated.exists());self.assertTrue((original/'source.pdf').exists())
            self.assertTrue(Path(result['archive']).exists())
            import zipfile
            with zipfile.ZipFile(result['archive']) as archive:
                manifest=json.loads(archive.read('manifest.json'))
                self.assertIn('object',manifest['layout_route_validation/experiment.log'])
                self.assertIn('object',manifest['layout_route_validation/results.out'])

    def test_validation_assets_referenced_by_retained_manuscript_are_not_deleted(self):
        with tempfile.TemporaryDirectory() as folder:
            ws=Path(folder);target=ws/'layout_route_validation';target.mkdir()
            (target/'figure.pdf').write_bytes(b'Currently referenced asset')
            (ws/'review_en.tex').write_text(r'\includegraphics{layout_route_validation/figure.pdf}',encoding='utf-8')
            result=cleanup_validation(ws,execute=True)
            self.assertTrue((target/'figure.pdf').exists());self.assertEqual(result['targets'],[])

    def test_graphicspath_and_nested_retained_overleaf_roots_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            ws=Path(folder);target=ws/'reference_order_validation';target.mkdir();(target/'plot.pdf').write_bytes(b'Live figure')
            project=ws/'kept_project';project.mkdir()
            (project/'main.tex').write_text(r'\graphicspath{{../reference_order_validation/}}\includegraphics{plot}',encoding='utf-8')
            result=cleanup_validation(ws,execute=True)
            self.assertTrue((target/'plot.pdf').exists());self.assertEqual(result['targets'],[])

    def test_local_style_requirepackage_dependency_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            ws=Path(folder);target=ws/'reference_order_validation';target.mkdir();(target/'helper.sty').write_text('Package',encoding='utf-8')
            (ws/'main.tex').write_text(r'\usepackage{local}',encoding='utf-8')
            (ws/'local.sty').write_text(r'\RequirePackage{reference_order_validation/helper}',encoding='utf-8')
            self.assertEqual(cleanup_validation(ws,execute=True)['targets'],[])
            self.assertTrue((target/'helper.sty').exists())


if __name__=='__main__':unittest.main()

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import time
from editorial_export import finalize_versions
from editorial_refinement import sha


class EditorialExportTests(unittest.TestCase):
    def test_complete_versions_build_separately_without_refinement_or_model_calls(self):
        with tempfile.TemporaryDirectory() as folder:
            run=Path(folder);(run/'output').mkdir();root=run/'editorial/abcd';root.mkdir(parents=True)
            source=r'\documentclass[twocolumn]{article}\begin{document}Result.\end{document}'
            versions={}
            for stage,name in (('clean','full_cleaned.tex'),('condense','refined.tex')):
                p=root/name;p.write_text(source,encoding='utf-8');versions[stage]={'path':str(p),'sha256':sha(source)}
            calls=[]
            def deliver(run,state,report,chat,translate,**kwargs):
                self.assertFalse(kwargs['allow_refinement']);self.assertTrue(kwargs['source_ready']);self.assertFalse(translate)
                calls.append(run);report['publication_acceptance']={'technical_ready':True,'delivery_ready':True}
            with patch('autonomous_delivery.deliver_outputs',side_effect=deliver):
                result=finalize_versions(run,{'versions':versions},time.time()+300,export_reference=True)
            self.assertEqual(len(calls),2);self.assertNotEqual(calls[0],calls[1])
            self.assertEqual(result['exports']['clean']['status'],'READY_FOR_READING')
            self.assertFalse((run/'output/review_en.tex').exists())

    def test_modified_source_hash_is_rejected_before_export(self):
        with tempfile.TemporaryDirectory() as folder:
            run=Path(folder);p=run/'editorial/abcd/full_cleaned.tex';p.parent.mkdir(parents=True);p.write_text('Changed',encoding='utf-8')
            with self.assertRaises(ValueError):finalize_versions(run,{'versions':{'clean':{'path':str(p),'sha256':sha('Original')}}},time.time()+300)

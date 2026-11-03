import tempfile
from pathlib import Path
import unittest
import json
import zipfile
from storage_cleanup import compact_storage


class StorageCleanupTests(unittest.TestCase):
    def test_locked_historical_file_does_not_prevent_removing_other_archived_files(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'workspace').mkdir();old=root/'workspace_backup_20261022_104318';old.mkdir()
            (old/'locked.pdf').write_bytes(b'Open historical PDF');(old/'free.tex').write_bytes(b'Archived source')
            unlink=Path.unlink
            def remove(path,*args,**kwargs):
                if path.name=='locked.pdf':raise PermissionError('Open viewer')
                return unlink(path,*args,**kwargs)
            with patch.object(Path,'unlink',remove):result=compact_storage(root,execute=True)
            self.assertTrue((old/'locked.pdf').exists());self.assertFalse((old/'free.tex').exists());self.assertTrue(result['deferred'])

    def test_extensionless_graphicspath_and_dynamic_preview_references_are_preserved(self):
        for command in (r'\includegraphics{review_en_preview/page-001}',r'\graphicspath{{review_en_preview/}}\includegraphics{page-001}',r'\includegraphics{\selectedPreview}'):
            with self.subTest(command=command),tempfile.TemporaryDirectory() as d:
                root=Path(d);out=root/'workspace/autonomous_runs/run/output';folder=out/'review_en_preview';folder.mkdir(parents=True)
                image=folder/'page-001.png';image.write_bytes(b'Referenced diagram');(out/'review_en.tex').write_text(command)
                compact_storage(root,execute=True);self.assertTrue(image.exists())

    def test_archived_backups_deduplicate_and_active_sources_survive(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);ws=root/'workspace';ws.mkdir()
            for n in ('workspace_backup_20261022_104318','workspace_backup_20261022_113429'):
                old=root/n;old.mkdir();(old/'original.tex').write_bytes(b'Original scientific text')
            active=ws/'autonomous_runs/run/output';active.mkdir(parents=True);(active/'review_en.tex').write_bytes(b'Current text');(active/'review_en.pdf').write_bytes(b'Current PDF');(active/'review_en.xdv').write_bytes(b'Derived build')
            plan=compact_storage(root,execute=False);self.assertFalse(plan['executed']);self.assertTrue((active/'review_en.xdv').exists())
            result=compact_storage(root,execute=True)
            self.assertFalse((root/'workspace_backup_20261022_104318').exists());self.assertFalse((active/'review_en.xdv').exists())
            self.assertTrue((active/'review_en.pdf').exists());self.assertTrue((active/'review_en.tex').exists())
            with zipfile.ZipFile(result['archive']) as z:
                manifest=json.loads(z.read('manifest.json'));self.assertEqual(len(manifest['files']),2)
                self.assertEqual(len([n for n in z.namelist() if n.startswith('objects/')]),1)

    def test_evidence_figures_and_referenced_previews_are_protected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);ws=root/'workspace';out=ws/'autonomous_runs/run/output';preview=out/'review_en_preview';preview.mkdir(parents=True)
            image=preview/'page-001.png';image.write_bytes(b'Figure used by source')
            (out/'review_en.tex').write_text(r'\includegraphics{review_en_preview/page-001.png}')
            evidence=ws/'primary_sources/paper';evidence.mkdir(parents=True);(evidence/'source.pdf').write_bytes(b'Primary paper')
            compact_storage(root,execute=True)
            self.assertTrue(image.exists());self.assertTrue((evidence/'source.pdf').exists())

    def test_cleanup_failure_does_not_remove_unarchived_backup(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'workspace').mkdir();old=root/'workspace_backup_20261022_104318';old.mkdir();(old/'original.tex').write_text('Unique original')
            with patch('storage_cleanup.verify_archive',side_effect=ValueError('CRC mismatch')):
                with self.assertRaises(ValueError):compact_storage(root,execute=True)
            self.assertTrue((old/'original.tex').exists())

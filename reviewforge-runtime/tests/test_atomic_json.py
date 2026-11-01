import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from reviewforge import atomic_json


class AtomicJsonTests(unittest.TestCase):
    def test_temporary_windows_lock_retries_without_losing_old_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'progress.json';target.write_text('{"old":true}')
            original=Path.replace;calls=[]
            def replace(source,destination):
                calls.append(source)
                self.assertLess(len(source.name),25)
                if len(calls)<3:
                    self.assertEqual(json.loads(target.read_text()),{'old':True})
                    raise PermissionError('simulated sharing violation')
                return original(source,destination)
            with patch.object(Path,'replace',replace),patch('reviewforge.time.sleep'):
                atomic_json(target,{'new':True})
            self.assertEqual(len(calls),3)
            self.assertEqual(json.loads(target.read_text()),{'new':True})
            self.assertEqual(list(Path(folder).iterdir()),[target])

    def test_permanent_denial_preserves_old_file_and_cleans_temporary(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'progress.json';target.write_text('{"old":true}')
            with patch.object(Path,'replace',side_effect=PermissionError('denied')),patch('reviewforge.time.sleep'):
                with self.assertRaises(PermissionError):atomic_json(target,{'new':True})
            self.assertEqual(json.loads(target.read_text()),{'old':True})
            self.assertEqual(list(Path(folder).iterdir()),[target])

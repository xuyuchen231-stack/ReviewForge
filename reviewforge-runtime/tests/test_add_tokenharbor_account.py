import tempfile
import unittest
from pathlib import Path
from add_tokenharbor_account import save_account


class AddAccountTests(unittest.TestCase):
    def test_appends_without_duplicate_or_other_setting_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'credentials.env'
            path.write_text('RF_MODEL=model:free\n RF_API_KEYS = old\n')
            key = 'local-test-key-iPto'
            order = save_account(path, key, ['old'], 'iPto')
            self.assertEqual(order, ['old', key])
            self.assertEqual(save_account(path, key, order, 'iPto'), order)
            self.assertIn('RF_MODEL=model:free', path.read_text())
            self.assertEqual(path.read_text().count('RF_API_KEYS='), 1)

    def test_invalid_input_does_not_touch_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'credentials.env'
            path.write_text('original')
            for key in ['short-iPto', 'long-key-wrong-suffix', 'long-key\ninjection-iPto']:
                with self.assertRaises(ValueError):
                    save_account(path, key, [], 'iPto')
                self.assertEqual(path.read_text(), 'original')

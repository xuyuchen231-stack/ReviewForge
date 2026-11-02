import tempfile
from pathlib import Path
import unittest


class PriorityAccountTests(unittest.TestCase):
    def test_new_key_is_first_preserves_other_settings_and_records_available_window(self):
        from prioritize_account import apply_priority
        from account_cycles import WeeklyAccounts,WEEK
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);env=folder/'.env';env.write_text('RF_API_KEYS=first,second\nRF_MODEL=test:free\n')
            ledger=WeeklyAccounts(folder/'cycles.json')
            apply_priority(env,'new-uWQo',['first','second'],'https://tokenharbor.ai/v1',ledger,23,now=1000000)
            self.assertIn('RF_API_KEYS=new-uWQo,first,second',env.read_text())
            self.assertIn('RF_MODEL=test:free',env.read_text())
            row=ledger.entry('https://tokenharbor.ai/v1','new-uWQo')
            self.assertEqual(row['window_started_at']+WEEK,1000000+23*3600)
            self.assertFalse(ledger.blocked('https://tokenharbor.ai/v1','new-uWQo',1000000))
            self.assertIsNone(row.get('first_success_observed_at'))

    def test_existing_exhaustion_not_silently_cleared_and_duplicate_key_removed(self):
        from prioritize_account import apply_priority
        from account_cycles import WeeklyAccounts
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);env=folder/'.env';env.write_text('RF_API_KEYS=first,target\n');ledger=WeeklyAccounts(folder/'cycles.json')
            ledger.exhausted('https://tokenharbor.ai/v1','target',1000)
            apply_priority(env,'target',['first','target'],'https://tokenharbor.ai/v1',ledger,23,now=1000)
            self.assertIn('RF_API_KEYS=target,first',env.read_text())
            self.assertTrue(ledger.blocked('https://tokenharbor.ai/v1','target',1000))

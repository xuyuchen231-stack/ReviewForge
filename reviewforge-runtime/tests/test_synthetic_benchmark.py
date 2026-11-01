import unittest
try:
    import numpy as np
    from synthetic_benchmark import run_benchmark
except ImportError:
    np = None


@unittest.skipIf(np is None, 'Optional synthetic benchmark requires numpy')
class SyntheticBenchmarkTests(unittest.TestCase):
    def test_repeatable_split_and_no_test_fit(self):
        first = run_benchmark()
        second = run_benchmark(test_shift=5.0)
        self.assertEqual(first['frozen_models'], second['frozen_models'])
        self.assertEqual(first['selection'], second['selection'])
        self.assertTrue(np.isfinite([r['rmse'] for r in first['metrics']]).all())
        self.assertTrue(all(r['volume'] > 0 and r['biomass'] >= 0 and r['substrate'] >= 0 for r in first['trajectories']))
        self.assertFalse(first['experimental_data'])


if __name__ == '__main__':
    unittest.main()

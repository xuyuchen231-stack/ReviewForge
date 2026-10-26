import unittest
from delivery_checks import layout_diagnostics

class LayoutLocationTests(unittest.TestCase):
 def test_warning_locations_are_reported_without_hiding_small_overflows(self):
  log='Overfull \\hbox (8.25pt too wide) in paragraph at lines 12--14\nOverfull \\vbox (2.0pt too high) detected at line 19'
  report=layout_diagnostics(log);self.assertEqual(report['status'],'FAILED');self.assertEqual(report['overflow_details'][0]['start_line'],12);self.assertEqual(report['overflow_details'][0]['amount_pt'],8.25);self.assertEqual(report['overflow_details'][1]['start_line'],19);self.assertEqual(report['severe_overflow_count'],1)

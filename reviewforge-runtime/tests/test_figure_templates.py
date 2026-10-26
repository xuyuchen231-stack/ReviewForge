import tempfile,unittest
from pathlib import Path

class FigureTemplateTests(unittest.TestCase):
 def test_missing_renderer_does_not_leave_old_pdf_as_new_figure(self):
  from figure_templates import render
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as t:
   output=Path(t);(output/'figure.pdf').write_bytes(b'old unrelated figure')
   with patch('figure_templates.shutil.which',return_value=None):report=render({'kind':'topology','nodes':[{'id':'a','label':'A'}],'edges':[]},output)
   self.assertEqual(report['status'],'UNAVAILABLE');self.assertFalse((output/'figure.pdf').exists());self.assertNotIn('figure.pdf',report['outputs']);self.assertTrue(list((output/'stale_outputs').rglob('figure.pdf')))
 def test_topology_escapes_labels_and_uses_layout_engine(self):
  from figure_templates import topology_dot
  spec={'nodes':[{'id':'a','label':'A "quoted" input'},{'id':'b','label':'Evidence'}],'edges':[{'source':'a','target':'b'}]}
  dot=topology_dot(spec);self.assertIn('splines=ortho',dot);self.assertIn('n0 -> n1',dot);self.assertNotIn('pos=',dot);self.assertIn('\\"quoted\\"',dot)
  spec['edges'][0]['target']='missing'
  with self.assertRaises(ValueError):topology_dot(spec)
 def test_quantitative_data_requires_sources_and_comparable_conditions(self):
  from figure_templates import validate_quantitative
  spec={'unit':'seconds','comparison_group':'same protocol','items':[{'label':'A','value':2,'source_ids':['S1']}]}
  validate_quantitative(spec)
  for item in [{'label':'A','value':float('nan'),'source_ids':['S1']},{'label':'A','value':2,'source_ids':[]},{'label':'B','value':3,'source_ids':['S2'],'comparison_group':'another task'}]:
   with self.assertRaises(ValueError):validate_quantitative({**spec,'items':[item]})

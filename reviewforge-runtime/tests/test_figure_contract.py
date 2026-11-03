import unittest,tempfile
from pathlib import Path
from figure_contract import audit_vector
class ContractTests(unittest.TestCase):
 def make(self,folder,width=252,height=193,font=7):
  import fitz
  doc=fitz.open();p=doc.new_page(width=width,height=height);p.insert_text((15,30),'Scientific label',fontsize=font);path=Path(folder)/'test.pdf';doc.save(path);doc.close();return path
 def test_final_inclusion_scaling_detects_tiny_labels(self):
  with tempfile.TemporaryDirectory() as d:
   result=audit_vector(self.make(d,width=504,font=8))
   self.assertEqual(result['technical_status'],'NEEDS_ATTENTION');self.assertLess(result['smallest_printed_font_pt'],5)
 def test_area_limit_and_visual_pending_are_independent(self):
  with tempfile.TemporaryDirectory() as d:
   result=audit_vector(self.make(d,height=400))
   self.assertIn('Graphic exceeds one eighth of page area',result['issues']);self.assertEqual(result['visual_status'],'PENDING')
 def test_compact_original_passes_and_saves_editable_vector(self):
  from compact_publication import render_compact
  with tempfile.TemporaryDirectory() as d:
   render_compact(d);self.assertEqual(audit_vector(Path(d)/'compact_synthesis.pdf')['technical_status'],'PASS');self.assertTrue((Path(d)/'compact_synthesis.svg').exists())

 def test_authored_plan_renders_at_native_single_column_size(self):
  from publication_figures import render_concept
  spec={'id':'interfaces','source_keys':['A'],'panels':[{'title':title,'note':note,'nodes':[{'text':'Balance','kind':'mechanism'},{'text':'Rate','kind':'learning'}]} for title,note in [('Parameter','Parameters vary.'),('Rate','Rates vary.'),('Residual','Dynamics vary.'),('Observation','Readout varies.')]]}
  with tempfile.TemporaryDirectory() as d:
   report=render_concept(spec,d)
   self.assertEqual(report['final_size']['technical_status'],'PASS')
   self.assertEqual(report['spec'],spec)
   self.assertFalse((Path(d)/'interfaces.png').exists())
 def test_workflow_overloaded_labels_block_export(self):
  from publication_figures import render_workflow
  spec={'id':'overload','source_keys':['A'],'nodes':['Long label '*20]*8}
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):render_workflow(spec,d)

 def test_small_ordinary_label_on_same_baseline_is_not_a_math_script(self):
  import fitz
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'mixed.pdf'
   with fitz.open() as doc:
    page=doc.new_page(width=252,height=193)
    page.insert_text((15,30),'Rate',fontsize=7)
    page.insert_text((32,30),'small label',fontsize=5)
    doc.save(path)
   self.assertEqual(audit_vector(path)['technical_status'],'NEEDS_ATTENTION')

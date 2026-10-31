import tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
class DeliveryTests(unittest.TestCase):
 def test_export_recovers_wide_two_column_math_without_changing_math(self):
  from autonomous_delivery import deliver_outputs
  from manuscript_integrity import citekeys
  import json
  with tempfile.TemporaryDirectory() as t:
   run=Path(t);out=run/'output';out.mkdir();source='\\documentclass[twocolumn]{article}\n\\begin{document}\n\\begin{equation}a=b\\end{equation}\\cite{A}\n\\end{document}'
   p=out/'review_en.tex';p.write_text(source,encoding='utf-8');calls=[]
   def build(*args,**kwargs):
    calls.append(p.read_text(encoding='utf-8'))
    if len(calls)==1:return {'status':'PASS','layout_status':'FAILED','layout':{'overflows':['Overfull \\hbox (100pt too wide)'],'unresolved':[],'missing_glyphs':[],'overflow_details':[{'kind':'hbox','start_line':3,'amount_pt':100}]}}
    if len(calls)==2:return {'status':'PASS','layout_status':'FAILED','layout':{'overflows':['Overfull \\vbox (1.8pt too high)'],'unresolved':[],'missing_glyphs':[]}}
    return {'status':'PASS','layout_status':'PASS','layout':{'overflows':[],'unresolved':[],'missing_glyphs':[]}}
   report={'accepted_units':1}
   with patch('reviewforge_v4.compile_tex',side_effect=build):deliver_outputs(run,{'deadline':time.time()+1800},report,lambda *a:None,False)
   self.assertEqual(len(calls),3);self.assertNotIn(r'\onecolumn',calls[1]);self.assertIn(r'\begin{strip}',calls[1]);self.assertIn(r'\addtolength{\textheight}{3pt}',calls[2])
   self.assertIn(r'\begin{equation}a=b\end{equation}',calls[2]);self.assertEqual(citekeys(source),citekeys(calls[2]))
   self.assertEqual(report['review_en_build']['layout_status'],'PASS');self.assertEqual((run/'reports/layout_original_english.tex').read_text(encoding='utf-8'),source)
 def test_unresolved_citations_do_not_trigger_formatting_recovery(self):
  from autonomous_delivery import deliver_outputs
  with tempfile.TemporaryDirectory() as t:
   run=Path(t);out=run/'output';out.mkdir();(out/'review_en.tex').write_text(r'\documentclass[twocolumn]{article}\begin{document}Text\end{document}')
   with patch('reviewforge_v4.compile_tex',return_value={'status':'PASS','layout_status':'FAILED','layout':{'overflows':['Overfull \\hbox'],'unresolved':['Citation undefined'],'missing_glyphs':[]}}) as build:
    deliver_outputs(run,{'deadline':time.time()+1800},{'accepted_units':1},lambda *a:None,False)
   self.assertEqual(build.call_count,1)
 def test_stale_chinese_is_quarantined_and_english_build_precedes_translation(self):
  from autonomous_delivery import deliver_outputs
  with tempfile.TemporaryDirectory() as t:
   run=Path(t);out=run/'output';out.mkdir();(out/'review_en.tex').write_text('current English');(out/'review_zh.tex').write_text('stale Chinese');(out/'output').mkdir();(out/'output/review_zh.pdf').write_bytes(b'stale')
   state={'deadline':time.time()+1800};report={'accepted_units':1};order=[]
   def build(w,name,**kw):order.append(name);return {'status':'PASS','pdf':'output/'+name+'.pdf'}
   def translate(*a,**kw):
    order.append('translation');self.assertLess(kw['deadline'],state['deadline']);raise RuntimeError('provider failed')
   with patch('reviewforge_v4.compile_tex',side_effect=build),patch('reviewforge_v4.generate_chinese_body',side_effect=translate):
    deliver_outputs(run,state,report,lambda *a:None,True)
   self.assertEqual(order,['review_en','translation']);self.assertFalse((out/'review_zh.tex').exists());self.assertFalse((out/'output/review_zh.pdf').exists());self.assertEqual(report['translation'],'incomplete')
 def test_no_accepted_units_uses_no_models_or_compiler(self):
  from autonomous_delivery import deliver_outputs
  with tempfile.TemporaryDirectory() as t:
   run=Path(t);(run/'output').mkdir();state={'deadline':time.time()+1800};report={'accepted_units':0}
   with patch('reviewforge_v4.compile_tex') as build:
    deliver_outputs(run,state,report,lambda *a:self.fail('No API expected'),True)
   build.assert_not_called();self.assertEqual(report['translation'],'not_run_no_accepted_units')

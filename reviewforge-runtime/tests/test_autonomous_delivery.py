import tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
class DeliveryTests(unittest.TestCase):
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

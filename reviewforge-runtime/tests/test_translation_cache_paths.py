import json,tempfile,unittest
from pathlib import Path


class TranslationPathTests(unittest.TestCase):
 def test_author_list_is_not_mistaken_for_untranslated_prose(self):
  from translation_pipeline import validate_unit,DOCUMENT_AUTHOR_NAMES
  source=' study of von Stosch, Hamelink, and Oliveira supplies a more direct operational challenge than an unspecified held-out fit. Its development programme comprised '
  candidate='von Stosch、Hamelink 与 Oliveira 的研究提供了比未明确界定的留出拟合更直接的操作性挑战。其开发方案包括'
  token=DOCUMENT_AUTHOR_NAMES.set(frozenset(('von stosch','hamelink','oliveira')))
  try:self.assertTrue(validate_unit(source,candidate)[0])
  finally:DOCUMENT_AUTHOR_NAMES.reset(token)
 def test_capitalized_scientific_list_is_not_an_author_exception(self):
  from translation_pipeline import validate_unit
  self.assertFalse(validate_unit('Growth, Yield, and Productivity are measured.', '本文测量 Growth, Yield, and Productivity。')[0])
 def test_author_names_are_read_from_bibliographic_initials(self):
  from translation_pipeline import document_author_names
  text=r'\bibitem{A} von Stosch, M.; Hamelink, J. M.; Oliveira, R.. Study title.'
  self.assertTrue({'von stosch','hamelink','oliveira'}<=document_author_names(text))
 def test_author_exception_does_not_allow_untranslated_scientific_phrase(self):
  from translation_pipeline import validate_unit
  self.assertFalse(validate_unit('The hybrid model predicts production.', '该 hybrid model predicts 产量。')[0])
 def test_valid_batch_preserves_markers_and_uses_one_request(self):
  from translation_pipeline import translate_plain_slots
  from unittest.mock import patch
  import os
  with tempfile.TemporaryDirectory() as t,patch.dict(os.environ,{'RF_TRANSLATION_BATCH_UNITS':'1'}):
   calls=[]
   def ask(text,feedback):calls.append(text);return '生长 RFPROTECT000001TOKEN 增加。'
   result=translate_plain_slots('Growth RFPROTECT000001TOKEN increased.',ask,Path(t),'',{'attempts':0},None)
   self.assertIn('RFPROTECT000001TOKEN',result);self.assertEqual(len(calls),1)
 def test_bad_batch_falls_back_without_losing_protected_markers(self):
  from translation_pipeline import translate_plain_slots
  from unittest.mock import patch
  import os
  with tempfile.TemporaryDirectory() as t,patch.dict(os.environ,{'RF_TRANSLATION_BATCH_UNITS':'1'}):
   def ask(text,feedback):return '错误的标记输出' if 'RFPROTECT' in text else '有效中文。'
   result=translate_plain_slots('Growth RFPROTECT000001TOKEN increased.',ask,Path(t),'',{'attempts':0},None)
   self.assertIn('RFPROTECT000001TOKEN',result)
 def test_deep_windows_cache_can_be_written_with_full_hash_retained(self):
  from translation_pipeline import translation_cache_path
  from reviewforge import atomic_json
  with tempfile.TemporaryDirectory() as t:
   folder=Path(t)/('nested_'*18)/'plain_slots';folder.mkdir(parents=True)
   digest='c'*64;path=translation_cache_path(folder,digest)
   self.assertLess(len(str(path)),260)
   atomic_json(path,{'source_sha256':digest,'text':'中文'})
   self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['source_sha256'],digest)
 def test_short_name_keeps_full_binding_and_rejects_collision(self):
  from translation_pipeline import translation_cache_path
  with tempfile.TemporaryDirectory() as t:
   folder=Path(t);digest='a'*64
   path=translation_cache_path(folder,digest)
   self.assertLess(len(path.name),40)
   path.write_text(json.dumps({'source_sha256':'b'*64,'text':'other'}))
   with self.assertRaises(ValueError):translation_cache_path(folder,digest)
 def test_valid_legacy_cache_remains_reusable(self):
  from translation_pipeline import translation_cache_path
  with tempfile.TemporaryDirectory() as t:
   folder=Path(t);digest='a'*64;p=folder/(digest+'.json')
   p.write_text(json.dumps({'source_sha256':digest,'text':'old'}))
   self.assertEqual(translation_cache_path(folder,digest),p)

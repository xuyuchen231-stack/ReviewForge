import tempfile,unittest
from pathlib import Path
class ScientificNameTranslationTests(unittest.TestCase):
 def test_taxa_already_in_manuscript_keep_tex_spacing_and_spelling(self):
  from translation_pipeline import mask_tex
  for name in (r'P.\ pastoris',r'S.\ cerevisiae','Pseudomonas putida','Enterobacter'):
   with self.subTest(name=name):
    masked,saved=mask_tex('Observed '+name+' data.');self.assertIn(name,saved);self.assertNotIn(name,masked)
 def test_latin_organism_name_is_preserved_without_false_translation_failure(self):
  from translation_pipeline import mask_tex,validate_unit,TOKEN
  source=r'Observed \textit{Pichia} data.';masked,saved=mask_tex(source)
  self.assertNotIn('Pichia',masked);self.assertIn('Pichia',saved)
  candidate=masked.replace('Observed','Observed').replace(' data.',' data.')
  self.assertFalse(validate_unit(masked,candidate)[0])
  candidate=masked.replace('Observed','观察到的').replace(' data.','数据。')
  self.assertTrue(validate_unit(masked,candidate)[0])
 def test_ordinary_italic_english_cannot_be_hidden_as_a_species_name(self):
  from translation_pipeline import mask_tex,validate_unit
  masked,_=mask_tex(r'\textit{Validation protocol} remains unclear.')
  self.assertIn('Validation protocol',masked);self.assertFalse(validate_unit(masked,masked)[0])

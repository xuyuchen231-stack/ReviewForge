import unittest
import tempfile
from pathlib import Path
from translation_pipeline import mask_tex, TOKEN


class TranslationAnchorTests(unittest.TestCase):
    def test_inline_code_citation_identifier_is_not_translatable(self):
        source=r'\texttt{Geremia20254ccb72}'
        masked,saved=mask_tex(source)
        self.assertFalse(TOKEN.sub('',masked).strip())
        self.assertIn(source,saved)

    def test_plain_author_et_al_is_translated_without_changing_citation_markup(self):
        from translation_pipeline import translate_fragment
        with tempfile.TemporaryDirectory() as folder:
            d=Path(folder)/'units';d.mkdir()
            result=translate_fragment(r'Unlike Lawrence et al.\cite{L2020}',lambda *a:'\u4e0e Lawrence et al. \u4e0d\u540c',d,'',[])
        self.assertIn('Lawrence \u7b49',result)
        self.assertIn(r'\cite{L2020}',result)

    def test_strain_fragments_and_uppercase_partition_codes_are_not_untranslated_prose(self):
        from translation_pipeline import validate_unit
        self.assertTrue(validate_unit('The GS','GS')[0])
        self.assertTrue(validate_unit(' GPo','GPo')[0])
        self.assertTrue(validate_unit('the V-I/V-E split','V-I/V-E\u5212\u5206')[0])
        self.assertFalse(validate_unit('The model','model')[0])
        self.assertFalse(validate_unit('the operating point','the operating point')[0])

    def test_plain_slots_never_send_formulas_citations_or_tokens_to_model(self):
        from translation_pipeline import translate_fragment
        source=r'Growth $x=1$ follows \cite{Smith2020} evidence.'
        seen=[]
        def ask(text,feedback):
            seen.append(text)
            self.assertNotIn('RFPROTECT',text)
            self.assertNotIn('Smith2020',text)
            self.assertNotIn('x=1',text)
            return {'Growth':'\u751f\u957f','follows':'\u4f9d\u636e','evidence.':'\u8bc1\u636e\u3002'}[text.strip()]
        with tempfile.TemporaryDirectory() as folder:
            d=Path(folder)/'units';d.mkdir()
            result=translate_fragment(source,ask,d,'',[])
        self.assertIn('$x=1$',result)
        self.assertIn(r'\cite{Smith2020}',result)
        self.assertEqual(len(seen),3)

    def test_failed_unit_does_not_block_later_units_or_publish_partial_text(self):
        from translation_pipeline import translate_fragment, TranslationError
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder)/'units';directory.mkdir()
            reports=[]
            def ask(text, feedback):
                return text if 'First' in text else '\u7b2c\u4e8c\u6bb5\u8bd1\u6587\u3002'
            with self.assertRaises(TranslationError):
                translate_fragment('First paragraph.\n\nSecond paragraph.\n\n',ask,directory,'',reports)
            self.assertEqual([r['status'] for r in reports],['FAILED','PASS'])
            self.assertEqual(len(list(directory.glob('*.json'))),1)

    def test_ralstonia_names_are_immutable_scientific_identifiers(self):
        for name in ('R. eutropha', 'Ralstonia eutropha', 'Cupriavidus necator', 'C. necator', 'C. autoethanogenum', 'X.~dendrorhous', 'Xanthophyllomyces dendrorhous'):
            with self.subTest(name=name):
                masked, saved = mask_tex(name)
                self.assertFalse(TOKEN.sub('', masked).strip())
                self.assertIn(name, saved)

    def test_internal_hyperlink_destination_is_not_translatable_prose(self):
        source = r'\hypertarget{rf-wide-0001-start}{}'
        masked, saved = mask_tex(source)
        self.assertFalse(TOKEN.sub('', masked).strip())
        restored = TOKEN.sub(lambda m: saved[int(m.group()[9:15])], masked)
        self.assertEqual(restored, source)

    def test_link_caption_remains_translatable(self):
        masked, _ = mask_tex(r'\hypertarget{anchor}{Scientific caption}')
        self.assertIn('Scientific caption', masked)
        self.assertNotIn('anchor', masked)

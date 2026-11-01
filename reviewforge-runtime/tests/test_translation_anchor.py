import unittest
import tempfile
from pathlib import Path
from translation_pipeline import mask_tex, TOKEN


class TranslationAnchorTests(unittest.TestCase):
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

import unittest
from translation_pipeline import mask_tex, TOKEN


class TranslationAnchorTests(unittest.TestCase):
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

import unittest
from publication_export import prefer_multiline_displays


class MultilineExportTests(unittest.TestCase):
    def test_exporter_strip_and_anchor_are_recovered_without_blank_math_paragraphs(self):
        source=r'\begin{strip}\small\hypertarget{rf-wide-0001-start}{}\['+'\n'+r'a=long(x,y),\qquad b=long(x,y)\label{eq:a}'+'\n\n'+r'\]\hypertarget{rf-wide-0001-end}{}\end{strip}'
        result,count=prefer_multiline_displays(source,minimum=20)
        self.assertEqual(count,1)
        self.assertNotIn(r'\begin{strip}',result)
        self.assertNotIn(r'\small',result)
        self.assertNotIn('\n\n',result)
        self.assertIn(r'\hypertarget{rf-wide-0001-end}{}',result)

    def test_long_equation_uses_multiple_lines_with_one_original_label(self):
        source=r'\begin{equation}a=long(x,y),\qquad b=long(x,y),\qquad c=long(x,y)\label{eq:a}\end{equation}'
        result,count=prefer_multiline_displays(source,minimum=20)
        self.assertEqual(count,1)
        self.assertIn(r'\begin{aligned}',result)
        self.assertNotIn(r'\begin{strip}',result)
        self.assertEqual(result.count(r'\label{eq:a}'),1)
        self.assertIn(r'\end{aligned}\label{eq:a}',result)

    def test_nested_plus_is_not_split(self):
        source=r'\[x=\frac{a+b}{c+d}\]'
        result,count=prefer_multiline_displays(source,minimum=1)
        self.assertEqual((result,count),(source,0))

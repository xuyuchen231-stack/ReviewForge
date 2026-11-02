import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch


class CompactPublicationTests(unittest.TestCase):
    def test_ambiguous_author_reference_is_not_redirected_when_other_figure_merges(self):
        from compact_publication import compact_figures
        source=r'Experiment in Figure~\ref{fig:model}.\begin{figure}\includegraphics{experimental-results.pdf}\label{fig:model}\end{figure}\begin{figure}\includegraphics{figures/scale_single.pdf}\label{fig:rf-scale_single}\end{figure}'
        with tempfile.TemporaryDirectory() as folder,patch('compact_publication.render_compact'):
            result,_=compact_figures(source,Path(folder))
        self.assertIn(r'Experiment in Figure~\ref{fig:model}',result)

    def test_author_aligned_system_keeps_separate_equations(self):
        from compact_publication import column_math
        source=r'\[\begin{aligned}x&=1\\y&=2\end{aligned}\]'
        self.assertEqual(column_math(source)[0],source)

    def test_generic_model_label_is_not_ownership_proof(self):
        from compact_publication import compact_figures
        source=r'\begin{figure}\includegraphics{experimental-results.pdf}\label{fig:model}\end{figure}'
        with tempfile.TemporaryDirectory() as folder,patch('compact_publication.render_compact') as render:
            result,report=compact_figures(source,Path(folder))
        self.assertEqual(result,source)
        self.assertEqual(report['status'],'NEEDS_REVIEW')
        render.assert_not_called()

    def test_single_column_policy_does_not_promote_figures_to_starred(self):
        from publication_export import prepare_two_column_export
        source=r'\documentclass[twocolumn]{article}\begin{document}\begin{figure}\includegraphics[width=\columnwidth]{a.pdf}\caption{A.}\end{figure}\end{document}'
        self.assertNotIn(r'\begin{figure*}',prepare_two_column_export(source))

    def test_redundant_known_figures_merge_without_dropping_unknown_figures(self):
        from compact_publication import compact_figures
        source=r'\begin{document}See Figure~\ref{fig:rf-framework_abcd}.\begin{figure*}\includegraphics{figures/framework_abcd.pdf}\caption{Old}\label{fig:rf-framework_abcd}\end{figure*}\begin{figure}\caption{Data}\label{fig:author-data}\end{figure}\end{document}'
        with tempfile.TemporaryDirectory() as folder,patch('compact_publication.render_compact'):
            result,report=compact_figures(source,Path(folder))
        self.assertIn(r'\ref{fig:rf-compact}',result)
        self.assertIn(r'\label{fig:author-data}',result)
        self.assertNotIn(r'\label{fig:rf-framework_abcd}',result)
        self.assertEqual(report['removed_redundant'],1)

    def test_graphic_contract_is_below_one_eighth_page(self):
        from compact_publication import FIGURE_MM
        self.assertLessEqual(FIGURE_MM[0]*FIGURE_MM[1]/(210*297),1/8)

    def test_column_math_removes_old_full_width_wrappers_without_shrinking(self):
        from compact_publication import column_math
        source=r'\begin{strip}\hypertarget{rf-wide-0001-start}{}'+'\n'+r'\small'+'\n'+r'\begin{equation}a=long(x,y)+long(x,y)+long(x,y)+long(x,y)+long(x,y)+long(x,y)+long(x,y)\label{eq:a}\end{equation}\end{strip}'
        result,_=column_math(source)
        self.assertNotIn(r'\begin{strip}',result)
        self.assertNotIn(r'\small',result)
        self.assertIn(r'\label{eq:a}',result)

    def test_compact_figure_is_not_duplicated_on_resume(self):
        from compact_publication import compact_figures
        source=r'\begin{document}\begin{figure}\caption{New}\label{fig:rf-compact}\end{figure}\begin{figure}\includegraphics{figures/framework_abcd.pdf}\caption{Old}\label{fig:rf-framework_abcd}\end{figure}\end{document}'
        with tempfile.TemporaryDirectory() as folder,patch('compact_publication.render_compact'):
            result,_=compact_figures(source,Path(folder))
        self.assertEqual(result.count(r'\label{fig:rf-compact}'),1)

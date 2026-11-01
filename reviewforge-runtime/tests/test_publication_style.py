import unittest
from publication_style import prose_lists,sorted_citation_groups
from publication_export import prepare_two_column_export
from manuscript_integrity import citekeys


class PublicationStyleTests(unittest.TestCase):
    def test_prose_lists_drop_markers_without_losing_scientific_content(self):
        source=r'\begin{itemize}\item First result $x+y$ \cite{A}.\item Second result 12.\end{itemize}'
        result,report=prose_lists(source)
        self.assertNotIn(r'\item',result);self.assertNotIn('itemize',result)
        self.assertIn('First result $x+y$',result);self.assertIn('Second result 12.',result)
        self.assertEqual(citekeys(source),citekeys(result));self.assertEqual(report['converted_lists'],1)

    def test_referenced_numbered_items_are_not_silently_broken(self):
        source=r'\begin{enumerate}\item\label{step:a}A.\end{enumerate}See \ref{step:a}.'
        result,report=prose_lists(source)
        self.assertEqual(result,source);self.assertTrue(report['retained_referenced_lists'])

    def test_equation_label_inside_list_does_not_prevent_prose_conversion(self):
        source=r'\begin{itemize}\item A balance follows.\begin{equation}x=1\label{eq:a}\end{equation}\end{itemize}See \eqref{eq:a}.'
        result,report=prose_lists(source)
        self.assertEqual(report['status'],'PASS');self.assertNotIn('itemize',result)
        self.assertIn(r'\label{eq:a}',result);self.assertIn(r'\eqref{eq:a}',result)

    def test_single_column_figure_is_not_automatically_promoted(self):
        source=r'\documentclass[twocolumn]{article}\begin{document}\begin{figure}[t]'+'\n% RF_SINGLE_COLUMN_FIGURE\n'+r'\includegraphics[width=\columnwidth]{plot.pdf}\end{figure}\end{document}'
        result=prepare_two_column_export(source)
        self.assertIn(r'\begin{figure}',result);self.assertNotIn(r'\begin{figure*}',result)
        self.assertIn(r'width=\columnwidth',result)

    def test_multi_citation_keys_follow_bibliography_order(self):
        source=r'\citep{B,A,B}\begin{thebibliography}{9}\bibitem{A}A.\bibitem{B}B.\end{thebibliography}'
        result=sorted_citation_groups(source)
        self.assertIn(r'\citep{A,B}',result);self.assertEqual(citekeys(source),citekeys(result))

    def test_textual_author_order_is_preserved_for_respectively_claims(self):
        source=r'\citet{B,A} reported 12 and 15 respectively.\begin{thebibliography}{9}\bibitem{A}A.\bibitem{B}B.\end{thebibliography}'
        self.assertEqual(sorted_citation_groups(source),source)


if __name__=='__main__':unittest.main()

import unittest
class BibliographyDeliveryTests(unittest.TestCase):
 def test_doi_date_does_not_override_explicit_journal_year(self):
  from bibliography_delivery import prepare_inline_bibliography
  source=r'\begin{thebibliography}{99}\bibitem{study}Raissi, M.; Perdikaris, P.. Article. \textit{Journal} 2019, 378. DOI: \url{10.1016/j.jcp.2018.10.045}.\end{thebibliography}'
  self.assertIn(r'\bibitem[Raissi et al.(2019)]{study}',prepare_inline_bibliography(source,{})[0])
 def test_ambiguous_manual_dates_are_not_guessed_from_a_title(self):
  from bibliography_delivery import prepare_inline_bibliography
  source=r'\begin{thebibliography}{99}\bibitem{old}Smith, J. Longitudinal measurements in 2019. Journal of Tests (2023).\end{thebibliography}'
  self.assertEqual(prepare_inline_bibliography(source,{})[0],source)
  source=source.replace('in 2019','over time')
  self.assertIn(r'\bibitem[Smith(2023)]{old}',prepare_inline_bibliography(source,{})[0])
 def test_registered_metadata_and_existing_manual_authors_support_textual_citations(self):
  from bibliography_delivery import prepare_inline_bibliography
  source=r'\citet{new,old}\begin{thebibliography}{99}\bibitem{old}Pinto, J.; Mestre, M.. Title. 2022.\end{thebibliography}'
  catalogue={'new':{'metadata_status':'REGISTERED_METADATA','authors':['Alex Moore','Jie Zhang'],'title':'Study','year':2025,'doi':'10.1/test','venue':'Journal'}}
  text,added,unresolved=prepare_inline_bibliography(source,catalogue)
  self.assertIn(r'\bibitem[Alex Moore et al.(2025)]{new}',text)
  self.assertIn(r'\bibitem[Pinto et al.(2022)]{old}',text)
  self.assertEqual(added,['new']);self.assertEqual(unresolved,[])
  self.assertEqual(prepare_inline_bibliography(text,catalogue)[0],text)
 def test_unverified_metadata_cannot_fill_a_missing_reference(self):
  from bibliography_delivery import prepare_inline_bibliography
  text,added,missing=prepare_inline_bibliography(r'\cite{unknown}\begin{thebibliography}{99}\end{thebibliography}',{'unknown':{'title':'Unverified','year':2025,'doi':'10.1/no'}})
  self.assertEqual(added,[]);self.assertEqual(missing,['unknown']);self.assertNotIn(r'\bibitem',text)
 def test_author_undefined_warning_blocks_layout_pass(self):
  from delivery_checks import layout_diagnostics
  self.assertEqual(layout_diagnostics("Package natbib Warning: Author undefined for citation`old' on page 1.")['status'],'FAILED')

 def test_numeric_bibliography_follows_first_active_citation_and_preserves_uncited(self):
  import re
  from bibliography_delivery import prepare_inline_bibliography
  source = r"\usepackage[numbers]{natbib}" + "\n% ignored \cite{A}\n" + r"First \citep[see][p. 2]{C,B}. Then \citet{A,C}.\begin{thebibliography}{99}\bibitem{A} Alpha.\bibitem{B} Beta.\bibitem{C} Gamma.\bibitem{D} Uncited.\end{thebibliography}"
  result=prepare_inline_bibliography(source,{})[0]
  self.assertEqual(re.findall(r'\\bibitem(?:\[[^]]*\])?\{([^}]+)\}',result),['C','B','A','D'])
  self.assertEqual(prepare_inline_bibliography(result,{})[0],result)
 def test_explicit_author_year_style_retains_publisher_order(self):
  from bibliography_delivery import prepare_inline_bibliography
  source=r"\usepackage[authoryear]{natbib}\cite{B,A}\begin{thebibliography}{99}\bibitem{A} Alpha.\bibitem{B} Beta.\end{thebibliography}"
  self.assertEqual(prepare_inline_bibliography(source,{})[0],source)

 def test_default_natbib_author_year_is_not_reordered(self):
  from bibliography_delivery import prepare_inline_bibliography
  source=r"\usepackage{natbib}\cite{B,A}\begin{thebibliography}{99}\bibitem[Alpha(2020)]{A} Alpha.\bibitem[Beta(2021)]{B} Beta.\end{thebibliography}"
  self.assertEqual(prepare_inline_bibliography(source,{})[0],source)

 def test_commented_citation_does_not_create_unresolved_reference(self):
  from bibliography_delivery import prepare_inline_bibliography
  source="% \\cite{ghost}\n"+r"\begin{thebibliography}{99}\end{thebibliography}"
  self.assertEqual(prepare_inline_bibliography(source,{})[2],[])

 def test_commented_bibitem_cannot_satisfy_an_active_citation(self):
  from bibliography_delivery import prepare_inline_bibliography
  source=r"\cite{B}\begin{thebibliography}{99}"+"\n% \\bibitem{B} Commented only.\n"+r"\bibitem{A} Active.\end{thebibliography}"
  catalogue={'B':{'metadata_status':'REGISTERED_METADATA','authors':['Smith'],'title':'Actual','year':2020,'doi':'10.1/test'}}
  text,added,missing=prepare_inline_bibliography(source,catalogue)
  self.assertEqual(added,['B']);self.assertEqual(missing,[])
  self.assertIn('% '+r"\bibitem{B} Commented only.",text)

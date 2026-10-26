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

import tempfile,unittest
from pathlib import Path

class PublicationExportTests(unittest.TestCase):
 def test_same_registered_doi_uses_first_cited_key_and_one_entry(self):
  from publication_export import canonicalize_references
  tex=r"\citep{B,A}\cite{A}\begin{thebibliography}{9}\bibitem{A}Alpha. DOI: \url{https://doi.org/10.1234/same}.\bibitem{B}Same article. DOI: \url{https://doi.org/10.1234/SAME}.\bibitem{C}Another. DOI: \url{https://doi.org/10.1234/other}.\end{thebibliography}"
  result,aliases=canonicalize_references(tex)
  self.assertEqual(aliases,{'A':'B'});self.assertIn(r"\citep{B}",result);self.assertNotIn(r"\bibitem{A}",result);self.assertIn(r"\bibitem{C}",result)
  self.assertEqual(canonicalize_references(result)[0],result)
 def test_no_doi_is_not_identity_evidence(self):
  from publication_export import canonicalize_references
  tex=r"\cite{B,A}\begin{thebibliography}{9}\bibitem{A}Title.\bibitem{B}Title.\end{thebibliography}"
  self.assertEqual(canonicalize_references(tex),(tex,{}))
 def test_pdf_link_order_honors_columns_and_spanning_float(self):
  from publication_export import ordered_citation_links
  links=[{'key':'right','x':320,'y':100,'x1':330,'y1':110},{'key':'left_low','x':60,'y':180,'x1':70,'y1':190},{'key':'left_top','x':60,'y':100,'x1':70,'y1':110}]
  self.assertEqual(ordered_citation_links(links,600,[]),['left_top','left_low','right'])
  links.append({'key':'wide','x':400,'y':30,'x1':410,'y1':40})
  self.assertEqual(ordered_citation_links(links,600,[(20,60)]),['wide','left_top','left_low','right'])

 def test_wide_math_reflow_preserves_formula_source(self):
  from publication_export import prepare_two_column_export,reflow_wide_displays
  math=r"\begin{equation}a=b+c\label{eq:a}\end{equation}"
  tex=r"\documentclass[twocolumn]{article}"+"\n"+r"\begin{document}"+"\n"+math+"\n"+r"\end{document}"
  result,count=reflow_wide_displays(tex,{'overflow_details':[{'kind':'hbox','start_line':3}]})
  self.assertEqual(count,1);self.assertIn(math,result);self.assertIn(r"\begin{strip}",result);self.assertNotIn(r"\onecolumn",result)
  self.assertEqual(reflow_wide_displays(result,{'overflow_details':[]})[0],result)
 def test_two_column_export_uses_wide_floats_not_single_column_body(self):
  from publication_export import prepare_two_column_export
  source=r"\documentclass[twocolumn]{article}\begin{document}"+"\n"+r"\onecolumn"+"\n"+r"\begin{table}[t]\begin{tabularx}{\columnwidth}{XX}A&B\end{tabularx}\end{table}\end{document}"
  result=prepare_two_column_export(source,force=True)
  self.assertNotIn(r"\onecolumn",result);self.assertIn(r"\begin{table*}",result);self.assertIn(r"\textwidth",result)

 def test_commented_or_ambiguous_doi_does_not_merge_distinct_works(self):
  from publication_export import canonicalize_references
  tex=r"\cite{A,B}\begin{thebibliography}{9}\bibitem{A}Work A. DOI: 10.1234/a"+"\n"+r"\bibitem{B}Work B."+"\n% old DOI: 10.1234/a\nActual DOI: 10.1234/b\n"+r"\end{thebibliography}"
  self.assertEqual(canonicalize_references(tex)[1],{})
  tex=tex.replace('% old DOI:', 'Alternative DOI:')
  self.assertEqual(canonicalize_references(tex)[1],{})
 def test_budget_exhaustion_does_not_write_tex_or_rebuild_pdf(self):
  import time
  from unittest.mock import patch
  from publication_export import reconcile_pdf_references
  tex=r"\cite{A,B}\begin{thebibliography}{9}\bibitem{A}A.\bibitem{B}B.\end{thebibliography}"
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);(p/'review_en.tex').write_text(tex);(p/'paper.pdf').write_bytes(b'valid prior PDF')
   with patch('publication_export.pdf_citation_order',return_value=['B','A']):
    result,build,report=reconcile_pdf_references(p,tex,{'status':'PASS','pdf':'paper.pdf'},lambda:self.fail('Budget must stop rebuild'),deadline=time.time()-1)
   self.assertEqual((p/'review_en.tex').read_text(),tex);self.assertEqual((p/'paper.pdf').read_bytes(),b'valid prior PDF');self.assertEqual(report['status'],'UNVERIFIED')
 def test_failed_recompile_restores_successful_source_pdf_pair(self):
  from unittest.mock import patch
  from publication_export import reconcile_pdf_references
  tex=r"\cite{A,B}\begin{thebibliography}{9}\bibitem{A}A.\bibitem{B}B.\end{thebibliography}"
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);(p/'review_en.tex').write_text(tex);(p/'paper.pdf').write_bytes(b'valid prior PDF')
   def fail():
    (p/'paper.pdf').unlink();return {'status':'FAILED'}
   with patch('publication_export.pdf_citation_order',return_value=['B','A']):
    _,build,report=reconcile_pdf_references(p,tex,{'status':'PASS','pdf':'paper.pdf'},fail)
   self.assertEqual((p/'review_en.tex').read_text(),tex);self.assertEqual((p/'paper.pdf').read_bytes(),b'valid prior PDF');self.assertEqual(build['status'],'PASS');self.assertNotEqual(report['status'],'PASS')

 def test_missing_wide_marker_pair_is_not_silent(self):
  from publication_export import validate_wide_markers,ReferenceCoverageError
  with self.assertRaises(ReferenceCoverageError):validate_wide_markers({'rf-wide-0000-start':{'page':0,'to':[10,20]}},['rf-wide-0000-start','rf-wide-0000-end'])
  with self.assertRaises(ReferenceCoverageError):validate_wide_markers({'rf-wide-0000-start':{'page':1,'to':[10,80]},'rf-wide-0000-end':{'page':0,'to':[10,90]}},[])
 def test_incremental_wide_marker_insertion_is_idempotent(self):
  from publication_export import mark_wide_material
  source=r"\documentclass{article}\begin{document}\begin{figure*}A\end{figure*}\end{document}"
  first=mark_wide_material(source);self.assertEqual(first,mark_wide_material(first))
  second=mark_wide_material(first.replace(r"\end{document}",r"\begin{strip}B\end{strip}\end{document}"))
  self.assertEqual(second.count('rf-wide-0000-start'),1);self.assertEqual(second.count('rf-wide-0001-start'),1)

 def test_compressed_citation_range_includes_invisible_middle_links(self):
  from publication_export import numeric_citation_records
  text='[1–4,6]';chars=[{'c':c,'bbox':[10+i*5,20,15+i*5,30]} for i,c in enumerate(text)]
  raw={'blocks':[{'lines':[{'spans':[{'chars':chars}]}]}]}
  links=[{'key':'K1','x':15,'x1':20,'y':20,'y1':30},{'key':'K4','x':25,'x1':30,'y':20,'y1':30},{'key':'K6','x':35,'x1':40,'y':20,'y1':30}]
  self.assertEqual([r['key'] for r in numeric_citation_records(raw,links,{i:'K'+str(i) for i in range(1,7)})],['K1','K2','K3','K4','K6'])

 def test_overleaf_package_contains_only_main_and_referenced_assets(self):
  import zipfile
  from publication_export import make_overleaf_project
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);(p/'review_en.tex').write_text(r"\documentclass{article}\begin{document}Text.\end{document}");(p/'.env').write_text('SECRET=not packaged');(p/'private.tex').write_text('unrelated draft')
   report=make_overleaf_project(p)
   with zipfile.ZipFile(report['zip']) as z:self.assertEqual(set(z.namelist()),{'main.tex','README.txt'})
   self.assertEqual(Path(report['main']).read_bytes(),(p/'review_en.tex').read_bytes())

 def test_numeric_group_keeps_earlier_author_only_citation(self):
  from publication_export import numeric_citation_records
  chars=[{'c':c,'bbox':[200+i*5,200,205+i*5,210]} for i,c in enumerate('[1]')]
  raw={'blocks':[{'lines':[{'spans':[{'chars':chars}]}]}]}
  links=[{'key':'B','x':10,'x1':20,'y':10,'y1':20},{'key':'B','x':205,'x1':210,'y':200,'y1':210}]
  self.assertTrue(any(r['x']==10 and r['y']==10 for r in numeric_citation_records(raw,links,{1:'B'})))
 def test_failed_recompile_restores_aux_numbering(self):
  from unittest.mock import patch
  from publication_export import reconcile_pdf_references
  tex=r"\cite{A,B}\begin{thebibliography}{9}\bibitem{A}A.\bibitem{B}B.\end{thebibliography}"
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);(p/'review_en.tex').write_text(tex);(p/'paper.pdf').write_bytes(b'PDF');(p/'paper.aux').write_bytes(b'old numbering')
   def fail():(p/'paper.aux').write_bytes(b'changed numbering');return {'status':'FAILED'}
   with patch('publication_export.pdf_citation_order',return_value=['B','A']):reconcile_pdf_references(p,tex,{'status':'PASS','pdf':'paper.pdf'},fail)
   self.assertEqual((p/'paper.aux').read_bytes(),b'old numbering')


 def test_portable_greek_text_does_not_rewrite_math_or_urls(self):
  from publication_export import prepare_two_column_export
  beta='\u03b2';formula='$\u03b1+\u03bc$';url=r'\url{https://example.test/'+beta+'}';label=r'\label{'+beta+'}'
  tex=r'\documentclass[twocolumn]{article}\begin{document}'+' '+beta+' '+formula+' '+url+label+r'\end{document}'
  result=prepare_two_column_export(tex)
  self.assertIn(r'\ensuremath{\beta}',result);self.assertIn(formula,result);self.assertIn(url,result);self.assertIn(label,result)

 def test_long_inline_math_scan_finishes_in_bounded_subprocess(self):
  import subprocess,sys
  code="from publication_export import portable_text_symbols; s='$'+('\\\\command '*10000)+chr(946); portable_text_symbols(s); print('ok')"
  result=subprocess.run([sys.executable,'-c',code],capture_output=True,timeout=5)
  self.assertEqual(result.returncode,0,result.stderr);self.assertIn(b'ok',result.stdout)

 def test_referenced_secret_file_is_not_packaged(self):
  from publication_export import make_overleaf_project
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);(p/'review_en.tex').write_text(r"\documentclass{article}\begin{document}\input{.env}\end{document}");(p/'.env').write_text('SECRET=do not package')
   with self.assertRaises(ValueError):make_overleaf_project(p)
   self.assertFalse((p/'overleaf_project/.env').exists())

import tempfile, unittest, json
from pathlib import Path
from unittest.mock import patch
from reviewforge_v4 import extract_sections,protect_tex,doi_normalize,cite_keys,make_bib,audit,compile_tex,collect_literature,GateError,run_v4

TEX=r'''\documentclass[twocolumn]{article}
\begin{document}
\section{Background}
Text \cite{Smith2000}.\begin{figure}figure\label{fig:a}\end{figure}
\section{Methods}
Text \cite{Jones2001}.
\bibliography{references}
\end{document}
'''
class TestV4(unittest.TestCase):
 def test_sections_do_not_own_bibliography(self):
  ss=extract_sections(TEX);self.assertEqual(len(ss),2)
  self.assertNotIn('\\bibliography',TEX[ss[-1][1]:ss[-1][2]])
 def test_preservation_gate(self):
  self.assertTrue(protect_tex(r'\begin{figure}Hi\label{fig:a}\end{figure}',r'\begin{figure}Bye\label{fig:a}\end{figure}')[0])
  self.assertFalse(protect_tex(r'\begin{figure}Hi\label{fig:a}\end{figure}','Bye')[0])
 def test_doi(self):self.assertEqual(doi_normalize('https://doi.org/10.9999/AB'), '10.9999/ab')
 def test_keys(self):self.assertEqual(cite_keys(r'\citep{a, b} \citet{c}'),{'a','b','c'})
 def test_bib_and_audit_gate(self):
  with tempfile.TemporaryDirectory() as tmp:
   w=Path(tmp);p=[{'key':'K1','doi':'10.1234/test','title':'A','authors':['B Test'],'year':2020,'venue':'Journal'}]
   make_bib(w,p);self.assertIn('@article{K1', (w/'references.bib').read_text())
   (w/'literature.json').write_text(json.dumps(p));(w/'review_en.tex').write_text(r'\cite{K1}')
   (w/'review_zh.tex').write_text(r'\cite{K1}');self.assertTrue(audit(w,1)['minimum_pass'])
   self.assertFalse(audit(w,60)['minimum_pass'])
 def test_compile_unavailable(self):
  with tempfile.TemporaryDirectory() as tmp:
   (Path(tmp)/'test.tex').write_text(TEX)
   with patch('reviewforge_v4.shutil.which',return_value=None):self.assertEqual(compile_tex(Path(tmp),'test')['status'],'UNAVAILABLE')
 def test_missing_source(self):
  with tempfile.TemporaryDirectory() as tmp:
   with self.assertRaises(GateError):run_v4(tmp,skip_search=True)

if __name__=='__main__':unittest.main()

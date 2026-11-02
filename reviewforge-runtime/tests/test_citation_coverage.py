import json
from pathlib import Path
import tempfile
import hashlib
import unittest
from citation_coverage import intro_citation_audit,apply_verified_patches


class CitationCoverageTests(unittest.TestCase):
    def test_caption_and_commented_citations_do_not_cover_introductory_prose(self):
        text=r'\section{Introduction}'+'\n% '+r'\cite{A}'+'\n'+r'\begin{figure}\caption{Diagram \cite{B}}\end{figure}'+' Background statement.'*150+r'\cite{C}'
        audit=intro_citation_audit(text)
        self.assertEqual(audit['first_citekeys'],['C'])
        self.assertEqual(audit['status'],'REVIEW')

    def test_late_first_citation_is_flagged_even_when_number_order_is_valid(self):
        text=r'\section{Introduction}'+' Background statement.'*150+r'\cite{A}\section{Methods}'
        self.assertEqual(intro_citation_audit(text)['status'],'REVIEW')

    def test_abstract_does_not_count_as_uncited_introduction(self):
        text='Abstract words. '*500+r'\section{Introduction}A supported balance \cite{A}.'
        self.assertEqual(intro_citation_audit(text)['status'],'PASS')

    def test_repair_requires_matching_source_and_inspectable_quote(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'primary_sources').mkdir();f=root/'primary_sources/source.txt';f.write_text('Balances account for feed inlets and outlets.')
            digest=hashlib.sha256(f.read_bytes()).hexdigest()
            (f.parent/'source.json').write_text(json.dumps({'doi':'10.0000/test','sha256':digest}))
            plan={'patches':[{'before':'A balance couples flows.','after':r'Balances account for feed flows \citep{A}.','citekey':'A','source_text_file':'primary_sources/source.txt','source_text_sha256':digest,'identity_file':'primary_sources/source.txt','identity_sha256':digest,'quote':'Balances account for feed inlets and outlets.'}]}
            text=r'\section{Introduction}A balance couples flows.\section{Next}\begin{thebibliography}{9}\bibitem{A}Source DOI 10.0000/test\end{thebibliography}'
            repaired,report=apply_verified_patches(text,plan,root)
            self.assertIn(r'\citep{A}',repaired)
            self.assertEqual(report['applied'],1)
            self.assertEqual(apply_verified_patches(repaired,plan,root)[0],repaired)
            original=plan['patches'][0].copy()
            with self.assertRaises(ValueError):apply_verified_patches(text.replace('10.0000/test','10.0000/test-suffix'),plan,root)
            other=f.parent/'other';other.mkdir();(other/'source.txt').write_bytes(f.read_bytes())
            plan['patches'][0]['source_text_file']='primary_sources/other/source.txt'
            with self.assertRaises(ValueError):apply_verified_patches(text,plan,root)
            plan['patches'][0]=original.copy()
            plan['patches'][0]['quote']=''
            with self.assertRaises(ValueError):apply_verified_patches(text,plan,root)
            plan['patches'][0]=original.copy();plan['patches'][0]['after']=r'Claim \citep{A,Invented}.'
            with self.assertRaises(ValueError):apply_verified_patches(text,plan,root)
            plan['patches'][0]=original.copy()
            plan['patches'][0]['quote']='Invented quote'
            with self.assertRaises(ValueError):apply_verified_patches(text,plan,root)

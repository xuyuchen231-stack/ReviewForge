"""Offline regression tests for ReviewForge quality and provenance gates."""
import tempfile
import unittest
from pathlib import Path
from evidence_gate import provenance_audit,evidence_gate
from review_planner import inspect_draft
from quality_audit import audit_depth

class QualityTests(unittest.TestCase):
    def test_arbitrary_chapter_count(self):
        tex='\n'.join('\\section{Chapter %s}\n\\subsection{Detail}\nText.'%i for i in range(1,8))
        self.assertEqual(inspect_draft(tex)['section_count'],7)

    def test_detect_short_section(self):
        result=audit_depth('\\subsection{Method}\nOne short explanation.')
        self.assertEqual(result['flagged_count'],1)

    def test_missing_citation_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            before=r'The model was validated \cite{Smith2020}.'
            after='The model was validated.'
            passed,_,report=evidence_gate(before,after,root)
            self.assertFalse(passed)
            self.assertEqual(report['existing_citations_removed'],['Smith2020'])

    def test_unregistered_citation_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            passed,_,report=evidence_gate('Old text.',r'New text \cite{Fake2025}.',root)
            self.assertFalse(passed)
            self.assertEqual(report['new_citations_unregistered'],['Fake2025'])

    def test_registered_new_citation_still_needs_verification(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root,'sources.bib').write_text('@article{Known2020, title={Example}}')
            passed,_,report=evidence_gate('Old text.',r'New text \cite{Known2020}.',root)
            self.assertFalse(passed)
            self.assertTrue(report['needs_evidence_review'])

    def test_novel_numbers_require_review(self):
        with tempfile.TemporaryDirectory() as root:
            passed,_,report=evidence_gate('Yield improved.', 'Yield improved by 47%.',root)
            self.assertFalse(passed)
            self.assertTrue(report['new_numeric_expressions'])

    def test_ledger_cannot_certify_entire_manuscript(self):
        from source_evidence import evaluate_ledger
        manuscript=r'This result is supported \\cite{Known2020}.'
        ledger={'entries':[{'claim':'This result is supported','citekey':'Known2020','source_id':'paper1',
                'locator':'p.4','excerpt':'Original text','verification_status':'expert_verified'}]}
        report=evaluate_ledger(manuscript,ledger)
        self.assertFalse(report['complete_expert_verification'])

    def test_prepare_weak_draft_without_fixed_chapters(self):
        from quality_pipeline import prepare
        with tempfile.TemporaryDirectory() as root:
            ws=Path(root)
            tex=r'\documentclass{article}'+'\n'+r'\begin{document}'+'\n'
            tex+='\n'.join('\\section{Part %d}\nShort text.'%i for i in range(1,5))
            tex+='\n'+r'\end{document}'
            (ws/'original.tex').write_text(tex,encoding='utf-8')
            report=prepare(ws)
            self.assertEqual(report['sections'],4)
            self.assertTrue((ws/'reports'/'review_plan_input.json').exists())
            self.assertFalse((ws/'review_en.tex').exists())

    def test_chinese_subsection_length_is_counted(self):
        from quality_audit import audit_depth
        text=r'\subsection{方法原理}'+'\n'+('这是一个用于描述研究方法、证据比较以及模型适用边界的中文段落。'*20)
        report=audit_depth(text)
        self.assertGreater(report['subsections'][0]['cjk_characters'],100)

    def test_manuscript_inventory_is_topic_independent(self):
        from quality_audit import audit_manuscript
        text=r'\section{Introduction}'+'\n'+('A substantive paragraph. '*30)+'\n'+r'\section{Methods}'+'\n'+('A second substantive paragraph. '*30)
        report=audit_manuscript(text)
        self.assertEqual(report['heading_count'],2)

if __name__=='__main__':
    unittest.main()

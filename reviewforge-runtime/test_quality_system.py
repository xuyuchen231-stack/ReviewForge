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

if __name__=='__main__':
    unittest.main()

"""Regression tests for offline quality gates; run with unittest."""
import json
import tempfile
import unittest
from pathlib import Path
from research_quality import evaluate, synthesis_analysis


class QualityGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name)
        (self.ws / "review_en.tex").write_text(r"\\cite{A2020}", encoding="utf-8")
        (self.ws / "review_zh.tex").write_text(r"\\cite{A2020}", encoding="utf-8")
        (self.ws / "literature.json").write_text(json.dumps([
            {"key": "A2020", "doi": "10.1/abc", "title": "Example", "year": 2020}
        ]), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_evidence_blocks_readiness(self):
        result = evaluate(self.ws, minimum=1)
        self.assertFalse(result["submission_ready"])
        self.assertEqual(result["unverified_cited_keys"], ["A2020"])

    def test_forged_status_without_source_anchor_is_rejected(self):
        row = {"citekey": "A2020", "doi": "10.1/abc", "title": "Example",
               "authors": ["A"], "year": 2020, "full_text_access": "local_text",
               "evidence_location": "p. 2", "supported_claim": "Test",
               "verification_status": "PRIMARY_TEXT_VERIFIED",
               "supporting_excerpt": "Unverifiable invented quote of sufficient length"}
        (self.ws / "evidence_ledger.json").write_text(json.dumps([row]), encoding="utf-8")
        result = evaluate(self.ws, minimum=1)
        self.assertEqual(result["unverified_cited_keys"], ["A2020"])

    def test_real_local_anchor_is_recorded_but_not_human_certified(self):
        source = self.ws / "sources"
        source.mkdir()
        quote = "An exact passage from the locally inspected primary source."
        (source / "paper.txt").write_text("Introduction. " + quote, encoding="utf-8")
        row = {"citekey": "A2020", "doi": "10.1/abc", "title": "Example",
               "authors": ["A"], "year": 2020, "full_text_access": "local_text",
               "evidence_location": "p. 2", "supported_claim": "Test",
               "verification_status": "PRIMARY_TEXT_VERIFIED",
               "source_file": "sources/paper.txt", "supporting_excerpt": quote}
        (self.ws / "evidence_ledger.json").write_text(json.dumps([row]), encoding="utf-8")
        result = evaluate(self.ws, minimum=1)
        self.assertEqual(result["unverified_cited_keys"], [])
        self.assertFalse(result["scientific_quality_human_verified"])
        self.assertFalse(result["submission_ready"])

    def test_synthesis_missing_axes_are_reported(self):
        result = synthesis_analysis([{"citekey": "A2020", "unseen_operating_conditions": "not tested"}])
        self.assertEqual(result["evidence_gaps"]["unseen_operating_conditions"]["unresolved_count"], 1)


if __name__ == "__main__":
    unittest.main()

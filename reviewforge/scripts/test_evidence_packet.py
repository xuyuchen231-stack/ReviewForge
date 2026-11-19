import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from evidence_packet import build_packet

class EvidencePacketTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.text = "原文\r\nResult holds only under oxygen limitation."
        raw = self.text.encode("utf-8")
        (self.base / "source.txt").write_bytes(raw)
        self.plan = {"question": "When does it hold?", "sources": [{
            "id": "study-1", "path": "source.txt", "sha256": hashlib.sha256(raw).hexdigest(),
            "text_access": "partial-text", "figure_access": "not-requested",
            "spans": [{"start": 0, "end": len(self.text), "locator": "p. 3, Results"}]}]}

    def test_exact_unicode_and_crlf(self):
        result = json.loads(build_packet(self.plan, self.base))
        self.assertEqual(result["sources"][0]["spans"][0]["text"], self.text)
        self.assertEqual(result["scientific_approval"], "not-assessed")

    def test_changed_source_rejected(self):
        (self.base / "source.txt").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "hash"):
            build_packet(self.plan, self.base)

    def test_budget_never_truncates(self):
        with self.assertRaisesRegex(ValueError, "budget"):
            build_packet(self.plan, self.base, 100)

    def test_invalid_range_and_missing_locator(self):
        span = self.plan["sources"][0]["spans"][0]
        for field, value in [("end", 9999), ("start", True), ("locator", "")]:
            old = span[field]
            span[field] = value
            with self.assertRaises(ValueError):
                build_packet(self.plan, self.base)
            span[field] = old

    def test_missing_status_and_duplicate_identity(self):
        src = self.plan["sources"][0]
        src["figure_access"] = "unknown"
        with self.assertRaises(ValueError):
            build_packet(self.plan, self.base)
        src["figure_access"] = "unavailable"
        self.plan["sources"].append(dict(src))
        with self.assertRaisesRegex(ValueError, "unique"):
            build_packet(self.plan, self.base)

if __name__ == "__main__":
    unittest.main()

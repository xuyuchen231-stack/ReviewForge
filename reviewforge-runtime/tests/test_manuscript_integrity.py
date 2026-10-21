"""Offline checks: citations, manual bibliography, LaTeX structure and source protection."""
import tempfile
import unittest
from pathlib import Path
from manuscript_integrity import analyze, bibkeys, citekeys, tex_integrity


class IntegrityTests(unittest.TestCase):
    def test_citations_with_multiple_keys(self):
        text = r"\cite{Alpha2020,Beta2021} \parencite[see][p. 4]{Gamma2022}"
        self.assertEqual(citekeys(text), {"Alpha2020", "Beta2021", "Gamma2022"})

    def test_bibtex_and_manual(self):
        self.assertEqual(bibkeys("@article{Alpha2020,\n title={X}\n}\n"), {"Alpha2020"})
        self.assertEqual(bibkeys(r"\bibitem{Beta2021} Some author"), {"Beta2021"})

    def test_latex_integrity(self):
        self.assertEqual(tex_integrity(r"\begin{figure}\label{fig:a}\end{figure} \ref{fig:a}"), [])
        issues = tex_integrity(r"\begin{figure}\label{fig:a}\label{fig:a}\ref{fig:missing}")
        self.assertTrue(any(x["kind"] == "duplicate_labels" for x in issues))
        self.assertTrue(any(x["kind"] == "unclosed_environment" for x in issues))

    def test_manual_bibliography_does_not_need_external_bib(self):
        with tempfile.TemporaryDirectory() as root:
            ws = Path(root)
            source = r"\cite{Alpha2020}" + "\n" + r"\begin{thebibliography}{9}\bibitem{Alpha2020} X\end{thebibliography}"
            (ws / "review_en.tex").write_text(source, encoding="utf-8")
            (ws / "review_zh.tex").write_text(source, encoding="utf-8")
            result = analyze(ws)
            self.assertEqual(result["languages"]["en"]["missing_bibliography_keys"], [])
            self.assertEqual(result["languages"]["en"]["bibliography_mode"], "manual")


if __name__ == "__main__":
    unittest.main()

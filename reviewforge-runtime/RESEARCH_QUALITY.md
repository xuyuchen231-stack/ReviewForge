# Research quality gates (offline)

These commands never call an LLM and do not spend API tokens:

```powershell
py .\reviewforge_v4.py quality-init
py .\reviewforge_v4.py quality
```

The first command creates **example files only**, not fake verified evidence. Copy the example files to `workspace/evidence_ledger.json`, `workspace/study_matrix.json`, and `workspace/independent_review.json`, then replace every example with primary-source observations. Do not rename an example file to live data without replacing the placeholders.

`quality` writes `workspace/reports/quality_gate.json` and `workspace/reports/major_issues.md`. The `run` command also writes these at the final compile stage.

Evidence entries require citekey, DOI, title, authors, year, full-text access, evidence location, supported claim and verification status. `PRIMARY_TEXT_VERIFIED` is only a *recorded assertion*: the program cannot independently authenticate quotations or semantic entailment. All unmatched citekeys remain unresolved.

Each study comparison should record model structure, learned component, mechanistic constraints, measured signals, validation design, unseen feeding/induction policy tests, cross-batch validation, baseline comparisons, failure modes, and evidence location. Use explicit `not reported` when a primary source does not provide a field. Do not invent measurements.

The independent-review file is an explicit approval record, not an AI-generated rubber stamp. Quality reports conservatively block submission readiness while key evidence, PDF builds, study comparison, or independent review are missing. Journal submission and expert scientific approval remain human decisions.

**Existing manuscript protection:** these commands do not rewrite the existing manuscript, references, or images.

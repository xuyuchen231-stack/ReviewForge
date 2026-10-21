# ReviewForge engineering overhaul

## Design contract

The runtime separates **bibliographic identity**, **inspectable primary-text anchors**, **scientific interpretation**, **manuscript integrity**, **PDF build**, and **human publication approval**. Passing one gate does not imply passing another.

### Offline, no-token commands

```powershell
git pull origin main
py -m compileall -q .
py -m unittest discover -s tests -p "test_*.py" -v
py .\reviewforge_v4.py preflight
py .\reviewforge_v4.py audit
py .\reviewforge_v4.py quality-init
py .\reviewforge_v4.py quality
py .\reviewforge_v4.py compile
```

Do not execute `run` or `resume` just to compile or audit: those actions can invoke paid language-model APIs.

### Safety and reproducibility

- The bibliography merge preserves existing entries. Metadata discovery must not replace the author's `references.bib`.
- Manual `thebibliography` entries are recognized by the integrity checker.
- Build reports always identify success/failure, diagnostic log tails, source hash and whether a PDF was actually produced.
- Old output PDFs are deleted before recompilation; a stale PDF cannot count as a successful new build.
- AI section edits are rejected if they remove labels, figure/table commands, citations, or change protected mathematical/TikZ environments.
- Evidence statuses are not trusted without a matching local source-text excerpt and consistent catalogue metadata.
- Source-text excerpt presence is **not** semantic entailment; scientific support still needs expert checking.
- The quality gate emits `reports/quality_gate.json`, `reports/major_issues.md`, `reports/synthesis_gaps.json`, and `reports/manuscript_integrity.json`.
- Quality results are intentionally conservative and do not assert Q1-journal suitability.

### Research synthesis standard

For each primary study, compare: learning location (rate, parameter, state or output correction); conserved mass/stoichiometry; measured signals and initialisation; truly unseen feeding/induction conditions; held-out batch/reactor validation; mechanistic/recalibration baselines; solver failures; limits of extrapolation. `not reported` must remain distinct from `not tested`.

### Known limits

The runtime does not yet prove that a local excerpt semantically entails a claim; cannot autonomously obtain paywalled full texts; and does not substitute for a qualified peer reviewer. Windows MiKTeX and XeLaTeX still need a machine-specific end-to-end build test. Existing nine-hour outputs remain untouched by offline audits.

### Testing

`.github/workflows/reviewforge-quality.yml` attempts syntax and unit tests on pushes. The workflow status must be inspected before claiming a green CI result. If the hosted runner fails to start, use the local offline commands above and attach the output.

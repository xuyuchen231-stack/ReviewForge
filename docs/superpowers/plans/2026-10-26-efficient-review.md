# Efficient evidence-backed review implementation plan

> **For agentic workers:** Use executing-plans to implement these tasks with tests and verification.

**Goal:** Apply the user's supplied efficiency/depth/layout/figure suggestions while preserving source provenance and scientific gates.

**Architecture:** Separate inexpensive structured preparation from writing and review. Extract small bounded source batches, persist validated cards independently, and repair only failed cards. Preserve source math and use export-only layout adaptation plus diagnostics. Figure rendering consumes structured data with provenance and uses deterministic layouts.

**Tech stack:** Python 3.10/3.12, standard library runtime, optional Matplotlib/Graphviz figure export, XeLaTeX.

**Spec:** User attachment 573851f6-2d71-4df2-8fd3-1be0c4280289; accepted with exceptions below.

## Constraints and exceptions

- Keep primary full-text/excerpt evidence; do not replace it with title/abstract-only guesses.
- Use immutable passage IDs; do not fuzzy-match equations, punctuation or unsupported claims.
- Batch size and byte limits bound context/output; never force 12 full-text papers into one request.
- Two scientific visits by default; unresolved scientific issues stay unresolved. Minor style alone does not force rejection when every substantive criterion passes.
- Paragraph functions and calibrated length guidance support depth; word counts never prove scientific quality or force sparse/bridge padding.
- Do not rewrite/scale original mathematics automatically; retain readable export adaptation, compiler warnings and visual-review status. Zero severe warnings is not a 100% visual guarantee.
- Figures need explicit source data/provenance; never invent measurements, guarantee a journal style, or auto-run generated code.

## Tasks

- [x] Verify stage budgets, preparation non-thinking route, fallback time reservation, scheduling fairness and GPT path on actual manuscript snapshots.
- [x] Add bounded batch extraction and exact full-request disk cache, preserve old valid per-unit cards, save successful cards before retrying failed ones. Test source-ID isolation, changed questions/axes/spans, partial responses and interrupted resume.
- [x] Add evidence-calibrated paragraph/depth contracts, two-visit default and report stagnation rather than repeating unsupported rewrites. Keep English plain LaTeX and translation separate.
- [x] Extend layout diagnostics with magnitude and line locations without weakening existing overflow/missing-reference checks. Keep formulas immutable.
- [x] Add deterministic figure templates for explicit topology and provenance-backed quantitative data, with output manifests and optional dependencies. Verify a real example visually.
- [x] Run both Python test suites, independent read-only review and bounded real workflow; update local configuration only after route checks, preserve current progress and originals, commit/push.

## Verification evidence and limits

Three real source packets were extracted in one call in 4.9 seconds, with source-specific IDs materialized and each card validated. The same request resumed with three cache hits and zero API calls. This is a case measurement, not a promised speed multiplier or percentage saving.

In an isolated full-manuscript snapshot, selected unit004 completed planning, source preparation, GPT-6.1 Sol writing (98.7 seconds), GPT-6 Astra review (39.9 seconds), and produced approximately 1031 English words. After recovering the final coherence batch under the preparation/coherence routing policy, all ten complete/overview batches finished and English compile/layout passed. The other 57 units remained not selected. No full production nine-hour job was launched by this check.

The first diagnostic exhausted its short coherence budget after nine completed groups; the report correctly recorded a failure, preserved those groups and resumed without repeating them. An actual author-label failure traced to a DOI containing 2018 alongside the explicit journal year2019; identifier numbers are now excluded from manual date ambiguity checks, while genuinely conflicting bibliographic years remain unresolved.

Matplotlib rendered a labeled synthetic template-QA chart to PDF/PNG, visually checked for clipping. Synthetic values never entered the manuscript. Graphviz is absent on this computer; the topology renderer correctly saves DOT and reports UNAVAILABLE, rather than claiming a rendered diagram. Existing manuscript figures were not automatically redrawn.

Local offline verification: 180 core tests plus 11 quality tests passed on both Python3.10 and3.12, including per-source ownership, partial-batch resume, cache context changes, provider deadlines, stagnation reopening and unchanged scientific gates. Independent read-only audits found no remaining important regression. Token telemetry is explicitly limited to successful nonempty responses with reported usage, not total billable spend. Public commits exclude private manuscripts, sources and credentials.

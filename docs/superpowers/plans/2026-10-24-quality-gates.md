# ReviewForge quality gates implementation plan

Goal: fix incomplete Chinese output, make evidence available to both model roles,
and separate PDF compilation from layout and visual acceptance.

Architecture: small offline-testable translation, evidence-context and delivery
modules integrated into the existing v4 CLI. Preserve the existing Python runtime,
master manuscript, project layout and provider configuration.

Scope approved in chat: implement the proposed improvements and upload to GitHub.
Execute inline, with an independent read-only code review before publishing.

## Tasks
- [x] Translation: protected TeX tokens, bounded prose units, checkpoints, retry,
  explicit failure, topic-independent titles and preserved document options.
- [x] Evidence: normalize existing ledger formats, include excerpts and locations
  in writing and review, invalidate cached revisions when evidence changes.
- [x] Delivery: log diagnostics, PDF page previews, hash-bound visual review;
  a generated PDF alone must not imply successful delivery.
- [x] Research workflow: section coverage and figure briefs, issue-based revision
  acceptance, document conservative revision versus outline-led restructuring.
- [x] Regression tests, existing suite, real local compilation/render smoke test,
  independent review, explicit-file commit and push to the existing repository.

## Verification focus
Failed/reused translations; math/citation preservation; captions and headings;
non-fermentation topics; absent/malformed evidence; stale PDF/report acceptance;
unresolved citations and overflowing formulae; model scores without resolved issues.

## Baseline
23 discovery tests: 21 pass; obsolete minimum_pass assertion and a missing-source
fixture expecting a missing-compiler status fail. Correct fixtures/contracts while
retaining the distinction between bibliographic checks and scientific support.

## Decisions
Reuse the current checkout on a dedicated branch. Stage explicit source paths only;
private manuscripts, archives, credentials and generated outputs are excluded.
No paid API calls or full manuscript rewrite are needed for these runtime fixes.
Visual previews do not constitute automated scientific or aesthetic approval.

## Verification record
Independent review identified Windows newline hashing, partial English detection,
visual approval invalidation on resume, spaced citations, and legacy math/table
syntax. Each has a regression test and fix. Real XeLaTeX smoke test confirmed
clean layout PASS and intentionally overwide rule FAILED, both with PDF output.
Final LaTeX pass, rather than intermediate compilation warnings, controls layout.
Final verification: 45 discovery tests and 11 quality-system tests pass. Python
compilation and git whitespace checks pass. External manuscript includes now
explicitly block translation pending flattening; no incomplete include is certified.
Publication: stage explicit source/doc/test paths, fast-forward main and push.

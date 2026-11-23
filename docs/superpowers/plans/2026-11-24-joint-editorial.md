# Joint evidence-backed editorial workflow implementation plan

Goal: complete a manuscript automatically with fewer evidence/review tokens, without losing critical support, resetting existing counters or weakening checks.

Architecture: retain legacy refine/checkpoints unchanged; add an explicitly routed joint clean+condense mode for new work. Use exact claim-scoped fact cells and immutable primary spans, patch-only writing, current-candidate review with exact change records, validated issue locations, persistent bounded local repair and reviewer-only schema correction. Reuse scientific checks only under exact candidate/source bindings. Missing/unresolved evidence blocks acceptance.

Tech stack: Python standard library, existing CompatibleAPI/RequestJournal/TransportTracker, unittest; tiktoken for offline comparisons only.

- [x] Evidence bundle in editorial_scoped.py: deterministic field mapping, quantitative/qualification safeguards, unknown versus available fields, exact cells/anchors retained, full fallback for unclassified claims. Tests before implementation.
- [x] Joint workflow in editorial_joint.py: protected blocks, exact adjacent block patching, strict preservation checks; independent current-candidate reviewer with baseline diffs and exact quote-bound issues; automatic bounded targeted repairs and reviewer-only metadata correction. No manual candidate promotion.
- [x] CLI --mode auto|legacy|joint and stable route manifest; legacy calls and valid old checkpoints remain compatible. Append-only attempt and physical usage budgets, no reset on resume. Free-only validated provider routing from observed history, no consent changes.
- [x] Offline replay same original manuscript with actual writer/reviewer payload generation; count both cl100k/o200k and verify selected facts/quotes/provenance and full text integrity.
- [x] Full software regression suite; one isolated live joint run on the same original R4 source and registry, preserving prior run ledgers. Report real cost/time, automatic completion or exact unresolved defects honestly.
- [x] Update installed skill reference, push and merge verified changes; keep manuscript/evidence/logs private. Deliver measurements after verification. Do not replace the better prior revision with this benchmark or claim fresh PDFs were built.

Validation note: isolated four-block manuscript trial completed with cumulative counts retained. Real total includes debugging calls. The benchmark changed only 58 characters and does not establish equal editorial quality; it did not replace the prior reviewed draft. Original/source math, numerical and citation protections passed; cache-only replay sent no requests. PDF/translation were outside this code-performance validation. Offline token estimates and actual provider usage are separate.

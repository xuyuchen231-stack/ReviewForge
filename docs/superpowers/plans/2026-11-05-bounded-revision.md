# Bounded revision execution implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement task-by-task. Independent code review follows requesting-code-review.

**Goal:** Replace 200k-token repeated editorial calls with bounded fact-card requests and targeted repair, preserving accepted caches, source evidence and all scientific gates.

**Architecture:** Keep canonical fact extraction and existing cache identities. At model request boundaries, reuse exact semantically reviewed fact values and qualifications; retain raw primary anchors locally. Bound review batches by actual encoded payload, not prose length alone. Make scientific blockers distinct from optional editorial preferences, and persist attempt/usage records across restarts.

**Tech stack:** Existing Python 3.10 standard library, unittest, current compatible API clients.

**Spec:** User request in this chat: optimize first; reduce latency and cost, complete the workflow without repeatedly stopping, preserve manuscript quality. Existing scientific gates and accepted work must not be bypassed. No new paid models, dependencies, duplicate runs or unbounded live tests.

## Constraints and review focus

- Do not change WRITE/REVIEW constants or source bindings merely to invalidate accepted units.
- Exact values, qualifications, fact IDs, source-access metadata, mathematics and citations survive projection. Raw anchors remain in canonical registry; contested claims can request exact evidence explicitly.
- A scientific rejection stays blocked. Optional wording changes must not become invented scientific failures.
- No budget reset on context changes. No retry loop for a fixed scientific rejection.
- Unknown/truncated/invalid outputs never count as success. Transient retries stay bounded and logged.
- Review oversized inputs through complete paragraph batches with coverage validation, never string truncation or dropped studies.

## Tasks

1. [ ] Add failing tests for compact exact fact cards, hard request limits, bounded complete paragraph review and preserved qualification/access information; implement request preparation and measure the actual u8 snapshot.
2. [ ] Add failing tests for short localized repair inputs, severity-aware optional suggestions, exact paragraph coverage, and rejected claims remaining rejected; implement reviewer clarification and targeted repair without cache resets.
3. [ ] Add failing tests for append-only request accounting and stale usage isolation; preserve retry records, aggregate actual usage and input characters without logging prompts or keys. Prevent fixed scientific rejection from automatic whole-workflow retry and preserve cumulative edit budget counters.
4. [ ] Fault-inject malformed JSON, truncation, interrupted review, failed patch and changed evidence; exercise writing, repair, independent review and section assembly on an isolated fixture. Run full checks and independent code review. Measure real snapshot input before/after. Only then perform one bounded live u8 review if its input passes the cap; report its actual outcome without claiming the entire manuscript is complete.

Delivery: local code + installed skill guidance + GitHub, updated instructions and concrete measurement. Do not promise one-pass scientific acceptance or guaranteed provider availability.

## Verification and rulings

Tasks 1–4 implemented and verified with the complete offline suite and an isolated
copy of the active manuscript. Independent read-only review found no remaining
blockers after evidence retrieval, physical-send accounting and global assembly
consistency fixes. No production source approvals were changed by simulated tests.

Exact accepted units may inherit their existing source checks only after validating
the saved plan, candidate hashes, review checks and byte-exact section assembly.
A separate all-unit consistency review and final manuscript source audit remain.
Optional minor style feedback never overrides a failed scientific boolean check.

Actual bounded u8 validation used TokenHarbor's configured free model. Four physical
requests (including one schema follow-up) consumed 74,195 input and 3,380 output
tokens; the previously observed single u8 review consumed 201,740 input tokens.
This is a 63.2% input reduction for this comparison, not a promised whole-run saving.
Physical response times were 6.483, 8.931, 11.982 and 13.593 seconds. The review
still rejected specific unsupported/offline-reference and validation-split wording.
The isolated test did not promote approval, reset budgets or restart an expensive
whole-run loop. The active manuscript is still incomplete, not submission-ready.

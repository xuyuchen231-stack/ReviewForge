# Review convergence implementation plan

> **For agentic workers:** Use executing-plans for inline implementation and one independent review at the end.

**Goal:** Reduce repeated model work without granting scientific acceptance.

**Architecture:** Reuse the existing unit checkpoints, paragraph validation and persistent budgets. Add an issue history within each unit budget; retain full review records. Exact unchanged accepted units retain local approval after discourse-only context changes, while mandatory assembly consistency review checks their interaction.

**Tech Stack:** Python 3.10 standard library, unittest.

**Spec:** User-approved workflow changes in this conversation, 2026-11-07.

## Global constraints

- Never reset cumulative budgets, truncate evidence or force approval.
- Changed sources/contracts still change the existing unit-folder binding.
- No provider concurrency: shared free-account cooldown and reservation state is not concurrency-safe.
- Preserve unresolved or contradictory scientific objections; repeated rejection pauses for diagnosis.

## Review focus

- Accepted but incomplete/changed checkpoints must not reuse approval.
- Optional style requests must not enter repair batches.
- Restart cannot erase a stalled issue history.
- Changed substantive issues reset only the stall streak, not edit budgets.
- Unchanged writer output must not incur another identical independent review.

### Task 1: Consistent blocking-row classification

- [x] Add failing test mixing optional style and a factual defect.
- [x] Reuse one predicate in review validation and local repair.
- [x] Run local repair and paragraph tests.

### Task 2: Persistent exact issue history and no-progress guard

- [x] Test stable issue IDs, duplicate issue coalescing, restart and changed issue sets.
- [x] Save exact reviewer requirements and paragraph anchors in unit budgets.
- [x] Stop after three consecutive equivalent blocking reports; preserve diagnosis and all review gates.
- [x] Reject identical repair output locally rather than paying for another review.

### Task 3: Reuse local approval under discourse-only changes

- [x] Test unchanged accepted units make no new reviewer call, while rejected units still revalidate.
- [x] Preserve original review-context hash and mark assembly context check required.
- [x] Keep mandatory exact assembly/global review and source/contract cache bindings.

### Verification and delivery

- [x] Run all tests and an isolated snapshot replay, no paid/live model tests.
- [x] Independent code review, address findings, update runtime documentation.
- [x] Push tested changes to existing GitHub main; do not restart an unchanged scientific rejection.

Validation: 505 unittest tests passed; independent review found no remaining blockers. Isolated current-run replay reused seven accepted units and preserved the u8 scientific blocker, with no live APIs or production checkpoint changes. Provider concurrency was deliberately deferred; semantic contradiction adjudication remains source-backed diagnosis, not heuristic approval.

# Bounded major-revision execution

Use the current `major_revision.py` request path. Defaults cap later editorial
inputs at 90,000 encoded characters; `RF_MAX_REQUEST_INPUT_CHARS` is bounded between
10,000 and 120,000. Characters are a local safety limit, not a token estimate.
Initial immutable-source extraction has a separate 180,000-character ceiling.
Oversized writing splits intact source blocks, reviews split complete paragraphs,
and upstream fact verification retains all exact quotes through shared references.
An indivisible oversized item stops before dispatch rather than silently truncating.

Canonical fact cards retain exact values, fact IDs, source hashes, access and
qualifications. They are not newly generated summaries. Specific original anchors
can be requested once; unresolved or unknown evidence requests remain blocking.
Do not publish unsupported components of qualified records. Existing accepted
units remain valid only under their current source/context bindings.

For unchanged assembled units, hash-verify the plan, each candidate and accepted
review, and the exact assembled text before inheriting source checks. Check all
unit findings and paragraph messages together for cross-unit conflicts, retrieving
exact disputed paragraphs as needed. Local assembly review and the final
sentence-level source audit remain required. None confer expert verification.

`model_requests/requests.jsonl` records logical calls and actual HTTP sends without
prompt bodies or credentials. Aggregate physical sends when present for a binding,
not both levels. Unknown failed/interrupted usage stays unknown. Parsed responses
are cached separately from scientific acceptance. Persistent physical budgets allow
at most three chargeable/unknown sends and 24 total sends per unchanged request;
known HTTP refusals still count toward the total limit. Scientific rejection does
not trigger whole-workflow network recovery. Do not reset budgets to obtain a pass.

Verification includes exact source preservation, changed-evidence invalidation,
malformed/truncated responses, evidence requests, complete paragraph coverage,
cross-unit conflicts, fallback accounting and restart limits. A simulated pass tests
software control flow only; report real model rejection honestly and repair its
specific evidence issues rather than promoting a fixture or disabling the gate.
# Review convergence and reuse

`major_revision.py run --research-loop` keeps a single worker alive through reconstruction
and export. Use `--once` only for finite diagnostics. An exclusive OS lock prevents
duplicate workers for the same run. `worker_state.json` distinguishes actual work,
provider waits and unresolved diagnosis; waiting is not manuscript progress.
Creating `stop_continuous` in the major-revision root stops the loop after the
current bounded request. Saved cooldowns are respected before dispatch.

After a bound section rejection, a separate structural-repair queue can revise or
merge the implicated unit without resetting the old 4-write/6-patch counters.
Its explicit additional allowance is 12 calls per run, persisted in
`structural_repairs.json`. Each exact issue is tried once; a transport failure may
resume once, still spending the same cumulative allowance and physical-send caps.
Original unit/section/review records are archived. Numeric results, mathematics
and citation sets must survive; changed drafts remain unaccepted pending normal
independent review. A rejected identical repair is not purchased again.
Exhausted or unresolved scientific work enters an honest diagnosis wait without
repeated API calls, and resumes on substantive checkpoint correction. Unresolved
normal returns such as `NEEDS_REVISION` never mean completion. Final PDF delivery
still requires scientific, translation and layout checks; shutdown stays revoked.

The unit folder binds source facts and writing/review contracts. If only earlier
units' discourse findings change, an exact, complete, accepted local unit review
may be reused. The checkpoint retains its original review-context hash and marks
`assembly_context_recheck_required`. This is local approval only: the assembled
chapter still requires exact unit verification and all-unit consistency review.
Source/qualification or contract changes continue to invalidate the folder binding.

Each unit's existing `.budget.json` now records `review_convergence`: exact reviewer
requirements, paragraph anchors and citations, stable IDs, failed checks and review
rounds. Exact duplicate requirements are coalesced; semantic equivalence is not
guessed. Historical issues are not automatically called resolved when absent from
a later report. Contradictory or newly changed requirements need diagnosis against
the source; an old reviewer verdict does not override new primary evidence.

Three equivalent blocking reports create a `convergence_block`. An identical
writer candidate also blocks immediately, before another independent review.
Restart alone cannot clear either block. Other units can still finish.

To resume after inspecting the actual source/paragraph, save a genuinely corrected
candidate as unaccepted/pending review with a valid candidate hash, or attach a
`repair_diagnosis` to the unit checkpoint with `block_sha256` (the signature of the
current budget's convergence_block), a concrete `reason`, and a specific `action`.
The runtime saves a one-use diagnosis receipt and the old block. It clears only
the stall streak; all issue history, full-write and paragraph-patch budgets remain.
An exhausted edit budget remains exhausted. Never manufacture approval or attach
an empty/repeated diagnosis merely to retry.

Optional minor/observation style suggestions use the same predicate in review
validation and paragraph repair, so they cannot enlarge a necessary repair batch.
Provider calls remain serial until shared account cooldown/reservation state is
made concurrency-safe; local deterministic checks require no model call.

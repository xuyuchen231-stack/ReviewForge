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

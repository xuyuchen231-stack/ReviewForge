# Source reading and scoped evidence packets

Adapted conceptually from Aut_Sci_Write, inspected at commit
`357766f90bd42f4f982d054be55c687c27202f22` (2026-11-20).
Source: https://github.com/ShZhao27208/Aut_Sci_Write
Relevant modules: `sci-extract/SKILL.md`, `harvester/render.py`, `sci-review/SKILL.md`.
This is an independent adaptation, not installation of the upstream suite.

## Read according to the source's purpose

For primary research, establish the process/problem, mathematical mechanism,
measured inputs and outputs, comparator, validation split, quantitative results
and operating limits. Explain how the model works before judging its performance.
For a review, extract its scope, organizing taxonomy, evidence selection,
consensus, disagreements and their causes, evidence gaps, and useful comparison
figures/tables. Do not treat a review's summary as verification of its cited
primary studies. Retrieve those studies for disputed or numerical claims.
Reuse unchanged hash-bound extractions; do not reread every source on every pass.

## Capture status is separate from claim support

Record text access (`full-text`, `partial-text`, `abstract-only`, `metadata-only`),
figure access (`publisher`, `pdf-crop`, `unavailable`, `not-requested`), source
identity, extraction method, source hash and exact locators in the existing ledger.
A crop needs visual caption/panel verification; order matching alone is insufficient.
A failed extraction means unknown, not that the original paper lacks a figure.
Keep retrieval failures and possible legal access routes in the audit record;
never claim access or bypass restrictions. Successful retrieval does not certify
semantic support, numerical correctness or permission to reproduce an image.

## Synthesize instead of listing papers

For each substantive comparison, state the shared scientific question, why the
methods differ, the evidence under comparable conditions, and what follows for
model selection. Explain disagreements through conditions, measurements and
validation design before proposing a research direction. Merge a subsection when
it contributes no distinct argument. Fit the author's chosen structure; do not
force a four-section CS template, quantitative abstract claim, word blacklist or
AI-detection score onto a fermentation narrative review.

## Small exact packets, no extra model rounds

Use existing registry retrieval first. For ad hoc local source text, the offline
`scripts/evidence_packet.py` builds an exact, hash-bound packet from selected
character spans. It does not call any API, infer evidence quality or approve a
claim. The JSON plan contains `question`, `sources`, and each source's `id`,
`path`, `sha256`, `text_access`, `figure_access`, `spans`; each span contains
`start`, `end` (Python character offsets in UTF-8 decoded text) and `locator`.
Paths are relative to the plan. Hashes bind original bytes; excerpts retain exact
text. Choose intact passages with qualifications and request additional spans
when a reviewer needs context. Selection remains the author's/agent's responsibility.

Run `python scripts/evidence_packet.py plan.json packet.json --max-chars 24000`.
The explicit character budget is not a tokenizer or a provider token guarantee.
Over-budget packets fail without silent truncation or writing a partial output;
select a smaller coherent question or split by complete passages. Missing sources,
stale hashes, duplicate IDs, missing locators and invalid ranges also fail.
Keep full sources local. These packets supplement existing retrieval; review gates, provider routing and
repair budgets stay unchanged.


## Runtime integration and measurement

`evidence_transport.encode_context_payload` applies the same codec after existing
exact-duplicate and row sharing. The v4 writer/reviewer, major-revision provider,
autonomous checkpoint caller and editorial-refinement caller use this encoder.
The packet interns only identical long evidence strings (minimum 256 characters)
when serialized size falls at least 10%; it does not select, summarize or truncate.
Every packet is expanded locally and compared to the complete prior payload before
use. Existing source hashes and locators remain exact; additional text hashes bind
UTF-8 strings and are not claims of original-document verification. No new model
calls, review stages or acceptance logic are introduced. A standalone runtime that
lacks the optional skill codec retains its previous transport.

Run `python benchmark_evidence_packets.py --manuscript <body.tex>
--workspace <run> --output <report.json>` from the runtime directory. This replays
actual writer preparation and client encoding using a capture-only API; it never
contacts a provider. Optional benchmark dependency: `tiktoken`. Report both the
previous transport and raw JSON baselines; distinguish exact local tokenizer
counts from actual billed provider tokens. Do not use identical before/after
manuscripts as a purported observed reviewer request. Full payload roundtrip must
pass for every case. This proves transport integrity, not scientific correctness
or unchanged model output quality.

# Clean reference and condensed manuscript

Evidence rules govern reasoning; they are not paragraph templates. Start with the concrete
scientific finding and its conditions. Explain comparative mechanisms, differences and the
decision implied by the evidence. State shared reporting/access limitations once at the relevant
scope, with paper-specific qualifications only when they change a conclusion. Retain meaningful
uncertainty, counterevidence and missing-validation consequences. Do not infer authorship from
repeated language.

After scientific assembly, `editorial_refinement.py` provides two distinct stages: clean the
complete reference manuscript, then condense that cleaned version. Keep the raw source snapshot
internally. The author-facing complete reference version must itself be cleaned, not the raw
disclaimer-heavy manuscript. Partial stages must not be delivered as complete named versions.
Every chunk passes structural/numerical preservation and provisional before/after model review.
No change grants expert verification or changes scientific unit acceptance. Failure pauses;
resumption reuses reviewed chunks bound to source and prompt hashes.

The evidence CSV preserves source access, field status, locators and study dimensions separately
from publication prose. Unknown access remains unknown; it does not show that a method was not
reported or performed. Inspect original sources for new empirical claims.

Aim for 25–30 pages only after scientific redundancy is removed. Page count is an editorial goal,
not a license to shrink fonts, discard necessary results or truncate chunks. Confirm physical page
count on the compiled final manuscript before claiming that target has been met.

Notation requires a role registry: state vector, biomass scalar, manipulated inputs and external
disturbances. Never globally replace x/X or e/u. Audit labels and actual compiled references;
a forward reference to an existing equation is not a missing equation.

Additional conceptual figures should clarify learning interfaces, locked validation information
boundaries and the M0–M4 revision ladder. Do not present conceptual curves as experiments.
H1–H4 numerical comparisons require an independently executed protocol with frozen train,
validation and test splits, raw outputs and declared model assumptions. A synthetic fed-batch
example is not experimental fermentation data or a validated PenSim replication.

Critical citation sampling runs inside the same editorial writer/reviewer calls, with at most
eight identities and 7000 characters of source anchors per chunk. Both nodes receive the same
evidence. Require complete per-selected-key judgments and exact candidate passages; absent
anchors cannot receive supported/qualified status. Keep uncertain and unsampled keys explicit.
Do not describe a bounded sample as a completed whole-bibliography verification.

One targeted repair is permitted per failed chunk; further failures are queued while other chunks
continue. Resume pending reviews without rewriting their drafts. Evidence changes create separate
version directories; reuse only content/context/prompt-bound unchanged chunks. Numerical identity
checks permit repeated mentions to be consolidated; model review still checks their units,
referents and conclusions. Protected mathematics remains byte-identical.

The standalone refinement command compiles clean and condensed versions independently, checks
actual PDF citation order and exports source-only Overleaf projects. Technical readiness, visual
review, page target and scientific approval remain separate. A visual failure blocks readiness;
pending visual review cannot be promoted to approved delivery.

## Compact publication

Default to final English/Chinese PDFs only in `workspace/成果`, with
explicit local start/end times in filenames and offset-aware timestamps in the internal manifest.
Keep the cleaned complete reference source, editable bilingual source/assets and run metadata in
one internal source ZIP. Keep original literature and resumable scientific/evidence checkpoints;
never delete them merely to reduce visible clutter.

Publish only a fresh pair bound to both build source/PDF hashes and translation provenance. Keep
the previous complete pair if Chinese fails. Build only the condensed version by default and
translate it once. Do not persist per-page PNG previews unless explicitly requested. Remove only
known regenerable build debris after publication.

Historical generated validation directories may be archived and removed only through an explicit
allowlist, root/link guards, verified archive hashes and unchanged-file checks. Preserve unique
logs/results and referenced manuscript assets. Do not interrupt active work.

Caption prose may change under semantic review. Exact table data/structure, figure construction,
caption mathematics, numerical identities, citation identities and references remain protected.
Old mechanically blocked drafts are re-reviewed only if the narrowed deterministic rule now
passes. Candidate citation passage IDs provide exact copied quotes, never fuzzy matching or a
fabricated scientific pass. Accepted existing chunks remain reusable.

## Figure and citation presentation

Honor the user's integrated a–d overview and single-column companion preference. Replace only
actively labelled generated RF figures with verified generated-asset provenance, never a data
figure whose comment happens to contain an RF label. Preserve analytic illustrations and author
data. Remap generated references and keep explicitly single-column floats at column width.

Export plain narrative instead of ordinary prose bullet lists, retaining exact scientific content.
Equation labels inside lists do not block conversion; genuine referenced item counters do. Flag
unresolved presentation before translation. Sort numeric parenthetical groups, preserve textual
author order, and reconcile actual first-use order independently for English and Chinese PDFs.
Repeated citations keep their assigned identities; do not renumber on every repeated mention.

The compiler timeout covers the entire owned process tree. On Windows create the compiler root
suspended, assign the kill-on-close job, then resume; no helper should escape before containment.


## Joint editing and automatic bounded recovery

Use `editorial_refinement.py refine --run RUN --mode joint` for a single final
cleaned/condensed candidate. The existing `--mode legacy` keeps two independently
edited versions and all their checkpoints. `auto` uses legacy for an existing
legacy current manifest, joint otherwise. Never restart seven-chapter construction
to run this editor, and never substitute a new source for an in-flight checkpoint.
Joint produces `versions.condense` and an original snapshot, not a falsely named
clean intermediate. Compilation, translation and layout gates remain unchanged.

The writer returns adjacent-block patches. Full selected canonical field values,
source-check qualifications, access scope and relevant primary spans are retained;
other original fields/spans remain explicitly retrievable. An unclassified claim
uses full fields. Missing selected support or an unresolved requested anchor cannot
be treated as verified evidence. Citation sampling is still sampling, not a new
full-bibliography or expert scientific approval.

The independent reviewer sees current paragraphs once and only replaced baseline
spans for loss checking. Blocking issues must quote the current or genuinely removed
text. Targeted repairs use located paragraphs and neighboring context. Invalid
quote/version ownership gets one reviewer-only correction; exact primary evidence
requests get bounded source retrieval in that same correction. Do not add a separate
stylistic approval loop. A scientific rejection is never a format correction.

Duplicate citation checks are consolidated only after every passage binding is
valid; retain all original rows and the worst status. An invalid passage ID can
receive one small independent citation-only recheck, bound to the unchanged candidate.
This inherits only already-positive preservation checks and cannot erase unsupported
or unresolved scientific findings. Invalid math/data patches are discarded locally;
valid neighboring edits remain. A historical invalid candidate is retained before
rollback. Do not pay repeatedly to rewrite a corrupted candidate.

Persist counts before requests, completed responses before processing, all rejected
reviews, exact source/context identities and repair receipts. Three writer calls and
six reviewer calls per chunk remain cumulative across restarts; actual HTTP sends
also use TransportTracker. A no-op after a real rejection stops, never buys another
review of identical prose. Diagnose the exact unresolved issue without resetting
budgets or approving it by hand. True unresolved defects can still block completion.

`--route-history JOURNAL` can inspect existing physical-send records, without a
probe: only failures of the configured preferred free writer on two distinct
accounts plus a successful configured free fallback writer allow choosing that
fallback. This changes no allowance and grants no extra send. A later preferred-route
success supersedes the diagnosis. Free access consent is never changed automatically.
Joint CLI permits TokenHarbor free and explicitly allowed self-hosted Free.ai routes,
never APIMaster, premium Free.ai or unapproved paid fallbacks.

Do not claim token savings alone prove equal manuscript quality. Record the actual
amount changed, preserved math/data/citations, unresolved issues, call history and
whether a run needed interventions. Include debugging calls in actual totals; mark
prospective/offline estimates separately. Never overwrite a better reviewed draft
with an almost unchanged benchmark candidate merely because its model accepted it.


### Continue a real revision with documented unresolved issues

For validation from a previously revised manuscript use `--source completed.tex`
with `--mode joint --revision-plan plan.json --run EVIDENCE_RUN`. The original
scientific master is not overwritten. The plan must bind `source_sha256`, supply
`requirements_by_chunk`, `required_citekeys`, and existing `shared_budgets` paths.
Each shared budget starts from recorded spent counts; reserve new calls in the
same file before sending, even when source/request bindings change. Missing or
malformed inherited budgets block continuation. An exact `cross_section_context`
quote must exist in the supplied current manuscript. Review the current draft
before buying another writing pass; only a located unresolved issue triggers repair.

A generic positive verdict does not resolve a documented issue. Every requirement
needs a resolved status, an exact current passage and reason; its required sources
must be supported or qualified rather than uncertain. Prior citation coverage can
be included via required_citekeys. Keep whole-manuscript assembly/coherence and
mathematical checks separate from local citation checks; citekey sampling never
establishes complete bibliography or expert verification.

Prefer current block IDs for review metadata; code copies exact text. Completed
metadata responses are replayable after interruption without spending another call.
Conservative normalization of an invalid *negative* issue category preserves the
negative verdict and original explanation; it never supplies approval.

A table's source-located plain narrative cells can be clarified under independent
semantic review. Mathematical content, numerical cells (including number words),
LaTeX structure, commands and citation identities stay exact. Match ownership by
source span rather than repeated cell text elsewhere. Archive a rejected patch;
when the only cause is this objectively overbroad table-prose lock, reapply its
already-saved response as an unaccepted candidate and independently review it.
The writer count remains unchanged; never convert the old rejection to approval.
Report such repairs and debugging interventions honestly.


### Avoid paying for already completed scientific checks

Treat review-record format repair as indexing, not another scientific review.
Prefer supplied block IDs on the first response. An invalid current quote receives
at most one small option-ID selection request, with no full evidence bundle. Code
copies the exact existing location and cannot change accept/check booleans, source
verdicts, resolution statuses, explanations or manuscript prose. If this fails and
no real located manuscript issue exists, stop with the record error; never send
correct text to an author for a no-op rewrite.

For an explicit source request, send only the requested exact original fact cells,
qualifications and primary anchors, affected current passages and necessary exact
cross-section context. Do not resend unrelated studies or a whole passed unit.
The four scientific preservation checks must already be positive for this bounded
source-only path. An existing failed editorial check remains failed; supplementing
sources does not auto-approve it. Preserve unrelated negative findings and newly
unresolved tasks, including over-returned model rows outside the requested subset.

After an actual patch, still review the COMPLETE current candidate and real before
changes under all five criteria. Reuse only citation findings whose exact passages
remain unchanged, were supported/qualified, and have identical binding/evidence
context hashes. Conservative change ownership includes affected table rows and
adjacent citation windows; unknown ownership or changed source context falls back
to full evidence. General whole-chunk requirements are always freshly judged.
Original evidence for an inherited source remains retrievable on demand; requesting
it promotes it to fresh scope. A new negative finding supersedes every inherited
positive. No scientific or source access qualification is silently upgraded.

Source/candidate/context-bound accepted receipts can recover a partial checkpoint
or a saved patch already independently approved. Validate the entire receipt and
normal acceptance gates, preserve all spent counters, and reject a receipt after
later negative scientific events from any review channel. An old positive receipt
cannot discard a later negative citation, unresolved task or false preservation
check merely because text hashes match. Do not reuse approval after context changes.

Freeze code before validation and retain failed freezes. Distinguish historical
response replay, live location-only checks, cache continuation, offline encoded
payload estimates and new live scientific review. A small index-repair bill is not
an equivalent-workload whole-paper token benchmark. Report refusals and unknown
usage separately and never reset budgets to obtain a pass.

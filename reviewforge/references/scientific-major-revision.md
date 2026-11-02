# Evidence-first scientific major revision

Use this route when problems involve inconsistent primary-study facts, repetitive argument,
weak comparative synthesis or an unclear contribution. Language-only polishing cannot repair
those problems. Preserve the original and published bilingual pair while reconstructing.

## Shared facts before prose

`study_registry.py` stores source-versioned facts once per study. Organism, product, scale,
independent cultivations, learning location, operating changes, prediction-time information,
updates, split roles, comparators, outcomes, uncertainty, constraints and computational timings
are separate matrix dimensions. Distinguish microbial experiments, microbial simulations,
adjacent-domain methods and reviews. Do not treat an augmented sample count as independent
cultivations or a test set used for selection as an untouched final test.

An acquired full text overrides stale abstract-access metadata. Publisher-index excerpts are
not complete full texts. Selected passages cannot establish that a paper did not report a detail.
The major-revision route checks public publisher PDF links recorded by Crossref, verifies the
DOI in extracted PDF text and records failures separately. Public access checks are bounded and
cached; they do not bypass a subscription or guarantee that every paper becomes available.
Source snapshots include content hashes; do not overwrite an older source file with new text.
Conflicting positive extractions require a logged, source-grounded reconciliation. History remains
inspectable; a more recent file alone is not evidence that an older factual statement is wrong.
Quotation checks and semantic checks are separate. Rejected/unreviewed facts cannot support a pass.

## Reconstruction and density

The supplied 13-section fermentation manuscript has a seven-section reconstruction contract in
`major_revision.py`: introduction; formulations/guarantees; operating-change evidence;
identifiability/history/scale; model-revision decisions; validation/uncertainty/operational use;
synthesis/priorities. Other manuscript structures need their own mapping rather than silent slicing.
The contribution is the application of operating-change and prediction-information coordinates
to a defined study cohort, not the generic recommendation to validate independently.

Keep supported experimental details and analytical examples; remove repeated conclusions and
retrieval disclaimers. Word budgets guide editing, never truncation, font shrinking or fabricated
results. Preserve formation-loss nonuniqueness and ratio-derivative examples once. Correct feed
trajectory versus scalar-amplitude sensitivity explicitly. Separate algebraic conservation,
feasible projection to numerical tolerance, finite penalties and observation-only corrections.
Do not add simulated curves and label them experimental. Search dates, inclusion rules and
full-text coverage must describe actual records; unknown search provenance remains unknown.

Export the complete evidence matrix as JSON, long CSV and one-row-per-study CSV. Put access
bookkeeping there; main text should synthesize concrete findings. Core microbial evidence should
anchor conclusions; CHO/flocculation examples are methodological background, not substitutes.

## Running and interpreting status

From `reviewforge-runtime`, `python major_revision.py prepare --workspace .\workspace` snapshots
the current manuscript and prepares the plan/matrix with **zero model calls**. This is not a
completed revision. `facts` performs shared source-card extraction; `run` resumes extraction,
reconstruction, independent section review, whole-manuscript scientific review and the existing
bilingual export. It has bounded individual requests and repairs, with no arbitrary total-hour
cutoff. Only configured TokenHarbor free models are permitted; APIMaster is excluded.

Accepted cards and sections are cached by relevant source/contract content. Rejected sections
can be repaired on resume; final-review findings invalidate affected accepted section caches.
After a bounded repair, unresolved evidence or scientific issues stop with an inspectable report
rather than endlessly consuming calls. Original files are not replaced by the reconstruction.

`scientific_quality.py` binds review to exact manuscript sentence units, covers repeated cited
occurrences and compares same-study descriptions across sections. Oversized cross-section groups
remain explicitly uncovered; they cannot silently pass. It is a model-assisted review, not proof
that every claim is true. PDF build, translation, editorial completion, provisional scientific
model pass, expert verification and submission readiness are different states. Never report
`submission_ready`, `expert_verified` or `author_approved` merely because code/tests/PDFs pass.

The default delivery chain reports scientific status separately; runs carrying the scientific
revision policy require this gate before delivery. Source/fact changes invalidate relevant review
caches; layout/reference changes also refresh the final manuscript-bound report.

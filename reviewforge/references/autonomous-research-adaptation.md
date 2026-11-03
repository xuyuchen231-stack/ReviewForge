# Autonomous research methods adapted for scientific reviews

Read the relevant sections when planning or improving an unattended review run.
This is a ReviewForge adaptation of ARIS principles, not an ARIS installation or
a claim of feature parity. Source inventory: `aris-source-map.json`. Attribution
and the upstream MIT notice: `../THIRD_PARTY_NOTICES.md`.

## 1. Agree on completion before spending calls

Turn the user's existing scope and preferences into a short, checkable contract.
Reuse instructions already supplied; do not reopen settled choices or require an
approval ceremony for an authorized run. Separate required deliverables from
optional polish. For this user's current review the contract includes the items below. For another
review, keep only the deliverables and layout/languages actually requested:

- a specific review question and contribution relative to existing reviews;
- the decisive claims linked to inspected primary facts, with contradictions resolved;
- genuine comparisons within compatible study designs, not a study catalogue;
- calibrated title, abstract and conclusions, including domain and validation scope;
- retained useful reasoning, coherent notation and valid formula/citation references;
- requested two-column layout, readable single-column figures, bilingual consistency;
- final PDF build and actual visual checks, rather than a compiler-only success.

Do not import an arbitrary citation count, minimum section length, score threshold,
journal page budget or requirement to run experiments. A style exemplar describes
an editorial pattern; it does not create the target journal's requirements.

Track preparation, drafting, scientific review, export, visual QA and authorized
delivery separately. Completion of one stage is not completion of the manuscript.
Model judgments remain provisional even when all machine checks pass.

## 2. Plan the argument and the evidence together

Build a compact claim matrix with claim ID, exact assertion, type (reported result,
analytical inference or proposed test), primary fact IDs/locations, opposing evidence,
conditions, intended section and any figure/table. A citation is not the assertion.

For a review, experiments in ARIS's matrix become studies, comparisons and analytical
examples. A new simulation is optional work with explicit assumptions and authorization;
it must never be invented to make the review appear more empirical. Elementary algebra
needs clear assumptions and derivation, not unrelated application citations.

Assign each section a scientific question and each unit a distinct inference.
Preserve meaningful disagreements and negative results. State what a study changes
about a decision; avoid repeated definition → example → disclaimer templates.
Draft conclusions from the whole accepted evidence set, not just the old conclusion.

## 3. Read progressively, verify decisively

Start with available local PDFs and the existing evidence registry. Search externally
to resolve a named gap, find counterevidence or establish the closest prior review.
Deduplicate study identities across preprints, publisher versions and database records.
Use metadata/abstracts for discovery; locate methods, results, tables and supplements
for a decisive claim. Record source version, location and access level once in the ledger.

Treat a search failure as a failed retrieval, not evidence that work does not exist.
Never turn absence from an inspected excerpt into "the authors did not report it".
Keep raw source text distinct from generated summaries and reviewer conjectures.
New source evidence may supersede a previous summary; preserve the reason and apply
the correction consistently across chapters. Do not treat repeated model agreement
as an independent primary source.

Use three citation checks: existence, bibliographic fields, and claim support in context.
Check author order/year/venue/identifier when identity is ambiguous. For disputed entries,
independently reconstruct the record without using the suspected field as truth; do
not launch a multi-agent audit of every settled entry by default. The actual compiled
EN/ZH citation sequence still needs verification.

## 4. Review independently and repair in proportion to the problem

The reviewer gets the current candidate, primary facts, scope and completion contract.
Hide previous numeric scores and the author's persuasive defense during a fresh final
assessment. Actual model independence must be reported honestly: a separate request
to the same configured model is a separate context, not a different model family.
Stay within the authorized free TokenHarbor routes; no premium-model substitution.

Preserve the raw review. Resolve a malformed or contradictory report before issuing
another broad request. In particular `accepted=true` cannot close an OPEN CRITICAL or
MAJOR issue. Ask for the disputed judgment/format only; do not regenerate good prose
to fix a malformed review envelope.

Classify actual issues, not the reviewer's tone:

| Severity | Meaning | Response |
|---|---|---|
| CRITICAL | Fabricated/wrong evidence or a central conclusion contradicted by sources | Hold the affected claim and resolve evidence first |
| MAJOR | Material scope error, unsupported transfer, missing decisive comparison | Repair the affected argument and re-review it |
| MINOR | Citation placement, concise wording, local exposition/layout | Patch locally, recheck; let independent units proceed |
| OBSERVATION | Optional preference without a concrete error | Record once; do not spend repeated calls chasing it |

An issue record needs a stable ID, location, assertion, source basis, severity,
requested change and a closure test. Close it with the actual change/evidence and
independent recheck. Rephrasing an unsupported assertion is not a factual repair.
Keep issue details in the audit log, not defensive language stapled to every paragraph.

## 5. Finish bounded loops instead of endlessly polishing

Count only completed reviews against the same task and materially comparable evidence.
Record accepted new findings, closed issues and substantive changes. A timed-out call,
provider cooldown, monitor tick, higher score or extra page is not scientific progress.
Count consecutive completed no-gain reviews; a validated finding or issue closure
resets the count. A changed candidate version alone does not reset it.

- After two completed rounds with no supported new finding or issue closure, change
  the repair strategy: group duplicated claims, move access bookkeeping to the matrix,
  obtain the decisive source, or narrow the unsupported scope.
- Preserve the research question. "Structural pivot" means changing how to resolve
  the blockage, not silently switching topic or lowering the completion standard.
- After four completed no-progress rounds, report the concrete persistent blocker.
  Suspend that unchanged scientific loop until new evidence or a materially different
  repair strategy is available; independent work may continue. Preserve the best
  evidence-supported candidate; do not keep restarting or accept it because time expired.
- Reuse valid source cards, drafts and reviews. Changed evidence/claims invalidate
  their dependents, not unrelated chapters. Re-review patched coherent units.
- Treat technical recovery, quota waits, scientific revision and style polish as
  different states. Respect server retry deadlines and persistent account budgets.

The optional offline helper `../scripts/campaign_state.py` evaluates declared records:

```text
python <skill>/scripts/campaign_state.py --input campaign.json --output campaign_advice.json
```

Input fields: `revision`, `reviewed_revision`, `checks` (name → PASS/FAIL/UNKNOWN),
`issues` (id, severity, status, required, resolution_evidence, independently_reviewed),
`history` (kind, unique review_id, new_findings, closed_issue_ids), optional
`wait_until_epoch`. For mixed histories include task_id and evidence_scope on the
snapshot and each event; only matching events count. Duplicate IDs count once;
completed reviews lacking an ID are reported but do not count toward stagnation.
Use `completed_review` only for completed judgments and list only validated gains.
Required checks come from the user's contract; do not omit an unmet requirement to
obtain PASS. CLOSED without evidence and independent review remains unresolved.
The helper does not inspect source documents, verify PDFs, certify a paper, send
mail, restart tasks or turn off a computer. It is an advisory tool for the agent,
not a replacement gate for the existing runtime.

## 6. Test the whole argument, not only local paragraphs

At the manuscript milestone, extract a reverse outline: one main message per paragraph,
each section's answer, and the evidence behind the final takeaways. Read the messages
in sequence. Merge duplicated claims; repair logical gaps and conclusion drift.
Do not force identical paragraph functions or regenerate all paragraphs for variety.

For a scope-heavy review, use one independent adversarial question: what is the strongest
source-supported reason the headline conclusion could be wrong? A separate adjudication
checks the current text against that objection. This can use the existing global review
pass; it is not two mandatory expensive extra calls on every unit. Unsupported cross-domain
generalization, a comparison without comparable conditions, and novelty already covered
by a prior review are high-value targets. Do not demand the paper rebut every imaginable
objection. An attack memo is a hypothesis to check, not evidence by itself.

Separate citation identity, factual entailment, numerical provenance, mathematical
validity and overall scope. A paper can pass one and fail another. "No new blocker
found" is not expert certification, proof of originality or absence of all errors.

## 7. Write concise, specific scientific prose

Lead with the strongest supported result or comparison. Use specific methods, controls,
quantities and conditions where they matter. Put retrieval bookkeeping in the evidence
matrix, and consolidate a shared limitation rather than repeat it after every citation.
Retain a qualification locally when removing it would strengthen or alter the claim.

Prefer direct subjects and verbs. Remove sentences that add no evidence or necessary
inference. Do not implement a word blacklist, minimum word count or fixed paragraph
formula. Keep established abbreviations in Chinese when normal for the field. A style
pass may not strengthen evidence or erase inconvenient results to sound more confident.

For mathematics, freeze the actual statement, distinguish identity/definition/proposition,
state assumptions and limits, and use a common symbol register. Preserve an exact formula
during translation and prose-only edits; documented scientific corrections use the
technical review path. Fit long equations by meaningful line breaks, not tiny type or
one operator per line. A longer derivation belongs only where it changes interpretation.

## 8. Give each figure and table a job

Use an evidence matrix for many comparable studies; do not imply a numerical ranking
when tasks, units or testing protocols differ. Real quantitative figures require genuine
data, units, conditions and source provenance. Label analytical illustrations as such.

Use editable figure specifications for relationships and workflows, semantic colors,
explicit connections and integrated a–d panels where useful. Inspect the rendered figure
and every panel at its final physical size. Apply the user's single-column/area preference
and concise captions. Remove an uninformative figure rather than add decorative complexity.
Fix the specification/source and regenerate; don't patch a stale raster independently.

Compilation success is separate from page layout, scientific visual correctness,
citation ordering, math readability and bilingual consistency. Check the actual entry
TeX and PDF to prevent delivery of an obsolete successful build. Preserve the complete
previous bilingual pair until the verified replacement qualifies under retention policy.

## 9. Reuse research memory without poisoning it

Reuse the existing study registry, claim matrix, issue ledger and run logs; do not create
a duplicate wiki by default. Link studies → facts → claims → sections and record supports,
contradicts, qualifies and derived-from relationships where they change a decision.
Every reusable note keeps its source and status: reported, inferred, proposed or unresolved.
Keep failed strategies with their reason so a later run does not repeat them. Model summaries,
review comments and successful compiler logs do not become primary evidence by repetition.

## 10. Improve the workflow from observed bottlenecks

Name the current bottleneck in one sentence, with log evidence: retrieval, request latency,
truncation, schema repair, repeated scientific rejection, low-information prose or layout.
Compare against a fixed small benchmark of representative units before changing prompts.
Keep a known-good baseline. Measure output validity, preserved facts/math, reviewer blockers,
input/output usage when returned, repeated calls and elapsed time; don't optimize speed alone.

Change the smallest mechanism that addresses the observed failure. Test interruption,
resume and regression paths; inspect a real output. Independent review evaluates the actual
diff and evidence. Keep improvements, revert regressions, record failed hypotheses. Do not
let the workflow rewrite its own acceptance rules to declare itself successful.
Apply existing session authorization; do not add a new permission ritual for routine local
fixes. Preserve current provider restrictions and the authorized delivery conditions.

## Adaptation boundaries

The useful ARIS patterns above are translated into review-writing tasks. We intentionally
do not inherit its model names/effort tiers, score-based stopping thresholds, GPU rentals,
mandatory experiment/ablation counts, minimum page lengths, Bash-only helpers, or a promise
of submission readiness. No new service, account, key, subscription or notification channel
is required. Existing math, evidence, source-preservation and account-cycle invariants remain.

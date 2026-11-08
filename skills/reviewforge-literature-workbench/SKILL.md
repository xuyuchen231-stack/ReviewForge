---
name: reviewforge-literature-workbench
description: "Plan, research, synthesize, draft, critique, and revise a scientific literature review from a topic or existing manuscript. Use for narrative, scoping, systematic, and evidence reviews; literature mapping; claim-to-source audits; citation verification; review restructuring; bilingual manuscript preparation; and publication-oriented revision."
---

# ReviewForge Literature Workbench

Turn a research question, literature corpus, or weak manuscript into a traceable scientific review. Work from research design through a coherent draft and independent audit. Optimize for evidence quality and useful synthesis; never imply that automation guarantees acceptance or replaces expert judgment.

## Start and choose the review mode

1. Inventory the user's files and identify the topic, intended contribution, target audience or journal, language, output format, and any existing manuscript or bibliography.
2. If the user gives a topic but not a framework, propose a scope and review mode from the evidence and proceed with clearly stated assumptions. Ask only when a missing decision would materially change the included evidence or requested deliverable.
3. Select one mode:
   - **Narrative/critical review**: organize and critically synthesize a field; use transparent, proportionate search documentation without forcing a PRISMA workflow.
   - **Scoping review**: map concepts, evidence types, and coverage; use a recognized reporting framework when appropriate.
   - **Systematic review**: prerecord or document eligibility criteria, reproducible searches, screening decisions, and the applicable reporting standard. Use PRISMA only when the review design warrants it.
   - **Meta-analysis**: require sufficiently comparable outcomes and designs, verified numerical data, and an explicit statistical method. Do not derive pooled estimates from narrative summaries.
4. Establish explicit inclusion/exclusion criteria, time range, organism/population/system, methods, outcomes, and source types. Keep the scope revisable until search evidence is mapped.

## Research and source handling

1. Translate the question into distinct search axes: core concepts, synonyms, mechanisms/methods, operating or population conditions, outcomes, and known anchor works. Search more than one relevant source when tools allow; choose databases for the field rather than treating one index as exhaustive.
2. Record the query, source/database, date, filters, result count when available, and retrieval failures. Distinguish a broad web search from a database-complete search.
3. Deduplicate by DOI or stable identifier first, then normalized title and author/year. Flag uncertain matches; do not silently merge distinct versions or studies.
4. Verify bibliographic identity using authoritative metadata (publisher record, Crossref, PubMed, arXiv, or another suitable registry). A valid DOI or abstract verifies identity/metadata only; it does not establish that the source supports a manuscript claim.
5. Retrieve and inspect full text where lawfully accessible. Use metadata/abstract-only records for discovery and mark their evidence depth. Never claim to have read an inaccessible paper. For PDFs, distinguish extracted text from OCR and flag tables/figures whose values were not directly readable.
6. Use citation chaining selectively: inspect references of key reviews and forward citations of seminal or conflicting primary studies. Use citation counts as discovery signals, never as evidence quality.
7. Classify each source (primary study, review, method paper, dataset, guideline, commentary, preprint) and assign its role in the argument. Prefer primary evidence for empirical claims; use reviews to map debates and prior syntheses.

## Build the evidence base before drafting

Create a claim-to-evidence ledger before writing substantive sections. For every important empirical or comparative claim, capture:

- claim in neutral language;
- source identity and stable locator (DOI/URL plus page, section, table, or figure when available);
- exact short excerpt or faithful data record supporting it;
- study/system, conditions, methods, measured outcomes, and relevant numbers with units;
- whether the support comes from full text, abstract, or metadata only;
- limitations, conflicting evidence, and verification status;
- intended manuscript section and citation key.

Use `references/evidence-ledger.md` as the project table schema and verification rules. Select the review-mode safeguards in `references/review-modes.md` before screening or synthesis. For fermentation dynamic-prediction topics, use `references/fermentation-dynamic-prediction.md` as the comparison-field checklist.

For each study, extract only fields relevant to the review question: question, model/system, design, inputs/conditions, methods, comparator, validation design, measured outcomes, key result, uncertainty/limitations, and relevance. Use null/unknown for missing values. Separate author interpretation from measured results. Keep versions, corrections, and retractions visible.

Assess study quality using criteria suited to the design and field. Do not apply clinical risk-of-bias tools to unrelated engineering or biological process studies. Do not convert heterogeneous studies into an unsupported numeric consensus score. When evidence conflicts, compare system, operating conditions, definitions, measurement methods, validation split, sample size, and study quality before interpreting the disagreement.

## Map prior reviews, novelty, and the argument

1. Locate recent and authoritative reviews on the same or adjacent questions. Compare their scope, cutoff date, organizing logic, evidence base, unresolved disagreements, and stated limitations.
2. Define the new review's contribution in one testable sentence. Do not label a review novel solely because it is newer, longer, bilingual, or has more references.
3. Build a thematic outline around explanatory questions and comparisons, not a sequence of paper summaries. For each section specify its claim, evidence clusters, disagreements, transition, and implication.
4. Identify gaps only relative to the documented search and corpus. A keyword absence or a single database search is not proof that no studies exist. Search alternative terminology and neighboring fields before making an absence claim.
5. Make a synthesis map that connects evidence to the review's thesis. Separate established findings, context-dependent findings, unresolved questions, and hypotheses.

## Draft and revise

1. Draft one coherent section at a time from the approved argument map and evidence ledger. Each paragraph should make a clear point, compare or explain evidence, state relevant conditions, and lead to the next point.
2. Place citations next to the specific claims they support. Preserve source-specific numbers, units, terminology, and uncertainty. Do not pad references or add citations merely to reach a count.
3. Write limitations as concise scientific analysis of evidence boundaries. Keep tool limitations, search failures, and workflow notes in the audit report, not in manuscript prose. Avoid defensive disclaimers and self-justifying language.
4. After each section, independently review factual support, synthesis depth, alternative explanations, overclaiming, paragraph logic, terminology, and citation placement. Revise documented issues and recheck the changed claims.
5. Run a cross-section pass for consistent definitions, scope, causal language, abbreviations, figure/table callouts, and repeated or contradictory claims.
6. If using a journal target, inspect its current author instructions from an official source. Treat patterns from benchmark articles as editorial examples, not formal requirements.

## Quality gates

Do not mark a manuscript claim verified unless its source and location are inspectable and semantically support it. Maintain these statuses: `verified-full-text`, `verified-abstract-only`, `metadata-only`, `conflicted`, `unsupported`, or `not-checked`.

Before finalizing, audit:

- every in-text citation resolves to one reference and every reference is cited;
- bibliographic fields and identifiers agree with authoritative metadata;
- empirical claims, quoted values, units, sample sizes, and comparisons trace to the source;
- review coverage matches the declared scope and search record;
- contradictions, limitations, and uncertain claims remain visible;
- tables and figures summarize the reviewed evidence accurately and add analytical value;
- manuscript language contains no fabricated sources, access claims, numerical results, or journal rules;
- original files are preserved and changes are reviewable.

Use a transparent section rubric when scoring is useful. Score named criteria (scope, evidence coverage, synthesis, critical analysis, logic, citation integrity, writing, and presentation); show criterion scores and concrete reasons. A score is a revision aid, not a publication-readiness probability.

## Deliverables

Choose outputs that fit the user's request and available files. A full project normally contains:

- revised manuscript and untouched original snapshot;
- search strategy and retrieval log;
- deduplicated source library or bibliography;
- claim-to-evidence ledger and study extraction table;
- novelty/scope map and review outline;
- independent review report, revision log, and unresolved-item list;
- final human verification checklist.

For LaTeX projects, preserve the user's macros, labels, citations, figures, tables, and source layout. Compile only when the necessary tools are available; report actual build status. Never describe a source file as a generated PDF unless compilation succeeded. Do not overwrite the master manuscript without explicit authorization. Publication, public upload, journal submission, or external sharing requires the user's authorization.

## User-specific profile: fermentation and dynamic prediction

Apply this profile when the topic concerns fermentation digital twins, hybrid bioprocess models, or the user's established review on prediction under changing operating conditions. Keep the core question centered on what happens after feeds, induction, temperature, or other process settings change, rather than fitting historical trajectories alone.

- Distinguish mechanistic, data-driven, and hybrid approaches; within hybrid methods distinguish rate learning, parameter learning, state correction, output-residual correction, and coupled architectures.
- Separate trajectory fitting, state estimation, interpolation, and genuinely prospective prediction under unseen batches or operating policies.
- Compare inputs, initialization, measurements, constraints, mass-balance consistency, validation split, operating-policy novelty, uncertainty, and transfer across batches.
- Address non-uniform mass distribution and the gap between mechanistic equations and observed reaction behavior when supported by sources.
- Organize around methodological choices, evidence quality, case comparisons, model-selection guidance, and evaluation benchmarks; use compact tables and original, interpretable figures.
- For the user's bilingual manuscript workflow, maintain aligned English and Chinese arguments, terminology, figure/table references, and cited works. The user's prior target was at least 60 distinct works actually cited in each language; treat this as a project target only when that bilingual manuscript is active, and report any shortfall honestly.
- Keep scientific limitations in the article as specific, evidence-based analysis. Keep process warnings and audit details outside the manuscript.

## Operating limits

- Search and extraction tools vary by environment. Use the tools actually available, preserve provenance, and state what was not retrieved.
- Search scripts or APIs from other skill projects are optional adapters, not guaranteed dependencies. Do not install packages or execute downloaded code without a clear need and user authorization.
- A single agent run can produce a complete draft and audit bundle, but source access, domain expertise, and human decisions still bound the claims that can be made.
- Do not embed API keys, access tokens, or personal credentials in this skill or its outputs.

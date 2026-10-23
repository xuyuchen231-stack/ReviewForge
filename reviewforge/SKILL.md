---
name: reviewforge
description: Research, critique, and revise scientific review articles through authoritative-review benchmarking, evidence-backed literature synthesis, iterative peer review, citation audits, and controlled manuscript revision. Use for academic review manuscripts, Q1 journal preparation, review-paper quality checks, and supervised or overnight revision workflows.
---

# ReviewForge

Use this skill for scientific review articles. Preserve scientific meaning and trace every important empirical claim to an inspectable primary source. Never invent a citation, DOI, study result, or journal standard.

## Workflow
1. Define review question, scope, target journals, intended contribution, and explicit exclusions. Request manuscript and literature evidence when absent.
2. Study authoritative reviews in the same field: compare how they establish scope, organize competing methods, synthesize disagreements, evaluate evidence, and justify open questions. Distinguish editorial patterns from actual journal requirements. See `references/benchmark.md`.
3. Build a claim-to-evidence matrix before revising: claim, source identity, exact supporting excerpt and location, study limitations, and verification status. Follow `references/evidence.md`.
4. Review independently for novelty relative to existing reviews, synthesis vs listing, methodological validity, limitations, research gaps, and scholarly language. See `references/review.md`.
5. Revise one coherent section at a time. Preserve citations and quantitative details; clearly label interpretations and hypotheses. Prioritize substantive synthesis over cosmetic edits.
6. Re-audit every modified empirical claim and every newly introduced citation; reject or quarantine unsupported claims. Report unresolved items without presenting them as verified.
7. Accept only evidence-passing revisions that address documented problems. Keep a revision log and best-known version; never silently overwrite the original.
8. For overnight execution, use the separate ReviewForge Runtime application. A ChatGPT Skill alone does not run for nine hours unattended.

## Deliverables
- Revised manuscript and original snapshot
- Claim/evidence ledger with unresolved items
- Review report (major/minor concerns) and revision rationale
- Change history and final human-verification checklist

## Specialization
For fermentation hybrid-modeling reviews, distinguish in-distribution trajectory fitting from prediction under unseen feeding/induction policies; compare rate learning, parameter learning, state corrections and output residuals using measured inputs, initialization, material-balance constraints and cross-condition validation.

## Guardrails
- A DOI lookup proves bibliographic identity, not scientific support.
- Exact local excerpts provide inspectable anchors, but semantic entailment requires expert review; model judgments are provisional.
- Do not fabricate access to paywalled sources or claim journal acceptance likelihood.
- Require human approval before publication, external uploading, or replacing a master manuscript.

## Manuscript language policy

Write publication-ready scholarly prose. Remove defensive disclaimers, apologies, self-justifying commentary, writing-process notes, and generic caveats from the manuscript. Retain meaningful limitations and uncertainty as concise, specific scientific analysis supported by evidence. Keep evidence warnings, review decisions and tool limitations in separate audit reports, never in the article body. Use the project's configured writer and reviewer models; keep provider/model choices in runtime configuration. Never embed API secrets in a skill.

## ReviewForge v4 + Light-skills workflow integration

For a Windows local research-review run, use the separately distributed ReviewForge v4 Runtime. It retains v3 configuration and starts through `start_review_v4_9h.bat` after `setup_secret.bat`, `check_connection.bat`, and import of the complete manuscript as `workspace/original.tex`. Use `resume_review_v4.bat` to resume.

### Stage contracts

1. **File intake / continuity**: inventory the author's `.tex` file, `.bib` database, original figure files and styles; hash the original; protect it from overwrite. Learn from `light-file-reading`, `light-memory-pm`, and `light-orchestrator`.
2. **Literature map**: search multiple thematic axes through OpenAlex, verify DOI registrations with Crossref, de-duplicate records, and preserve search queries, failures and dates. Learn from `light-literature-search`. Metadata verification is not content verification.
3. **Argument and critical synthesis**: differentiate new operating-policy validation from fitting or state-estimation claims; compare rate/parameter/residual approaches. Borrow claim-evidence and overclaim gates from `light-paper-writing`, review criticality from `light-review-rebuttal`, and integrity rules from `light-research-ethics`.
4. **Citation and evidence**: count distinct citekeys actually present in the manuscript, not library entries. Prevent fabricated references and distinguish registered DOI metadata from verified scientific support. Learn from `light-citation`.
5. **Visual and bilingual consistency**: preserve equation commands, figure/table bodies, labels and citations; compare Chinese and English citekeys and terminology. Learn from `light-figure` and `light-consistency`.
6. **PDF build**: use XeLaTeX/latexmk if available, report missing tools and failed compilation accurately, keep logs and PDFs. Learn from `light-typesetting`.
7. **Readiness**: an output file is not a publication-readiness verdict. Human expert review and original-article checking remain necessary; journal selection requires the author's decision. Learn from `light-venue-matching`.

Repository: https://github.com/Light0305/Light-skills, MIT license, copyright 2026 Light0305. Adapt workflow principles; do not claim full native Light 23-skill integration. See the Runtime `LIGHT_INTEGRATION.md` and `THIRD_PARTY_NOTICES.txt`.

### Manuscript style policy

Never include writing-process commentary, defensive disclaimers, self-justification, or tool limitations in the academic article. State scientific uncertainty through evidence-calibrated causal and methodological analysis. Keep verification caveats and workflow faults in a separate audit report, not in journal prose.

### Output readiness rules

Deliver the English and Chinese XeLaTeX source, actual generated PDFs only when compilation succeeded, BibTeX database, literature trace, review log, and final audit. If 60 distinct works are not actually cited and registered, report the shortfall; never manufacture citations to satisfy a numerical target. Preserve source title, numbers, figures, and author control of the master document.

## v4.1: evidence and delivery contracts

- **Translation:** translate bounded prose units with protected TeX/math/citation tokens.
  Include title, abstract, headings, captions and table prose. Retry failed units and
  persist successful units; never count retained English as completed Chinese.
  Translate from the current English source, preserve class options, and use the
  project's terminology glossary. Text embedded in images/TikZ needs a separate
  figure edit and visual check; do not claim it was translated by the prose pipeline.
- **Evidence:** give writer and reviewer the same source excerpts, locations,
  limitations and verification status. Metadata is a discovery aid. A missing
  source anchor is an unresolved evidence task, not permission to invent support.
  Changing the evidence ledger invalidates cached model revisions.
- **Coverage:** organize evidence around the review's questions. Record supporting
  studies, counterevidence searches (including searches yielding no counterevidence),
  and unresolved conditions in `coverage_matrix.json`. Prioritize these gaps when
  adding literature; numerical targets are configurable project requirements.
- **Figures:** first specify the question answered and evidence sources; then
  decide retain/redraw/remove. Inspect scientific meaning, caption, abbreviations,
  and readability at final column width. Use editable scientific plotting/vector
  sources for evidence figures. An inventory is not a completed redesign.
- **Revision acceptance:** require documented issue resolution without new major
  or unsupported-claim problems. Model-score increases alone cannot accept changes.
- **Delivery:** distinguish compiler PASS, layout PASS, rendered previews and
  actual visual review. Inspect all rendered pages, particularly equations and
  tables. Bind visual approval to the exact PDF hash and reviewed page list.
  Missing previews, overflow or unresolved references remain delivery blockers.
  These technical checks do not certify scientific validity or journal readiness.

### Revision modes

The default runtime revises within existing top-level sections. For an inadequate
outline, first propose a topic-led structure and map old paragraphs, evidence,
equations and figures to their destinations. Review that mapping before producing
a separate structural candidate. The runtime `plan` command proposes a structure;
`run` does not automatically execute a whole-manuscript restructure. Never describe
conservative section editing as structural rewriting.

See `reviewforge-runtime/README_V4_1_ZH.md` in the repository for schemas and commands.

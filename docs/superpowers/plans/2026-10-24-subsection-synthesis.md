# Subsection synthesis implementation plan

> For agentic workers: use executing-plans to implement this plan task by task.

**Goal:** Replace definition-led expansion with question-led, source-bounded, whole-subsection synthesis.

**Architecture:** Keep essential routing in the skill; put detailed writing and evidence contracts in references. Add an independent opt-in runtime pipeline that scaffolds subsection plans, validates study records, drafts coherent units and requires structured whole-unit review before saving accepted candidates. Never migrate a live legacy checkpoint or overwrite its master manuscript.

**Tech stack:** Python standard library, existing compatible API and TeX/evidence gates, Markdown skill references, unittest.

**Spec:** Six user-approved improvements: argument design, problem-led comparisons, whole-subsection context, study comparison records, depth rejection criteria, representative sample calibration.

## Constraints

- No word-count or citation-count threshold proves depth.
- Unknown methods remain unknown; abstracts cannot establish unreported procedures.
- Citation preservation, source anchors and scientific entailment are distinct gates.
- User approval of a sample is distinct from model review; record it explicitly.
- Generated drafts and review reports stay separate from original and active manuscript.
- Keep API credentials outside repository and generated artifacts.

## Tasks

- [x] Baseline pressure scenario: inspect what permits textbook-like subsections (delegated skill test).
- [x] Write tests for thin/no-plan drafts, evidence-access restrictions, hash-bound reviews, partial revision retention, and unchanged masters.
- [x] Implement synthesis_pipeline.py: init/audit/revise, source digest, coherent units, evidence context, study provenance, strict review and sample gate.
- [x] Update SKILL.md and add detailed argument, comparison, rubric, calibration and usage references.
- [x] Run behavioral skill test and runtime regression suite; fix findings.
- [x] Sync installed skill and deliver Chinese usage guide and limitations; publish the verified source with this plan.

## Review findings and rulings

- Baseline skill expressed synthesis intent but lacked per-unit argument, comparison and depth-review artifacts; a definition+equation subsection could evade a weak review.
- Independent review found and fixes now cover: unchecked non-axis fields; stale calibrated samples; reviewer-outage draft loss; best-version overwrite; unresolved major issue IDs within and across invocations.
- Ruling: use a separate candidate pipeline instead of mutating a live legacy checkpoint. User approval covers implementation of the six improvements, not approval of an unseen writing sample.
- Ruling: local artifact checks and model review cannot certify semantic entailment or author satisfaction. No production manuscript or model-generated sample is labeled complete by this upgrade.
- Validation: 69 runtime tests plus 11 quality-system tests passed; skill format validation passed; CLI init/audit smoke confirmed incomplete-plan rejection and master preservation. Installed skill matches repository source; deliverable ZIP integrity checked. No manuscript rewrite/API call performed for this upgrade.

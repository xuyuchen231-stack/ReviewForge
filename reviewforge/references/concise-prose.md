# Concise scientific synthesis

Apply to drafting and revision when paragraphs repeat conclusions or use abstract labels in place
of substantive comparisons. Keep scientific depth in findings and reasoning, not in word counts.

- Give each paragraph a necessary job: a supported finding, a comparison, an analytical step,
  a needed definition, a scoped interpretation or a concrete proposal. Do not impose every job
  on every paragraph, or require a summary and caveat at every ending.
- State a central distinction once. Later mentions need a new result, condition or consequence.
  Otherwise merge them or refer back. Assign definitions, empirical evidence, identifiability,
  revision decisions and validation protocols distinct places in the outline.
- Use the actual model, measured quantity, operation, split and result as grammatical subjects.
  Preserve standard terminology; explain or remove an invented label that adds no useful concept.
  Treat word-pattern lists as contextual hints, not forbidden vocabulary or authorship detection.
- Delete sentences that add no scientific information or reasoning. Preserve necessary scope,
  uncertainty, negative findings, numerical context, formulas and counterevidence. Do not invent
  data to make a passage look specific or turn cautious conclusions into stronger claims.
- Word budgets are soft upper guides. Do not pad to minimum lengths or mechanically cut to a
  percentage. Reject a long generic paragraph when it contributes less than a short specific one.

The runtime shares these instructions through `prose_quality.py` across synthesis, major revision
and editorial refinement. Existing review calls assess nonredundant argument, concrete language
and paragraph information gain; no extra stylistic model loop is needed. Similarity diagnostics
identify exact repeated propositions, similar prose with unchanged numerical context and repeated
meta-commentary. They are advisory: a reviewer must examine their actual context before editing.
No diagnostics automatically delete source content, equations, or different quantitative results.

## Findings from the manuscript audit

Borrow the main-text discipline and reverse-outline checks from `nature-writing`, and the
fact-preserving editing constraints from `humanizer-zh`. Use rhythm-refinement advice only after
argument structure is sound; do not impose random sentence lengths or a word blacklist.

Before accepting a section, write its paragraph messages internally and inspect their sequence.
For a repeated claim, identify whether each appearance introduces, demonstrates, interprets or
synthesizes it. A changed example without a changed inference may still be redundant. Every
new technical qualification requires a placement decision and a deletion check elsewhere.

Keep central evidence and conclusion-changing limitations in the main text. Move traceability
detail, repeated access bookkeeping and extended reconciliation to the matrix or supplement.
Do not explain an explanation unless that reasoning is itself necessary to the central argument.

Write the conclusion from the established findings of the whole new manuscript, not from the
old conclusion's locally supplied pair of papers. For each takeaway retain the minimum decisive
evidence and its material boundary. A mathematical example earns its place by changing a modeling
judgment, not by making the prose look rigorous. Keep physical balance terms, training objectives,
constraints and numerical procedures conceptually distinct when editing terminology.

## Executable paragraph review

The major-revision runtime supplies immutable paragraph IDs to the existing independent section
review. Every prose paragraph receives a primary function, actual message, contribution, placement
and keep/revise/merge/move/delete decision. A section cannot pass with omitted paragraphs or with
outstanding relocation/revision requests, even when high-level checks are all positive. Headings,
equation-only blocks and figure/table-only blocks are not forced into prose templates.

Accepted paragraph messages are passed to later sections to check whether a repeated claim now
performs a different useful function. This is an internal audit, not text to insert into the paper.
Requested relocations preserve the original wording and citation context in an internal log; the
log does not constitute a submission-ready supplementary note or new research evidence.

Candidates are checkpointed before review. A failed review request resumes with the same saved
candidate; missing review fields trigger bounded reviewer-only recovery. Genuine content rejection
goes back to the writer with paragraph-specific feedback. Do not equate this coverage with proof
of scientific correctness or author approval.

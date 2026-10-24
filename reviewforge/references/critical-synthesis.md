# Designing a critical review subsection

Read this when drafting substantive review prose, rebuilding a thin section, or
deciding whether a heading deserves its own subsection.

## 1. Define the intellectual work

A core subsection answers a question the reader cannot resolve from a definition.
Write its question before choosing the heading. Examples for hybrid modeling:

- When does learning a variable kinetic parameter add information beyond refitting
  a constant parameter, and what validation distinguishes those cases?
- Which measurements make a learned rate usable for a future operating-policy
  prediction rather than only a reconstruction of an observed trajectory?
- When do different hybrid formulations disagree because of architecture, data,
  initialization, solver settings, or the prediction task?

These are examples of review questions, not established findings. Adapt them to
the actual evidence. Do not force every research field into fermentation terminology.

For each unit record:

1. **Question:** one scientific decision, ambiguity or explanatory problem.
2. **Thesis:** a provisional answer to test against the literature, not a predetermined
   claim every study must support.
3. **Comparative axes:** dimensions that discriminate the methods for that question.
4. **Evidence clusters:** agreements, contrasts and observations that qualify the thesis.
5. **Paragraph plan:** what each paragraph contributes and which sources constrain it.
6. **Synthesis:** the inference readers gain from considering the studies together.
7. **Boundary:** which task, domain, measurement conditions and validation limit it.
8. **Open question:** a testable unresolved distinction arising from that comparison.

Do not fill these with synonyms for the heading. “Parameter learning is important”
is not a thesis; “more experiments are needed” is not a discriminating open question.

## 2. Distinguish subsection functions

- **Core synthesis:** needs evidence-based comparison and a bounded judgment.
- **Mechanistic foundation:** can be primarily conceptual if necessary for the later
  comparison. Explain the modeling choice it enables and cross-link its later use.
  Do not pretend an equation is empirical validation.
- **Bridge/transition:** may be short. State its transition function; do not invent
  literature volume to satisfy a size rule.
- **Case study:** a single study may warrant space if its detailed analysis answers
  the review question. Explain why wider comparison is unavailable or inappropriate.

In the current runtime use `kind: core` for substantive units, including mechanistic
foundations/case studies with a genuine question and explicit sparse-evidence rationale.
Use `kind: bridge` only for actual transitions and document `bridge_reason`.
This exemption does not waive evidence requirements for empirical statements.

## 3. Build comparisons before paragraphs

Arrange studies by dimensions, not publication year unless chronology explains
the scientific development. A useful comparison distinguishes:

- what was actually changed in the model;
- the information available during fitting and prediction;
- the task and conditions under which the claimed benefit was tested;
- the comparator and opportunity for recalibration/tuning;
- the result's scope and its plausible alternative explanations.

Comparable settings can support conditional contrasts. Different organisms,
scales, assays, targets, metric definitions or holdouts can prevent direct ranking.
Explain this noncomparability and what can still be compared structurally.
Never calculate a pooled improvement from unrelated reported errors.

Do not force disagreement: concordant studies can support a conditional pattern.
An absence of opposing evidence is meaningful only with a documented search scope.
Do not call inaccessible details “missing from the paper.”

## 4. Paragraph functions, not a mandatory template

One possible progression is question → concrete constructions → comparative
evidence → explanatory analysis → limits and conclusion. Vary it to fit the argument.
Do not reproduce five identically structured paragraphs in every subsection.

An individual paragraph may:

- distinguish two often-conflated prediction tasks;
- compare how studies identify a learned quantity;
- explain why a reported contrast does or does not isolate the architecture;
- analyze a counterexample or a failed transfer;
- derive a bounded implication from several observations;
- specify the experiment that would distinguish competing explanations.

A paragraph should make an assessable point. Citation count and sentence length do
not establish this. Mechanism, derivation, equation interpretation and practical
consequences belong where they advance that point.

## 5. Example: from textbook passage to review argument

**Insufficient as a completed core subsection:**

> A known kinetic function can be retained while a network learns its parameters.
> This combines mechanistic knowledge with flexibility. [Equation follows.]

It defines an architecture but leaves unanswered what varies, what observations
identify it, and whether it improves the intended prediction relative to alternatives.

**Evidence-constrained design for a stronger subsection:**

- Distinguish constant-parameter recalibration, state-conditioned parameters and
  time-indexed parameter prediction; introduce the equation to locate these differences.
- Read study methods and identify the actual learned quantity. Shah 2022 can inform
  the sensitive/time-varying parameter case only after checking its plant-data validation.
  An ANN–Monod coupling in Winz is a different construction; do not label it the same
  approach merely because both combine equations and a network.
- Compare prediction-time inputs, baseline tuning and withheld runs if available.
  If those facts are inaccessible, leave that comparison open and seek the full text.
- Separate improved state prediction from unique physiological identification of a
  parameter. The latter needs its own evidence or a carefully labeled analysis.
- Conclude only what the examined studies establish; identify a controlled comparison
  needed to test benefits beyond recalibration.

This is an argument blueprint, not a submission-ready paragraph or an approved style
sample. Verify all case details in the local evidence before drafting.

## 6. Diagnose and repair common failures

| Failure | Repair | Evidence of repair |
|---|---|---|
| Definition + formula | Add the scientific choice, actual constructions and validation comparison, or merge as a foundation | Reader can state what distinction the subsection resolves |
| One paragraph per paper | Reorganize around shared questions/axes | At least one substantive relationship between studies is explained |
| Bundled citations | Attribute each source's exact role and shared inference | Sources support the sentence at its claimed scope |
| Generic limitations | Identify the relevant design/measurement condition and consequence | Limitation changes interpretation of a specific comparison |
| Causal speculation | Examine confounds and label hypotheses | Observed association is separated from an untested explanation |
| Repetitive headings | Merge using an old-to-new content map | No equation, figure, source or substantive claim disappears |
| Length inflation | Remove repeated definitions and substitute evidence-based reasoning | Added text changes the scientific understanding |

The target is useful intellectual coverage. Do not prescribe a universal word count,
number of paragraphs, number of studies or ratio of critical sentences.

# Whole-subsection review and sample calibration

## What must be judged

Every core unit receives a complete-unit review. For each criterion provide an
explanation and exact candidate passages; the runtime rejects missing/invented passages.

1. **Question answered:** does the subsection resolve its stated scientific question,
   rather than explain only the heading's terminology?
2. **Comparative synthesis:** are actual relationships between studies examined on
   relevant axes, with sparse literature explicitly justified when necessary?
3. **Explains differences:** are agreements/differences related to model assumptions,
   tasks, information, data and validation, without untested causal attribution?
4. **Evidence scope:** do source locations support the exact constructions/results,
   and are abstracts, missing access, future work and observed results kept distinct?
5. **Bounded conclusion:** does the final inference follow from the comparison,
   specify its limits, and lead to a discriminating unresolved question?

Do not score these by word count, number of citations, comparison keywords or
formula counts. Offline diagnostics can flag thin coverage but cannot certify depth.
An isolated definition or derivation may be appropriate in a foundation or bridge;
its declared role must explain why a full empirical comparison does not belong there.

## Rejection conditions

- A completed core subsection consists mainly of definitions, an equation and generic
  advantages, with no source-based comparative reasoning.
- Papers are presented consecutively without explaining their relationship.
- A citation bundle appears to support a field-wide frequency/consensus claim while
  individual records support only isolated cases.
- Better performance is attributed to architecture despite different data, tasks,
  tuning, measurement access or validation designs without addressing those differences.
- Specific splits, tests, quantitative effects or industrial/control demonstrations
  are inferred from titles, metadata or nonspecific abstract language.
- Limitations and future directions could be pasted unchanged into any subsection.
- The prose repeats the definition at its end rather than deriving a useful judgment.
- Empirical evidence and the review author's proposed framework are conflated.
- More words are added while existing unsupported claims or open major issues remain.

## Actionable review records

For each issue record its ID, exact passage/location, severity, reason, affected
source/field, required rereading or revision, and a concrete acceptance check.
Preserve those IDs when requesting repairs and show whether they were resolved.
Do not request “add more depth” without specifying the missing comparison or reasoning.

Structural/source-provenance checks run before substantive acceptance. A reviewer
must reject unsupported content even if the section reads persuasively. Conversely,
passing citation checks does not demonstrate synthesis. Keep a last-known version
and the rejected attempts; never label fallback original text as newly improved prose.

## Representative sample

Choose one central, difficult unit with several relevant constructions and meaningful
validation questions. Do not choose the easiest introduction as a quality benchmark.

Deliver together:

- the complete candidate, preferably English and a faithful Chinese reading version;
- the question/argument plan and comparison table;
- an explanation of what the comparison adds over the old passage;
- open evidence problems in a separate report;
- the model's structured depth review and exact candidate hash.

Ask about concrete properties of the sample: comparative specificity, sufficient
method detail, depth of reasoning, critical judgment, headings and reading flow.
Record changes the user requests. Approval of six design principles is not approval
of a sample that has not yet been read.

The runtime stores the last model-passing candidate and review in
`synthesis_candidates/accepted/`; separate run directories preserve all attempts.
Approval refers to those accepted files and is stored in `synthesis_plan.json.calibration`:

```json
{
  "approved": true,
  "approved_by": "user",
  "sample_sha256": "exact accepted sample hash",
  "review_sha256": "hash of its model-review JSON",
  "preferences": ["Concrete feedback actually given by the user"]
}
```

Set this only after actual approval of that version. It is a workflow record, not
an authentication mechanism. Recalibrate if the sample or its review changes.
Before reusing a sample against changed evidence/plans, recheck its applicability;
model review is never elevated to external peer review or expert verification.

## Manuscript-level acceptance

After units improve, evaluate contribution, ordering, consistent comparison axes,
redundant openings, compatible local conclusions, exceptions and remaining gaps.
Integrate candidates through an explicit content map and inspect the complete draft.
Rebuild and visually inspect the PDF, then update Chinese from the stabilized English.
Successful local reviews do not automatically justify a manuscript-level readiness claim.

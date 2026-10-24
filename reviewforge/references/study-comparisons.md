# Study comparison contract

Use `study_comparisons.json` alongside the claim/excerpt ledger. They serve different
purposes: a short ledger anchor traces a narrow claim; a comparison record captures
the study information needed for a particular synthesis. Neither certifies entailment.

## Record identity and access

Each study has a `citekey`, DOI/version when available, `source_type` and optionally
`source_text_file`, a UTF-8 text extraction inside the workspace. Valid source types:

- `full_text`: original full article or explicitly identified authorized manuscript;
- `full_text_excerpt`: only identified sections/pages inspected;
- `abstract_only`: original author abstract, with provider/location recorded.

Preserve preprint/accepted/final version distinctions. A whole PDF file existing on
disk does not mean every relevant method or supplement has been examined.

## Fields and status

For every axis used in a subsection comparison record:

```json
{
  "status": "supported",
  "value": "A precise, bounded summary of the observed study detail",
  "locator": "Methods section and page/table/figure identifier",
  "excerpt": "An exact short source passage"
}
```

Allowed statuses:

- `supported`: explicit source evidence at that location;
- `not_reported`: searched relevant accessible methods/results/supplements; describe
  the inspected scope and do not imply a stronger absence than justified;
- `not_accessible`: source or relevant section unavailable/not yet inspected;
- `not_applicable`: the axis does not apply; explain why.

For these last three statuses, put the explanation/search scope in `value`; do not
write an invented excerpt. Empty scaffold values are pending work, not completed
comparisons. The runtime checks status vocabulary and supported excerpts; an agent
must still evaluate the adequacy of absence/rationale statements.

## Reusable extraction axes

| Field | What to extract |
|---|---|
| `system_scale` | Organism/system, operation mode, laboratory/pilot/industrial scale |
| `prediction_task` | Reconstruction, interpolation, forecasting, counterfactual policy, control |
| `mechanistic_structure` | States, balances, fixed equations and retained assumptions |
| `learned_component` | Rate, parameter, residual, state correction or sensor output; exact insertion point |
| `conditioning_inputs` | Time/state/input/history signals; availability at prediction time |
| `observations` | Assays/sensors, frequency, preprocessing and measurement uncertainty |
| `training_objective` | Loss terms, parameter estimation strategy and numerical treatment |
| `constraints` | Conservation, positivity, bounds, yield or other enforced conditions |
| `sample_size` | Independent runs vs repeated observations; units of replication |
| `validation_split` | Run/time/reactor/scale split; tuning vs final-test use |
| `baseline_tuning` | Baseline recalibration, matching data/access and optimization opportunity |
| `quantitative_results` | Metric definition, units, task, uncertainty and actual comparator |
| `operating_changes` | Feed, induction, substrate, scale, transfer or other tested changes |
| `uncertainty` | Method, calibration and demonstrated coverage |
| `failure_modes` | Actual failed cases, admitted limitations and proposed future work |

Choose axes that answer the subsection question. Do not force an irrelevant field
to produce a comparison or mistake unfilled columns for paper defects.

## Abstract-only restrictions

An abstract can establish a specifically stated result. It cannot establish details
not stated there. For detailed fields such as a validation split or sample count,
the runtime requires `explicit_in_abstract: true` plus an exact matching passage.
This flag is an assertion to inspect, not proof by itself. A DOI/title and the phrase
“validated experimentally” cannot establish a whole-batch split, independent control
execution, equal tuning, or a specific numerical advantage.

Full-text access does not waive this rule: a source passage must support the actual
claim. A study that places optimal control in future work cannot support completed
prospective control. Keep conflicts visible in the audit and correct the prose.

## Cross-study inference

For important comparison statements record in the argument plan:

- contributing keys and field locations;
- whether the statement reports a result, draws an inference or proposes a test;
- the dimensions that are comparable;
- plausible confounds and conditions limiting the inference.

Different data/systems can inform architectural taxonomy while being unsuitable for
performance ranking. A mechanistic rationale may motivate a hypothesis without
demonstrating it. Do not make comparisons sound causal merely by adding “therefore.”

Never bulk-copy full articles into distributable skill examples. Local evidence
stays local; source provenance belongs in the user's evidence workspace.

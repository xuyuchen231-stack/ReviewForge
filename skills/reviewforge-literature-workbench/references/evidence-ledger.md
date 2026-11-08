# Evidence ledger template

Use one row per substantive claim or study result. Keep source-level extraction distinct from manuscript prose.

| Field | Record |
|---|---|
| Claim ID | Stable identifier used in notes and audits |
| Candidate claim | Concise, falsifiable statement |
| Source | Full citation, DOI/stable URL, version and publication status |
| Locator | Page, section, table, figure, supplement, or abstract |
| Evidence excerpt/data | Short exact excerpt or faithful transcription with units |
| Evidence depth | Full text / abstract only / metadata only |
| System and conditions | Organism, population, design, operating conditions, inputs |
| Method and comparator | What was done and what it was compared with |
| Result and uncertainty | Outcome, effect/value, units, uncertainty, sample size |
| Limitations | Source-specific limitations affecting interpretation |
| Relation to other sources | Agreement, conflict, extension, or replication |
| Manuscript location | Planned section/paragraph and citation key |
| Status | verified-full-text / verified-abstract-only / metadata-only / conflicted / unsupported / not-checked |
| Reviewer note | What still needs human inspection |

## Rules

- A DOI match verifies identity, not support for the claim.
- Do not quote or transcribe values from a figure as exact if they were visually estimated; label estimates and preserve the figure locator.
- If the source supports a narrower claim, narrow the manuscript claim.
- If sources conflict, retain both records and explain which conditions or methods differ.
- Never replace missing evidence with a plausible value or a secondary citation presented as primary evidence.

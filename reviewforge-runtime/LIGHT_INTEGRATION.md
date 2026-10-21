# Light-skills adaptation manifest

Source: https://github.com/Light0305/Light-skills (master branch, inspected 2026-10-21). License: MIT, copyright (c) 2026 Light0305. Repository README describes 23 skills. We inspected public skill guidance for the modules below; this runtime **adapts their workflow principles**, not their script implementations.

| Light module | ReviewForge v4 mapping | Implementation status |
|---|---|---|
| light-literature-search | multi-query OpenAlex search, DOI/Crossref metadata and search log | implemented (metadata tier only) |
| light-citation | DOI uniqueness, BibTeX, cited-key gate and metadata vs claim distinction | implemented (not full-text semantics) |
| light-paper-writing | claims must match available evidence, section-level substantive rewrites | editorial instruction implemented; no full claim registry |
| light-consistency | compare bilingual citekeys and original structural landmarks | limited deterministic checks |
| light-typesetting | latexmk/XeLaTeX compile with explicit failure status | implemented, environment dependent |
| light-figure | preserve user's existing figures/labels and reject lost elements | partial structure gate; no visual render QA |
| light-orchestrator | staged checkpoint, provenance and resume | implemented basic local checkpoints |
| light-memory-pm | persistent state and immutable input hash | implemented basic checkpoint |
| light-file-reading | original.tex and linked assets import | implemented TeX assets importer |
| light-review-rebuttal | separate reviewer pass and issue ledger | implemented per-section model review |
| light-research-ethics | no invented numerical or bibliographic claims; honesty flags | editorial constraints, partial machine gates |
| light-venue-matching | no journal selection or invented submission readiness | intentionally not implemented |

The source project's full advanced schemas, journal workflow and its broader scripts were not copied. No guarantee of feature parity with Light-skills. MIT license attribution included in `THIRD_PARTY_NOTICES.txt`.

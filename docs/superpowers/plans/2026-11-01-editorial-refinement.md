# Editorial refinement implementation plan

> Execution: use executing-plans inline, then one independent review. Preserve user-authorized scope and all immutable manuscript snapshots.

Goal: reduce repetitive audit commentary, improve scientific information density, and deliver a cleaned complete reference plus a separately condensed version.

Architecture: deterministic diagnostics and evidence appendix; a checkpointed editorial clean/condense stage with protected-content and model-review gates; source-only audit archives. No unexecuted numerical results enter prose. Existing scientific acceptance counts remain unchanged.

Stack: Python standard library, existing CompatibleAPI/checkpoint transport, Matplotlib for authored figure and synthetic benchmark modules, existing LaTeX export.

- [x] Audit repeated access language, notation roles and real equation references; export detailed and per-study evidence CSVs. Exact repeated sentences are detected; semantic repetition is assessed by editorial model review.
- [x] Update generation pressure toward direct evidence-calibrated writing without removing uncertainty or inferring authorship.
- [x] Add resumable clean/condense stages with source-addressed complete versions, internal raw snapshots, mathematical/environment/numeric protection and provisional semantic review.
- [x] Integrate opt-in end-of-run refinement, locally enabled after verification, with enforced build reserve and pending-writer-draft recovery.
- [x] Add role-aware notation passages and reference diagnostics. Current equation17 is a valid forward reference. No blind symbol substitution is performed.
- [x] Render taxonomy, locked protocol and M0–M4 conceptual diagrams; configure this user's local figure plan. Independent 11-figure, 83-page two-column export passed compilation/layout checks.
- [x] Execute separate synthetic fed-batch H1–H4 comparison with frozen splits, CSVs, metrics, curves, implementation archive and honest limitations. No fabricated PenSim/organism results enter the paper.
- [x] Verify faults and regression tests, real four-call paragraph route, independent review and installed skill validation. Whole-paper refinement has NOT been executed; 25–30 pages and final scientific quality remain unverified until that run completes.

Verification: Python3.10 233 core tests +11 quality tests passed; Python3.12 233 core tests passed with the optional NumPy test skipped locally. CI installs optional research dependencies to cover it. Independent review findings about display math, deadlines, mixed versions, narrative environments and comments were fixed with regressions. No remaining important issue was reported in the final focused review.

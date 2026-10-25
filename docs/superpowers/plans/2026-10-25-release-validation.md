# Runtime repair and release validation — 2026-10-25 (Pacific/Auckland)

The user requested local repairs and complete verification before another handoff. No installation package or user-operated test loop was used. Originals, source material, credentials, raw model responses and diagnostic manuscripts remain local and excluded from Git.

## Reproduced defects and fixes

- Reviewer input included multiple drafts, and a live reviewer criticized sentences from the original rather than the candidate. Review now has one draft target; source evidence, citation requirements and prior findings remain available.
- Whole-unit reasoning-model reviews exhausted the old output allowance. Reviewer output defaults to 12000, with bounded request/session deadlines and no false acceptance on empty output.
- Network timeouts and incomplete HTTP responses reused an account. They now advance the account for the next route without marking it depleted or applying the rate-limit cooldown. Model output exhaustion advances models; 429 retains the separate ten-hour cooldown policy.
- All supported citation commands now share one parser. Newly unclosed or mismatched environments fail locally; invalid cached candidates retain original text during assembly.
- Completed tasks with missing, stale or invalid accepted candidates now re-enter the queue on resume. Assembly and coherence use the same source/contract/candidate/structure validation, including corrupt metadata handling.
- Coherence response schema and quotations validate inside bounded local retries. Transport failure has one additional recovery attempt under the same remaining work budget; genuine scientific findings still require repair.
- Translation now reads the actual run glossary/topic. Explicit fermentation organism identifiers, including TeX-spaced Latin names, remain immutable; ordinary italic English cannot bypass translation checks.
- Inline bibliography author/year labels support textual citations. Missing entries require registered metadata; ambiguous manual dates are not guessed. Undefined author/year warnings block layout approval.
- Export-only layout recovery preserves all equations/citations while trying single-column output and, only for remaining vertical overflow of at most 3pt, a 3pt text-height adjustment. It archives the original export, records hashes and uses at most two recompilations. It never masks unresolved references or missing glyphs.
- Internal source offsets are rejected from narrative prose and retained in evidence records instead.

## Verification evidence

Local offline checks run on both Python 3.10 and Python 3.12, including the optional real PDF preview test. Independent read-only reviews found the reproduced defects, checked their repairs and did not authorize or fabricate manuscript acceptance. Windows/Python 3.12 and Ubuntu/Python 3.10 CI jobs also passed for the main hardening commit.

Live writing/review: the 19-study unit completed under the corrected budgets and passed the grounded review on its actual candidate. An additional real coherence diagnostic identified a genuine overclaim; the production scheduler in an isolated snapshot returned it to writing and obtained a passage-grounded review resolving the major issue. A second selected unit is also being repaired to remove internal locator annotations. Other units are explicitly not selected in this diagnostic, never marked completed.

Live delivery: the two-unit English-to-Chinese route resumed cached translations, generated Chinese, preserved citation keys and structure, and compiled both PDFs with layout PASS, zero unresolved references and zero missing glyphs. The full English manuscript, containing only the separately accepted replacements, also compiled with layout PASS after the recorded layout recovery. Representative English and Chinese pages were visually inspected; this is not expert approval, author calibration or submission readiness.

The final production-scheduler repair/coherence/assembly result and latest test counts will be recorded after that run finishes. No nine-hour production job has been started by this verification.

## Continued validation — 2026-10-26

The production scheduler repaired both selected units and passed their local grounded reviews. Its subsequent monolithic coherence request still failed on the provider, so that stage was replaced with complete overlapping unit windows bounded to 32000 text characters, followed by bounded global opening/conclusion excerpts. Successful batches have exact-input/model-policy caches; partial failures retain every known major finding, including multiple findings for one unit. Cache resume, long-unit coverage, later-batch failure and corrupt working-report regressions passed.

A live reasoning-effort probe accepted the documented low-effort parameter but DeepSeek still exhausted its 12000-token response allowance without an answer; the fallback MiMo returned a valid grounded result. Accordingly, coherence has its own configurable primary route (defaulting to the already configured writer), while local scientific reviews retain their configured reviewer. Actual models remain disclosed and no same-model check is represented as independent expert review. The optional DeepSeek effort control is a request parameter, not a guarantee of provider behavior. See the [DeepSeek thinking-mode documentation](https://api-docs.deepseek.com/guides/thinking_mode/) and [Token Harbor compatibility documentation](https://tokenharbor.ai/docs/api/curl).

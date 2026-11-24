# Active opening deduplication and capacity diagnostics

Owner main1bf0f64 logs establish three distinct failures: worker draft rejected by unchanged synthetic-fixture vocabulary validator; API provider returned400json_validate_failed; router was withheld by the local shared7200reservation ledger, previously mislabeled as model-validation failure.

This patch preserves the synchronous opening/chat design. No deferred generation, background scheduling, priority queue, reserved chat headroom, post-failure retry window, cached personalized prose or reduced independent-review evidence is introduced. The user explicitly rejected foundational changes on November24at18:21.

## Bug fixes

- One active per-user opening across API/worker uses an owner-token Redis lock around the bounded generation. A simultaneous duplicate returns without a second provider chain or extra UI notice. The active owner publishes the existing normal result. Release is compare-owner and cancellation-safe; failure/completion permits immediate retry. TTL is only a process-crash safety bound, caller deadline plus5seconds. Without configured Redis, only same-process protection exists. Configured Redis errors fail closed.
- SharedProviderBudgetError is now classified as local capacity with an honest operational notice, not invalid model routing. No cart/shopping action is claimed.
- The synthetic-fixture regex still rejects the same vocabulary, including negations. Safe diagnostics identify popularity/promotion/urgency/real_stock without logging prose. Writer instructions explicitly avoid those terms even when negated, retaining synthetic test selection disclosure and existing deterministic/independent review gates.
- Fixture eligibility remains APP_ENVdevelopment plus explicit AIRDELIVER_DEV_FIXTURES opt-in. Fixture rows remain tagged dev_fixture/fixture_in_stock, not real offers or production catalog. No source rows or labels are changed.

## Provider400 boundary

The same request-specific schema succeeded on worker before evidence rejection, so provider json_validate_failed alone does not establish invalid schema construction. No raw failed generated text is logged or retained. This patch does not claim to cure all provider constrained-generation failures or weaken strict schemas. Existing fail-closed400diagnostics remain. More live stage evidence is needed if400persists.

## Quota configuration

PROVIDER_TPM_BUDGET remains the existing configurable7200default, with actual-success reconciliation and estimated reservations. No account/provider quota change is made. A larger owner subscription requires matching the configured budget to its verified model quota, then recreating API/worker; it does not need a new orchestration design. Estimates are not exact tokenization. Concurrency outside this Redis/model namespace remains outside admission. The active-opening lock prevents concurrent duplicates, not a second deliberate opening after the first completed.

No provider calls, owner-machine execution, model activation, data deletion or held migration changes. CI tests remain orchestration/evidence enforcement, not live product comprehension or production acceptance. Canonical55live acceptance is unchanged.

Verification: split full suite first786passed20skipped, second821passed4skipped with two repeated compiler-setup tests, giving1605unique passing tests. Two further cancellation/owner-release and configured-lock-outage tests added and passed in final35-test focused run, giving1607unique tests exercised,24skipped. No external provider/model call. Provider400cause remains unresolved, not falsely marked fixed.

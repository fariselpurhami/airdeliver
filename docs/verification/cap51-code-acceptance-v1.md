# CAP-51: consultation, context and history code acceptance

Active caller inventory: NeuralCore staged informational consultations call the
shared per-target source answer; ordinary current-card advice calls
FreeLLMService.consult_catalog through the shared SalesResponse boundary. The
public consult_on_product wrapper accepts current catalog evidence and does not
reuse arbitrary chat history as policy/facts. handle_commerce_interaction cannot
republish incomplete or failed consultation cards. Retained NLU synthesis and
single-product answer call reviewed_legacy_answer, with current SQL card
rehydration, hard-brief extraction/review, source lookup or scoped fallback and
post-model current-card comparison. The original raw web consultation body stays
preserved but has no active application caller.

Recent customer-only context is intent reference, not product proof. Consented
SQL hints are owner-bound, opt-in, expiring and optional, never constraints or
hidden persona evidence. NeuralCore already rechecks recalled hints before
publication. The retained NLU synthesis, single-product and setup bridges now
also recheck after model work and before returning/publishing a personalized
answer. Revoked/expired/changed hints or recheck failure withhold the answer.
This closes the remaining retained-caller revocation race without widening
collection, restoring hidden profiles or changing consent policy.

Actual SQL tests revoke consent during source/catalog/setup model calls and
assert personalized copy/source answer is not published. Existing owner,
expiry, feature-off/revoked, customer-only history, source outage and scoped
fallback tests remain. All2156collected cases covered on disposable
PostgreSQL19/realRedis:1075passed/3skipped and1076passed/4skipped, two bootstrap
cases duplicated.15focused real-SQL hint/revocation cases pass. Model outputs
are controlled: no source entailment, useful language or real-model claim.
Code completion subject to exact-head scan, both storage jobs and merge.
Owner execution and live quality parked, no provider calls or spending.

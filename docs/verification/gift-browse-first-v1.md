# Owner gift browsing policy

Owner explicitly selected optionA on2026-11-24: budget+occasion without category
should show grounded cards across available categories, then one follow-up.
Previous clarification-only gift policy is superseded for this exact shape.
Missing/unresolved budget/currency or missing occasion still clarifies. Literal
category follow-up keeps existing category search, not cross-category browsing.
No category/taste inferred from gender, no claim the gift is ideal for recipient.

Query reads up to500current active/local-positive-stock rows in explicit currency
and price cap, with normal catalog eligibility/fixture opt-in. Round-robin across
actual returned categories, max5cards. Those are exploratory options, not model-
invented items. Hard required/excluded feature filters stay. If only one category
is eligible, no second category is invented. Bound500may miss categories later
in large catalogs; this is not exhaustive inventory or learned recommendation.

Existing shared model writer and independent review author prose using only
current cards and request_evidence.gift_browse. Exactly one question required.
CurrentSQL price/stock/spec row is re-read after model awaits; changes withhold
whole response. No cart mutation/payment/checkout. Budget is per alternative,
not a summed bundle or a spending authorization.

Tests use disposable PostgreSQL through actual writer/review/revalidation:
diverse categories, cap/currency/outofstock/demo rejection, unknown budget,
changed price during writer await and independent reviewer rejection. Controlled
responses are not live LLM quality proof. Actual English gift/cards flow still
needs owner screenshot after rollout. Canonical55liveacceptance unchanged.

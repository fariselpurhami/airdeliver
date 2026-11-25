# Whole-chain capacity acceptance, offline evidence

## Tested, not assumed

The test_whole_chain_capacity module builds actual router/writer/independent-review requests and uses real Redis admission at the unchanged7200rolling budget. It covers English, Arabic, full ten-message history, thirty-two large spec fields, unknown costs, artificial usage reconciliation and prior shared traffic. No provider call or real usage measurement occurs.

- Unknown-cost short English router and writer reservations consume enough budget that review is withheld. This is fail-closed, not a successfully completed shopping answer. No publication is allowed without review.
- Explicitly artificial400token usage for each completed call allows router/writer/review/next-router by reconciliation. This proves ledger mechanics only, not actual model efficiency.
- Prior5000token traffic from another call blocks a new router without erasing that existing usage or creating a failed reservation entry.
- Multilingual/history/large-spec fixtures are measured through the same builder and do not assert that everything fits. Actual chain stage/input/output details remain private.

34 actual Redis/PG boundary tests pass including existing shared admission, cooldown, unknown outcome, configured outage and structural diagnostics tests. No lower evidence/review quality, cap raise, model change, ten-card drop, history reduction or synchronous-flow redesign was used.

## Acceptance decision

The compact patches reduce overhead, but they cannot certify a fixed low rolling budget for large-volume deployment. In particular, a fail-closed ledger is not itself a good enough customer experience: withholding review prevents false advice but still interrupts a conversation. Do not mark capacity closed from these tests or patch counts.

Required next evidence is a bounded owner-approved live trace using numeric usage and safe structural categories, not raw prompts/customer data/provider failed generation. Need actual router+research+writer+review and follow-up costs, quota headers/unit and exact deployed model/plan limits. Then size the operational capacity and concurrency for the expected traffic without silently raising the current cap or weakening review. Those limits and production traffic are external facts, not values code can infer. Until measured, high-volume readiness and live400 resolution stay open. Independent offline commerce work can continue.

# CAP-07: homepage current-row/fallback code acceptance

Retained NLU personalized matrix calls get_fresh_homepage_matrix. The active
method now rehydrates index candidates through current SQL active/stock/price/
synthetic predicates and opening-card eligibility, removes duplicate/seen IDs,
and fills from filtered SQL when the index candidates are all seen, stale or
insufficient. It never recycles seen candidates to fill eight slots. Original
method remains dormant as _legacy_get_fresh_homepage_matrix. Tier is only a
fallback sort hint, not evidence of spending traits, value, trends or quality.

Candidate work is bounded to60 index IDs and60 SQL fallback rows, then8 results.
SQL eligibility precedes ordering/limit so a large synthetic/inactive prefix
cannot starve real eligible rows. Currency/finite-price card checks can withhold
rows in the bounded SQL sample; this is not exhaustive catalog ranking. Unknown
or deleted current cards are not rescued from stale index fields. Query and
shuffle are deterministic retrieval mechanics, never customer preference proof.
Invalid owner/seen shapes reject early; outage returns no candidates and caller
cancellation propagates. Existing downstream copy/review and freshness checks
remain necessary; this method is not final publication authority.

13 focused real PostgreSQL cases pass, including tier ordering, all-seen empty,
65 synthetic rows before real rows, stale stock, duplicate/seen-only index,
outage and cancellation. Existing opening-pool eligibility/nonce tests pass.
All2268collected covered on3fresh disposable PostgreSQL19/realRedis runs:
754passed2skipped,753passed3skipped,756passed2skipped,2bootstrap duplicates. Live usefulness, cold/warm
latency, real catalog/model/index profile and owner homepage receipts remain
unverified and parked. Code closure requires exact-head scan and both storage
jobs plus fast-forward. No provider or owner-machine actions.

# Separate memory lifecycle audit, decisions open

This is not CAP18/CAP30 code closure. Neither is promoted by the tests here.
Current implementation has several independent systems:

- Canonical SQL shopping-v1: explicit opt-in, color/material/style affirmative
  statements only,90-day eligibility, opt-out deletes these rows. Feature flag
  defaults off. Export/control UI explicitly excludes recent chat/orders/older
  memory. Consent generation and row lock guard late extraction/revoke races.
- Current HTTP session: authenticated owner plus hashed browser session ID,
 1-hour TTL and five turns. Context recheck prevents revoked saved hints being
  published. Current customer text wins over hints.
- Retained NLU recent chat: owner namespace,24-hour TTL and bounded history.
- Behavior event stream/active dimension/seen:24-hour lifetime, bounded packets.
  Ghost profile:1-hour TTL, exact artifact/source dimension and time validation.
- Retained DNA cache:5-minute TTL. Price-history:20values but no expiry.
- Confirmed displayed-product history has separate recency timestamps and TTL;
  candidate retrieval/model failure never earns displayed exposure.

The original owner direction requested lifelong customer personality/likes and
behavior. It has not been reconciled with the current narrower shopping policy.
Do not infer permission to expand collection or deletion. Open decisions:

1. Does shopping-memory opt-out remain shopping-v1 only, or also cover behavior,
   recent chat and shown-product history? Any new full-personalization reset
   needs named scope and pending queue/race handling, not just deleting one key.
2. What retention should price-history have, currently bounded20entries with no
   expiry? No arbitrary new TTL was installed.
3. Should session reset clear only conversation/cart, or also cancel pending
   orders as the retained old cart-clear handler does? Current reviewed chat
   clear explicitly promises no order cancellation. Do not silently choose.

Independent hardening limits price-history reads to20entries and rejects bad
owner IDs, negative/nonfinite/overflowed amounts before deriving a tier. This
changes no retention, opt-in scope, collection category or learned-model state.
Actual-model extraction quality and owner privacy policy remain unverified.

74 focused storage/lifecycle cases passed. All2284collected covered on fresh
PostgreSQL19/realRedis:759pass2skip,758pass3skip,762pass2skip with2bootstrap
duplicates. Code/whole counts remain17/20 and0/20, respectively.

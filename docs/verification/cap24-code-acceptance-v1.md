# CAP-24: four-role opening code acceptance

Opening retains synchronous generation, personal/bestseller/trending/deal role
order, independent role pools,10-card row cap, model writer plus independent
review, SQL freshness before each stream, and exposure after successful publish.
Empty roles are omitted, never filled from a different role; partial delivery
can occur and is not atomic. Row labels are internal selection roles, never
sales/popularity/trend/discount evidence. Current client uses90-second opening
request budget above the75-second server matrix deadline, no automatic retry,
and an explicit uncertain-completion notice on failed HTTP. Existing client
regressions cover this contract; no new browser receipt is claimed.

Nonce sorting every eligible catalog row is replaced by one filtered count and
an ID-ordered sampled page, combined with a ranked half-pool. Returned candidates
are bounded; count/offset/ranked sorting still depend on catalog size and are
not constant-time or measured production performance. Original full nonce-sort
method remains dormant. SQL active/stock/name/currency/synthetic/freshness rules
still precede selection; fixture opt-in is unchanged. Pool rotation can reach
outside the ranked top while preserving filters.

Exposure recording is now scheduled immediately after confirmed row publication,
before pacing delay. Cancellation in pacing no longer loses a displayed row's
seen record. Cancel before/failed publication never earns exposure. Existing
actual SQL/Redis tests cover ordered roles, empty-role omission, stale rows,
writer/review failures and serial model chains.38 focused cases pass, including
a cancellation-during-pacing regression. All2269collected covered on3fresh
disposable PostgreSQL19/realRedis runs754pass2skip,753pass3skip,757pass2skip
with2bootstrap duplicates.
Live opening quality, quota mixed-load latency and owner browser/runtime remain
unverified, parked. Code closure requires latest-head scan and both storage
jobs plus fast-forward. No live provider or owner actions.

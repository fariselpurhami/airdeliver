# Atomic cart snapshot updates

Adds Redis WATCH/MULTI snapshot comparison to existing AICartService add/remove writes and saved-list cleanup. Concurrently changed state is rejected instead of overwritten. No automatic retry that could duplicate a submitted mutation. Cache backends without the atomic primitive fail closed. Snapshot is a Pydantic private attribute, not exported cart data.

Real disposable Redis tests force two readers before competing writes, a clear between read and write, and a newer cart write during saved-list database commit. All three fail against the previous unconditional write/delete behavior. With the fix: full local PostgreSQL19/Redis suite 737 passed, 3 skipped, 20 existing warnings. Local broker acceptance remains skipped; CI supplies the real broker. No paid provider calls.

Scope: not all cart writers yet. Checkout price-refresh and payment-completion cart cleanup still use legacy writes/deletes. This does not claim exactly-once mutations, solve saved-list idempotency or DB/cache atomicity, guarantee UI event ordering, or provide a global cart revision protocol. Existing clear behavior and pending-order cancellation policy are unchanged. A stale operation can fail and requires an authoritative refresh before retrying.

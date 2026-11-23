# Same-ID receipt/cart read interleaving

A full real-store test pass exposed a race where the winner committed between
the loser's receipt GET and cart GET. The loser returned stale although its own
operation had committed. No duplicate mutation was observed, but correct replay
classification matters for safe caller recovery.

On cart mismatch, re-read the receipt before declaring stale. The deterministic
real Redis regression injects the winning commit at exactly this boundary and
covers matching and conflicting fingerprints. Full local suite: 838 passed,
4 skipped, 20 pre-existing warnings, real migrated PostgreSQL and Redis.
Redis retention/eviction limitations remain unchanged. This does not make Redis
receipts durable across server data loss.

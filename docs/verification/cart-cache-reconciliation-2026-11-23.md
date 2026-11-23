# Prepared SQL-derived cart cache repair

A separate `canonical_cart:v1:` namespace can be rebuilt only from canonical SQL.
It never imports Redis into SQL, never touches legacy ai_cart keys, and never
interprets a missing SQL row as an empty legacy cart. SQL read failures propagate.
Cache failures return an explicit unavailable outcome with the SQL snapshot.
Compare-and-set prevents stale repair from replacing a competing cache write.
Cached revision newer than the SQL read leads to retry, never overwrite.

This is not wired to customer traffic. Migration, import policy, cutover and
retention remain review decisions. No dual-write success/durability claim is
made. All returned cart data comes from SQL, not from potentially corrupt cache.
Malformed raw cache JSON yields cache_unavailable, rather than silent success.

Local tests use real migrated disposable PostgreSQL and real disposable Redis:
missing canonical data, missing cache, stale/semantically corrupt cache, complete
cache flush, newer-cache protection, competing publish CAS race and cache outage.
No deployment, vendor spend or production database changes.

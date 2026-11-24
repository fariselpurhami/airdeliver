# Direct catalog publication freshness

The no-target direct product-search and visual entrypoints previously hydrated catalog rows
before shared writer/review awaits, without the final row check already present
in staged/setup/gift adapters. It now rereads every returned card after those
awaits and withholds the response when current row identity/price/stock/spec or
hard-constraint eligibility differs. Relation is routing metadata, excluded from
value equality as in the staged path. Both paths use a shared final-read helper. The fresh read covers alternative cards,
not just the initial retrieval IDs. Existing provider flow, retrieval, quotas,
writer/reviewer and synchronous response remain unchanged.

Ten migrated PostgreSQL tests exercise successful publication plus price, stock,
spec and deletion changes committed from a second session during copy. Controlled
model outputs test publication boundaries, not language correctness or live data.
This is not atomic inventory reservation and cannot guarantee future stock.

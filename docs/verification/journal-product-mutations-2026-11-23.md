# Prepared canonical add/remove semantics

Canonical add/remove preserve cart limits, USD-only behavior, live catalog
validation and line price/name refresh. They lock canonical user state, reject
stale expected revisions and bind mutation IDs to operation parameters. Replay
needs no fresh catalog availability and returns the current cart rather than
reverting to the original outcome snapshot. Removal replay preserves later
readdition. No inventory reservation or new payment behavior is claimed.

Real PostgreSQL tests cover fresh price changes, replay after catalog inactivation,
conflicting payload, replay after readdition, stock/currency/activity rejection,
and competing independent transactions with different IDs at one revision.
Full local suite: 848 passed, 4 skipped, 20 existing warnings.
Prepared only: no traffic routing, migration application or deployment.

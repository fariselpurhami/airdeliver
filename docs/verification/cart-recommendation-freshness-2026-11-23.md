# Delayed recommendation freshness

Read-only cart recommendation worker now rechecks membership AFTER retrieval as
well as before. An add/remove reversed during search does not publish stale
advice. Current cart products, anchor and duplicate candidate IDs are omitted.
No cart writes, new product invention or compatibility claim is introduced.

New controlled-worker regressions cover both membership reversals and candidate
exclusion/deduplication. Full local suite 854 passed, 4 skipped, 20 existing
warnings, with real PostgreSQL/Redis boundaries in the suite. Actual current
user-stack search/card delivery is not proven. Event delivery remains best effort,
not a transactional outbox; relevance and technical compatibility remain unproven.
No provider calls, accounts, deployment or schema application.

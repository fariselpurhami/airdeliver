# Prepared canonical cart ordering

Canonical SQL cart journal now has a read-only revisioned envelope. No legacy
Redis import, empty-cart creation or traffic routing occurs through this read.
The UI accepts increasing safe-integer revisions, drops delayed/duplicate frames
and refuses unordered legacy rewind after a revisioned snapshot is accepted.
Legacy behavior remains available until a revisioned snapshot is seen. Ordering
state resets when connection auth token changes so a different account's smaller
revision is not blocked. Token rotation may conservatively reset the ordering
floor; no cross-session global ordering claim is made.

Local verification: 833 backend tests passed, 4 skipped, using real migrated
PostgreSQL and disposable Redis. Frontend 80 tests across 11 suites and typecheck
passed. This is a prepared protocol: active Redis cart emissions do not yet carry
canonical SQL revisions. Runtime cutover/migration remains held for review.

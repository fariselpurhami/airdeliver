# HTTP cart recommendation follow-up, 2026-11-23

## Scope and contract

The HTTP cart factory has no commerce engine, so the existing engine-only branch silently skipped recommendations. An acknowledged add/remove now optionally publishes a dedicated version-1 read-only recommendation event. It is not an add/remove command. The worker binds a separate quorum queue and calls the existing catalog-grounded bundle/alternative methods. No paid LLM copy call is needed. Existing engine-backed cart execution is preserved.

Producer waits at most one second with one publisher attempt. A failed optional publish does not turn a persisted cart into a failed mutation. This is best effort, not a transactional outbox guarantee. A delayed event is skipped if the anchor's current membership no longer matches the operation. Replayed events may repeat a suggestion but cannot replay a cart mutation.

Copy says related catalog items, not proven technical compatibility. Products remain subject to existing PostgreSQL hydration and availability/budget filters.

## Executed

- Full migrated disposable PostgreSQL 19 suite: 696 passed, 2 skipped, 20 existing warnings.
- Eleven new producer/consumer/schema tests: add/remove event shape, no event after failed persistence, broker outage preserves acknowledged cart, catalog-method routing, carousel shape, no cache write/delete from consumer, delayed event suppression, malformed version/IDs/operation rejection.
- Existing real PostgreSQL recommendation truth tests and real isolated Redis cart tests remain passing.

## Not proven

New recommendation event RabbitMQ socket delivery has not been exercised locally. Producer/consumer tests use controlled broker transport, not a real quorum cluster. Existing worker startup topology now declares/binds the new queue. No live deployment, paid model evaluation, GTE performance evaluation, or load/cluster guarantee. No ruff/mypy tooling is configured/installed in this environment. Whole-platform readiness remains blocked on broader integration and deployment acceptance.

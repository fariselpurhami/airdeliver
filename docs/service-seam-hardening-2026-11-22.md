# Service seam hardening, November 22, 2026

## Search constraints

Regression before changes: 11 failures and 1 pass in test_commerce_constraints.py.
After changes: all 12 pass.

- Retain normalized positive integer excluded IDs; reject invalid expressions, booleans, nonintegral numbers, nonpositive IDs and nonfinite prices.
- Apply price/category/exclusion filters in SQL fallback rather than silently discarding them during a search dependency outage.
- Recheck cached/indexed hits against current database price, category and active state.
- Run bundle searches serially within a shared deadline because they share one AsyncSession. This favors transaction safety over unmeasured parallel speed.

## Payment finalization

Regression before changes: all 4 real-ORM boundary tests failed. They use a real SQLite SQLAlchemy Session/result and Order model behind an async adapter, not a permissive mock Order. They do not test PostgreSQL lock contention or external payments.

- Extract the Order scalar from a Row result.
- Persist a real provider-neutral transaction reference with an additive migration.
- Update is_paid and paid_at and retain the Stripe-specific reference for Stripe intents.
- Check owner identity and transaction consistency, preserve already assigned/paid order state, and reject cancellation reopening for manual reconciliation.
- Downgrade deliberately refuses to drop financial references without a retention plan.

## Verification

326 tests pass, 8 warnings, excluding the known memory-heavy test_behavior_engine.py. Coverage including worker_entrypoint.py is 47% (8,824 statements). No production boot, external payment capture, PostgreSQL migration execution or production model compatibility is proved by these tests.

## Still open, do not treat as production-ready

- PayPal capture must be bound to the correct local order and verified provider amount/currency/reference before capture. Checkout currently does not persist intent references before handoff.
- Stripe event dedupe precedes processing and failure handling can acknowledge unsuccessful work. Durable transactional outbox/dedupe remains needed.
- Payment side effects after commit are not atomically recoverable. A duplicate success can skip failed notifications/rewards/events.
- Checkout must reprice and validate stock against current database products rather than treating old cart prices as final.
- NLU/behavior embedding/profile/DTO seams, actual model inference, worker consolidation lifecycle, external dependency failure modes and full deployment integration remain under review.

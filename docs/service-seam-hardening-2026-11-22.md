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

## Behavior/NLU/worker follow-up

Six new boundary/inference regressions initially failed; all now pass. Fixes:

- Supply an explicit causal attention mask instead of relying on an unsupported causal hint without a mask.
- Store binary event packets as base64 ASCII for the existing Redis decode_responses=True connection. Inference still accepts legacy raw byte packets from binary clients.
- Track inference tasks, drain queued events during shutdown, serialize model access, and move model inference off the async message loop.
- Start consolidation during worker AI initialization and stop it before disconnecting Redis. Close resources on their original event loop even after startup errors.
- Align NLU and BehaviorEngine ghost keys, expose the public embedding method, use the real memory persistence parameter, and convert the typed confidence assessment at the DTO boundary.
- Run previously memory-heavy adapter tests with a small real-tensor brain fixture, without excluding any test files.

Latest complete backend suite: **337 passed, 12 warnings**, no excluded files; **51% statement coverage including worker_entrypoint.py**. The model tests deliberately use a reduced brain, not a production-default resource test. A corrected real-MiniLM smoke comparison between the old and new dependency environments also passes; see dependency-upgrade-2026-11-22.md for scope and persisted snapshots.

Important model limit: OmniNet currently initializes random weights and loads no trained checkpoint. Ghost tensor finiteness and API compatibility do not establish accurate preference prediction or stable semantics across restarts/workers. Training/calibration and production GTE/full-brain resource verification remain open. Nothing in this batch establishes million-user readiness.

## Free LLM retry/deadline follow-up

The retry foundation was unreachable after an unconditional return/raise. It now runs on connection errors and transient provider HTTP statuses only. Admission, all attempts and exponential backoff consume one outer deadline, and a slot is released during backoff. Invalid requests are not retried. SDK retries are disabled so nested retry policies do not multiply attempts. Cancellation still propagates. Regression baseline: two new tests failed, four passed; after the fix all six provider-limit tests pass. Full backend suite: **340 passed**, no exclusions. These are simulated transport failures, not proof of live provider quota/cost or availability. Stream-lifetime admission is not yet verified.

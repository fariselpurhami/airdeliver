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

## Payment authenticity and binding follow-up

The earlier PayPal binding and pre-processing Stripe cache-claim findings above are addressed in this batch:

- Persist the gateway's server-issued transaction reference before sending a payment URL/client secret to the browser. Legacy pending orders without a reference fail closed and need a new checkout, not an unverified capture.
- Before PayPal capture, verify the local binding, then fetch provider-owned order details and match order ID, local reference, owner, amount and currency. Verify completed capture funds as well as the outer order status. Completed orders reconcile without a second capture POST; capture POSTs have a stable PayPal-Request-Id.
- Add the PayPal webhook receiver, require PAYPAL_WEBHOOK_ID and signature headers, verify via PayPal's official verification endpoint, then match the independently fetched provider order and completed capture to the local record. The certificate URL is not fetched by this application.
- Fix Stripe settings dependency and SecretStr unwrapping. Verify the original raw bytes, cap both webhook bodies at 256 KiB while streaming, match Stripe amount/currency/reference/owner, and propagate processing failures as retryable 503 responses rather than swallowing them.
- Remove the pre-processing Redis claim that could mark failed work as already processed. The current order lock/state guard prevents repeat settlement, but this is NOT a durable event inbox or transactional outbox implementation.
- PayPal OAuth cache keys now distinguish account/API environment, and cache TTL does not intentionally exceed a short token lifetime.

Baseline: all seven new Stripe webhook tests failed before changes. Eight PayPal capture contract tests failed because the prior gateway accepted no server-owned expected-order facts. Tests now cover rejection without capture POST for wrong owner/reference/amount/currency, path rejection, completed reconciliation, exact raw-byte HMAC signature verification with the real Stripe SDK, request-size limits, error propagation, PayPal signature API wiring and both callback/capture endpoint bindings. Latest full backend suite: **362 passed**, **52% statement coverage including worker**; no excluded files. Provider HTTP is simulated. No live Stripe/PayPal payment, provider-console webhook registration, production callback delivery or full deployment boot was run.

Remaining launch blockers include durable event/outbox recovery, settlement-side stock/reservation and refund handling, catalog repricing, production model validation, and deployment configuration checks. A paid-state commit can still precede a failed notification/reward/event; do not describe this as exactly-once end-to-end settlement. Current checkout is USD-only, and these checks deliberately enforce that existing currency rather than guessing a new one.

Official references checked for this batch:
- https://developer.paypal.com/api/orders/v2/orders-get
- https://developer.paypal.com/api/orders/v2/orders-capture
- https://developer.paypal.com/api/webhooks/v1/verify-webhook-signature-post
- https://developer.paypal.com/pay-upon-invoice/integrate
- https://docs.stripe.com/webhooks

## Production configuration and migration follow-up

Baseline: four configuration tests failed. Production API and migrator were missing nine required CoreSettings variables; mounted *_FILE credentials were ignored. Alembic stopped before rendering any migration when DATABASE_URI was absent.

- Add a shared explicit production environment mapping for required app settings. This avoids loading the entire root .env into the API/migrator, while passing the payment/LLM/voice settings the API actually uses. Enable the existing Redis service explicitly.
- Resolve declared *_FILE settings, with file values taking precedence over stale plaintext environment/.env values. Missing, empty or oversized mounted files fail closed; file contents are never logged. Preserve secret spaces while trimming trailing newlines.
- Alembic now derives its URL from the same settings when DATABASE_URI is absent, and escapes ConfigParser percent interpolation so encoded credentials survive. User/password/database URL components use percent encoding, including spaces.
- Empty payment credentials are rejected rather than appearing configured. An empty Stripe webhook signing secret also explicitly returns 503 rather than accepting signatures made with an empty key.

Latest full backend suite: **369 passed**, **52% coverage including worker**, no exclusions. All migrations render as PostgreSQL SQL offline through a42bc980f321, including an encoded-password configuration. The additive payment-reference migration/backfill is also executed against an isolated SQLite test table. Neither check proves PostgreSQL migration execution, production lock behavior or Docker startup.

Docker and Podman executables and a Docker socket are absent in this execution environment. Compose YAML and required-setting coverage are parsed/tested, but no container build, compose config command, full stack boot or production integration result is claimed. Existing migration history contains feature-removal operations from earlier work; this batch adds no such removal. Review the migration chain against an existing deployment before applying it.

## Current-catalog checkout follow-up

Seven of nine new catalog/quantity regressions failed before changes. Checkout now validates bounded cart line counts/quantities/prices, rejects nonintegral quantities and invalid product IDs, and re-reads and locks current products before order creation. Missing/inactive products, insufficient current stock and non-USD products cannot reach payment initialization. Duplicate line quantities are aggregated for the stock/quantity check. All amounts derive from catalog prices. If a price differs from the cart, the cart is refreshed and shown for another user review; no order/payment is created at the changed price.

Complete backend suite: **378 passed**, no exclusions. These checks validate stock at checkout, but they do not reserve stock across the payment window. Competing pending checkouts, stock release/expiry, settlement inventory and refund/compensation workflows still need implementation and concurrency verification. Do not confuse a row lock ending at order creation with a reservation lasting until payment.

## Durable payment-event outbox

A new real-ORM regression reproduced paid-state commit followed by broker failure: retrying the already-paid order published no recovery notifications. It failed before this integration and passes afterwards.

- Persist three events (success text, order confirmation, conversion) in the same database transaction as payment settlement. The additive b52dc091a432 migration creates the outbox; duplicate order/kind pairs are constrained.
- Publish persisted events with stable event_id, AMQP message_id and correlation_id. Mark delivered only after a positive publisher confirm. NACK, exception and timeout leave the event pending with bounded exponential backoff. Publications have a six-second outer timeout and bounded batch size.
- Already-paid callbacks drain pending events without resetting order state or recreating rewards/events. A managed worker task also drains pending rows, including recovery after the callback process disappears. It uses per-row FOR UPDATE SKIP LOCKED, commits each result, and exposes scan state in worker health details. Its lifecycle follows worker startup/shutdown.
- Use string user IDs in these response messages to match the existing websocket consumer. Cart cleanup and gamification foundations remain in place.

Complete backend suite: **388 passed, 12 warnings**, no exclusions; **53% overall statement coverage including worker**, and 100% for the small outbox dispatcher module. Tests use real SQLite ORM transactions plus simulated broker confirms, failures and timeouts. PostgreSQL SQL renders offline through b52dc091a432. This is not a live PostgreSQL lock/concurrency, RabbitMQ durability or deployment-boot test.

Delivery is **at least once**, not exactly once: a crash after broker acceptance and before the delivery-marker commit can resend the same event ID. Downstream deduplication/inbox, durable cart cleanup and transaction-safe idempotent rewards remain open. This migration does not generate unsolicited notifications for historical paid orders. Pending-event count/age alerts and retention also need an operational policy. Stock reservations, settlement inventory/refunds and model checkpoint/training work remain launch blockers. The worker currently requires all gateway settings during initialization; that configuration seam is the next check.

## Gateway startup and simulation safety

All six new gateway safety regressions failed before the changes. The worker now initializes the configured gateway(s) instead of demanding Stripe, PayPal and M-Pesa credentials together. Missing settings are caught as typed validation failures without logging their values; unexpected constructor failures are not silently treated as missing configuration. No available gateway still fails startup explicitly.

The M-Pesa foundation was a sleep-and-fabricated-reference simulation, not a live integration. It now fails closed for live checkout. Its preserved simulation requires MPESA_SIMULATION_ENABLED=true, APP_ENV=development and the exact sandbox.safaricom.co.ke host; simulated results carry a simulated_ reference and explicitly state that no STK push was sent. The HTTP checkout provider excludes the disabled adapter, closes created HTTP clients even when no gateway is available, and avoids logging raw settings exceptions. Live M-Pesa OAuth/STK/callback implementation is still missing and is not represented as done.

Complete backend suite: **396 passed, 12 warnings**, no exclusions. The new tests cover Stripe-only worker initialization, no-gateway failure, disabled/default and production M-Pesa rejection, explicit labeled development simulation, live-host rejection and HTTP no-gateway behavior. Provider requests remain simulated; no external payment was made.

## API response-consumer integration

Three new integration/identity/startup tests failed before changes. The API accessed RabbitMQService.channel/exchange_name, neither of which exists. It launched this binding in a detached startup task, allowing startup to appear successful despite failure. A public consume method now binds through the actual connected topology, and API startup awaits registration. Binding failure closes acquired broker/cache resources and propagates.

Further checking against the real WebSocketManager, rather than an AsyncMock, caught a second mismatch: its connection keys are integers, while the relay passed strings. The relay now strictly normalizes positive integer JSON IDs or decimal strings to the manager's integer key, rejecting booleans, nonpositive IDs and ambiguous values. The test follows a real broker-service object through queue binding, callback decoding and the real manager to a fake socket, and checks that another user's response is not delivered to that socket.

Complete backend suite: **411 passed, 12 warnings**, no exclusions. No live RabbitMQ or browser websocket connection is claimed. This repairs single-process response wiring; it is not a durable client inbox, offline replay or multi-replica websocket routing design. Multiple API processes sharing one competing-consumer response queue still require a routing/broadcast solution before horizontal scaling. Health after a later disconnect and downstream deduplication remain separate concerns.

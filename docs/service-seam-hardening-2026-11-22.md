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

## Cross-process response bridge

Production compose sets WEB_CONCURRENCY=5. Its process-local socket managers therefore cannot rely on direct delivery by whichever process consumes the shared durable response queue. The existing websocket already subscribes to the user's Redis channel. The broker relay now publishes to that same channel, so the process holding the socket receives it through the existing listener. This preserves both foundations instead of adding another queue system. NoOp-cache development retains direct single-process delivery.

Two new bridge tests initially failed and now pass, including delivery to a real manager in a simulated different process and failure propagation rather than silent acknowledgement. Redis calls have a five-second bound and three transient retries with backoff; exhaustion requeues the broker message. Complete backend suite: **413 passed, 12 warnings**, no exclusions.

Redis pubsub is not a durable offline inbox. A disconnected subscriber can miss a message, and a crash after Redis publication but before broker acknowledgement can cause a replay. This fix does not claim offline delivery, browser receipt confirmation, deduplication, or a live five-process load test. Those remain separate verification/work. The previous multi-process direct-manager caveat is addressed at the routing level by this existing shared Redis channel, not by a claim of exactly-once client delivery.

The strict Redis bridge path is separately tested against the real RedisCacheClient wrapper. Its older best-effort publish decorator deliberately returns zero on connection failure, which is unsuitable before acknowledging a durable broker message. A new publish_required contract propagates backend failures instead; the broker relay uses that method. The existing best-effort API is retained for its other callers. This required-publication regression failed before the addition. Complete backend suite: **414 passed**, no exclusions. Tests still simulate the underlying Redis transport.

## Behavior checkpoint and lifecycle foundation

Three new engine regressions initially failed: loading saved weights, withholding random inference without a checkpoint, and refusing legacy random ghosts. The implementation now:

- Saves atomic versioned tensor-only checkpoints with action vocabulary, architecture, declared embedding revisions, dataset fingerprint, training/evaluation provenance and metrics. Invalid/nonfinite weights cannot overwrite a good artifact. Loads with weights_only=True from the same verified file descriptor used for hashing.
- Verifies SHA256, vocabulary, configured embedding identity/revision, architecture and tensor shapes/dtypes. Production requires an explicitly pinned artifact with declared held-out real-data evaluation and approval metadata, plus immutable embedding revisions. Metadata is a declared artifact contract, not an independent scientific attestation. No artifact is promoted by these changes.
- Does not allocate or expose a randomly initialized brain by default. With no artifact, neural inference and re-ranking are explicitly unavailable; observational event/history foundations remain. Invalid explicitly configured artifacts fail instead of silently falling back to random weights. Only an explicit development test flag can enable research-only random inference. This is not a rule-based replacement and is not completion of the training pipeline.
- Namespaces ghosts by artifact hash and event streams by embedding source. Ignores legacy unversioned ghosts rather than applying incompatible vectors. NLU meta-cognition reads the engine's versioned state; profile caches also include model identity.
- Creates one behavior engine per API process at startup, shares it across NLU requests, starts its consolidation loop and stops it before cache shutdown. The worker retains its managed lifecycle. Model state is available in worker health and the admin-authenticated /api/v1/health/behavior endpoint.
- Passes checkpoint/revision settings through production compose and supports pinned revisions in the embedding loaders. An empty optional setting means unset. Production compose explicitly selects production mode rather than inheriting a development environment value.

The corrected smoke remains a deliberately opted-in research compatibility test with random reduced weights, not evidence of trained recommendation quality. Training job, real-event durable dataset capture, evaluation on actual customers, monitoring thresholds and artifact promotion still need work. No production-ready checkpoint or measured real-data predictive quality exists in this repository yet. Full production GTE/full-brain resource fit and live deployment remain unverified.

Checkpoint/lifecycle verification: **428 backend tests passed, 18 warnings**, no exclusions, **55% overall statement coverage including worker**. The tests use small real tensor models and local checkpoint files. They cover exact state restoration, pin/vocabulary/embedding rejection, nonfinite-save retention, provenance gates, default no-random inference, legacy-ghost rejection, model/embedding namespaces and API dependency reuse. They do not validate production recommendation accuracy, a full-size model boot or actual training on customer data.

## Structured delivery and browser checkout

The launch market is the US. Checkout now requires a typed delivery snapshot and explicitly validates US region, ZIP format and phone syntax. This is format validation, not carrier deliverability. Orders persist their currency (USD for current launch checkout) and address snapshot. Historical orders get the existing USD currency but no invented address. The additive c63ed102b543 migration refuses destructive downgrade without a retention plan.

The standalone checkout now opens the same real assistant delivery/payment flow instead of a fake processing timer. The old visual foundation remains as an unused local component. Available payment methods come from the authenticated server. An explicit method selection does not initialize other providers. The backend access token is used for HTTP cart commands, rather than the encrypted frontend session cookie. Actual payment amount formatting uses Intl.NumberFormat and per-order currency; this does not internationalize the entire catalog UI.

PayPal has an approval panel, strict PayPal-host URL validation, configured merchant return/cancel URLs and an authenticated explicit capture step. Its redirect uses the current payment_source.paypal.experience_context contract. Physical-order shipping is supplied as a fixed address. The return page shows success only after the capture API confirms it, and reports network uncertainty without claiming no charge. A cancel return does not silently cancel an order. Browser checkout is unavailable for PayPal without a valid PAYPAL_CHECKOUT_ORIGIN. Configure the actual merchant web origin; no deployment domain was assumed. Production requires HTTPS; local HTTP is accepted only for loopback in explicit development mode.

Verification: 450 backend tests pass, 55% total coverage including worker. 35 frontend tests pass. TypeScript passes, including production-generated route contracts after fixing an existing Next 16 tracking params mismatch. A production Webpack build completed. PostgreSQL migration SQL renders through c63ed102b543; a SQLite migration test checks retained historical currency and absent historical address. Actual component renders with project CSS were visually inspected at mobile/desktop widths, including the PayPal approval/return/cancel states. This is not a hydrated browser-to-provider purchase test, a live payment, a full deployment boot, or PostgreSQL lock/concurrency verification.

Still open: signup wiring and public registration role isolation; checkout request idempotency/reconciliation; reservations, settlement inventory and refunds; durable downstream/client inbox and cart/reward side effects; full model training/evaluation and resource testing. Notification, experimentation, feature flags and compliance still require their own hardening. No claim is made that all 18 services are production-ready.

PayPal create-order contract checked: https://developer.paypal.com/api/orders/v2/orders-create and https://developer.paypal.com/api/rest/integration/orders-api/v1-v2-migration .

# Text-pipeline checkpoint ledger

Scope: inspect all remaining backend files in checkpoints, preserve real
foundations, no fabricated gateway/data/model, text before voice. No deployed
stack or credentials changed here. JSON inventory covers Python source paths,
syntax, definition counts and test-file text mentions, NOT semantic coverage.
No claim that every listed file has been audited or hardened.

## Checkpoint1: meta-cognition boundary, CI verified

Ten new regressions failed before changes. Prior implementation converted
uncalibrated weighted Euclidean distance into authoritative confidence and
invented historical confidence0.8. Empty/error states emitted uncertainty0,
and NLU defaulted to authoritative when there was no usable model/history.
Behavior ghosts are learned output-space projections; matching dimension does
not establish compatibility with the raw query embedding. Their producer does
not supply the assumed calibrated confidence.

Preserved service/config/DTO/enum entrypoints and real behavior model foundation.
Removed the unsupported numerical-confidence/purchase-authority inference, not
a trained model. No calibrated meta-confidence artifact exists. Missing evidence
now has explicit unavailable state, null uncertainty/drift/confidence,
calibrated=false and transaction_authorized=false. Legacy enum values remain
for wire compatibility, but cannot authorize a transaction. No rule-based model
replaces the old formula. Actual learned estimator training, held-out evaluation,
calibration and deployment gates remain unfinished, explicitly.

NLU uses known item facts with explicit uncertainty instead of requiring another
expensive query embedding for a nonexistent estimator. Failed generation no
longer claims a product matches the user's needs. This fixes this path only,
not every recommendation claim elsewhere. Changed hesitant-user guidance no
longer promises a risk-free investment. Production payment checks unchanged.

Local actual PostgreSQL19 migration+complete suite:536passed,2skipped,18warnings.
No live LLM evaluation, production checkpoint, model accuracy or full-storefront
journey proven. The diagnostic no longer masquerades as any of those.

## Original audit queue, status superseded by numbered checkpoints below

- Feature flags/experimentation: tuple-versus-boolean crash and rollout contracts.
- Text inference admission: noncancellable CPU work after async timeout and actual
  user-instance latency evidence; do not hide failures by lifting deadlines.
- Compliance service: hardcoded zones and endpoint-only route checks cannot
  certify legal drone routes. Preserve foundations, fail closed without approved
  current data. Drone/voice last, not a text blocker.
- Other services and endpoints in inventory: verify caller contracts, isolation,
  invalid input, cancellation and durable behavior before changing them.
- Behavior trainer was created by this work at20:01:36Nov22 and left untracked.
  Its origin was initially misreported as unknown. Checkpoint9 tests and commits it.


## Checkpoint2: feature/experiment foundations

Repository-wide caller search found no active application callers for these two
service foundations.15new regressions failed before changes. Legacy boolean
flag caused tuple-unpack failure; bool/negative/noninteger user IDs could enter
percentage rollouts. Experiment defaults pretended a checkout-color experiment
was active without a declared version/configuration.

Preserved public feature/variant methods and registered feature names. Immutable
validated rollout config accepts legacy bool/tuple and explicit Rollout objects.
Unknown/invalid subjects are not enrolled. SHA256 namespaced cohorts are stable
across processes without Python hash randomization or time. Versioned experiments
must be supplied explicitly; default returns control/unassigned. This removes
only an unconfigured demonstration assignment, not a deployed experiment.
Assignments expose experiment version, not fabricated exposure/results.

This is deterministic product configuration, NOT a behavioral model substitute.
No claims of distributed config, live admin UI, durable exposure capture, A/B
statistical significance or activation in app routes. New hashes would change
cohorts if an external consumer existed; none was found in the repository.
Local completePG19suite553passed,2skips,18warnings before final commit.


## Checkpoint3: bounded text inference and optional Hub auth

Two real-thread tests failed before changes. A timed-out/cancelled caller freed
its asyncio semaphore while CPU encoding continued; separate request engines
shared one model but not admission. Text query inference now has a weakly held
process-wide per-model gate. One total25second deadline covers admission+compute.
A submitted CPU job itself releases its gate in finally, not the timed-out
coroutine. Late exceptions are observed. No second model and no timeout increase.
Tests cover timeouts, cancellation, shared-instance blocking and eventual reuse.
Logs expose queue deadline versus submitted work and actual encode duration,
without query text/vectors. Not evidence of actual Mac latency or model quality.
A hung native call cannot be killed safely by this implementation: subsequent
callers time out without submitting more compute. Process-level restart remains
an operational option, not automatic data deletion. Other direct model.encode
paths, image inference, multi-process admission and distributed capacity remain
separate audit work. No global-resource-fit claim.

HF_TOKEN was already blank in .env.dev.example. Added optional read-token docs
and explicit seeder mapping. Effective Compose test proves api/worker/seeder
receive a sentinel token and share persistent cache mount/path. No real token
used. Cache hits avoid weights downloads, but not every metadata/revision request.
Do not promise offline operation or suppress warnings. Public models can work
without token; auth improves download quotas and permits granted private access,
not inference latency or automatic gated-model approval.

Official sources:
https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables
https://huggingface.co/docs/hub/security-tokens


## Checkpoint4: notification adapter truth and ORM boundary

Two new regressions failed before changes, including a real SQLAlchemy result
rather than a mock row. Push flow used result.all() Rows as subscriptions and
swallowed the resulting exception, so it could silently send nothing. It now
uses scalars(), bounded payload and explicit sent/failed counts. Provider
rejection returns failure without logging recipient/payload/provider exceptions.
Missing VAPID key and unexpected failures propagate instead of returning success.
Email/SMS mock loggers are preserved as adapter method boundaries but explicitly
raise unavailable; there is no configured actual email/SMS provider. Their old
PII/content-bearing fake-delivery logs are removed. No active app caller of these
methods was found. No external message, paid service or new account was used.

Actual push transport is mocked in the ORM regression. Live subscription expiry,
SSRF/egress controls for client-provided endpoints, delivery receipts, retry
outbox, VAPID contact configuration and actual provider validation remain open.
This is not production push delivery certification.558localPG19tests passed,
2skipped18warnings before commit.


## Checkpoint5: notification list/read representation

Two actual regression tests failed before changes: SQLAlchemy Rows treated as
notification models, and negative relative age for future timestamps. Uncovered
second DTO seam: response requires cta/timestamp fields absent from ORM model.
Explicit serialization now supplies known fields, optional cta from metadata,
rendered timestamp, and scalar models scoped to authenticated user. Naive legacy
times are labeled timezone unknown, never silently attached to a guessed zone.
Read-all route exercised as real FastAPI HTTP request.562localPG19tests passed,
2skips18warnings. No production data migration or notification delivery occurred.

Subscription endpoint still double-encodes JSON, lacks resubscribe upsert and
strict endpoint/key schema. Provider-egress controls and subscription validation
remain separate next work; list/read fix does not certify push security.

## Checkpoint6: authenticated support session isolation

Two regressions failed before changes. Reusing a caller-controlled session ID
shared cached history across authenticated users. The authenticated owner ID now
namespaces a SHA256 digest of the client session ID; legacy unscoped history is
not loaded by signed-in users. No cache data deletion or migration performed.
Cached history accepts user/assistant messages only, at most ten messages and
10000 characters per message. Invalid cache content starts a fresh session and
logs only the exception type, not cache content. Tests cover same-owner context
continuity and distinct-owner isolation. Anonymous chat still uses bearer-like
client session IDs, with no verified ownership or server-issued anonymous cookie.
Concurrent writes to one session remain last-write-wins. Action completion and
uncalibrated confidence claims are separate next work, not fixed by isolation.

## Checkpoint7: support action proposals are not completed actions

Four regressions failed before changes. Text and visual search had inferred
immediate dispatch or planned restock from inventory quantity alone. They now
report catalog stock and explicitly unverified shipping timing. Order tracking
and human support preserve their typed action proposals but no longer claim
satellite tracking or completed escalation. No backend order lookup, support
connection or frontend action execution is added or claimed. Repository search
found action definitions and service/tests, not a frontend executor for these
actions. Existing characterization assertions about dispatch/restock are changed
to stock-only contracts, backed by the new failing-before tests. Hardcoded
confidence fields remain uncalibrated and require a caller/schema migration.

## Checkpoint8: total routing deadline and private failure logs

Three regressions failed before changes. Permanent HTTP400 errors previously
retried three times; retries are now limited to connection/timeouts,429 and5xx.
One8second anyio deadline surrounds all attempts and backoffs, not8seconds per
attempt. Cancellation is not swallowed. Invalid provider JSON and exception text
are no longer logged; error type is enough for diagnosis. Missing configuration
and inference failure report unavailable, not a fabricated cold restart or glitch.
Tests use controlled provider doubles, not paid/live Groq calls. This bounds the
routing phase, not end-to-end product search, cache, visual or HTTP request time.

## Checkpoint9: finish the previously uncommitted offline trainer

Origin recovered: this work created behavior_training.py at20:01:36Nov22, not
Faris's original backup. Dedicated dataset/split/real CPU training/warm-start/
artifact tests and an operational module CLI now cover the previously untested
candidate trainer. Output-overwrite regression failed before protection was
added. CLI requires explicit architecture and new output path, bounds CPU threads,
and never activates a serving model. Every result stays production_approved=false.
Small synthetic tests exercise actual optimizer steps in both heads, artifact
roundtrip and warm starts. No real-customer dataset, full-size training, capacity
certification or online recommendation improvement is claimed. See
behavior-offline-training.md for operation, dataset schema and remaining limits.

## Checkpoint10: valid subscription JSON and resubscribe upsert

A real ORM regression failed before changes: subscribe encoded a JSON string
inside the JSON column. Subscriptions now store validated objects. PostgreSQL
ON CONFLICT updates the existing unique user row atomically when resubscribing,
not a second insert failing uniqueness. Browser endpoint and encryption-key shape
are validated, including actual P256 point parsing. Plain HTTP, credentials,
IP-literal hosts and nonstandard ports are rejected. Existing stored strings are
not migrated or deleted. Current one-subscription-per-user foundation is retained,
so resubscribing replaces that user's prior device rather than adding multidevice.

This is input/schema hardening, NOT full SSRF prevention. DNS could resolve a
hostname to private addresses, redirects and outbound network policy are not
controlled here. Provider allowlist/egress enforcement remains a launch blocker
before untrusted subscriptions can trigger backend sends. No actual push provider
send performed.591 local PG19-suite tests passed,2skipped20warnings. Subscription
ORM regression uses SQLite with the PostgreSQL upsert construct; actual PostgreSQL
route+concurrency stress is not yet included.


## Checkpoint11: CI-only search disk budget

A later duplicate18daf53 run45076152994 failed in Seaweed search verification:
OpenSearch returned403 index_create_block_exception with disk high-watermark
warnings and about5GB/7percent free. RustFS passed the same17row learned-embedding
seed path. Newer checkpoint6/7 jobs passed both backends. Do not label this as a
credential failure or hide it by disabling disk safety. Before search integration,
the hosted CI job now removes only disposable Python package download caches and
unused Docker build cache, retaining installed environments/images/containers/
volumes. Disk use is printed before/after. No user machine cleanup or production
watermark change. This mitigates cache pressure, but only the next CI run can
measure reclaimed space and establish whether the incident recurs.

## Checkpoint12: cache failure fallback and privacy

Two regressions failed before changes: Redis errors hit logger extra.args,
which conflicts with the reserved LogRecord field and raises KeyError instead
of returning the documented fallback. It also attempted to log raw operation
arguments, which can contain chat, tokens, cart or session values. Error logs
now retain operation and exception type only. JSON serialization/corruption and
initial-connect logs likewise exclude keys/raw exceptions. Same fallback return
contracts and Redis operations retained. Tests inject connection/Redis failures;
this is not live failover or a change to fail-open rate-limit policy.

A third failing-before regression covers the documented stdlib JSON fallback:
json.dumps returns str, so unconditional.decode crashed. Both byte/string
serializers now retain the same JSON storage contract.

## Checkpoint13: real voice transport boundary

New real loopback TCP/WebSocket integration failed before changes because the
installed websockets version rejects extra_headers. Correct additional_headers
and current close semantics now tested through actual Uvicorn, browser-side
WebSocket protocol and a local upstream server. Current provider audio envelope,
subtitle frames, ping/pong and nested tool-call response use published schemas.
Disconnect exits reader and closes upstream. PCM bytes roundtrip unchanged.
Older top-level audio remains supported for compatibility.

The upstream is a local protocol fixture, NOT ElevenLabs. Prior14 voice service
tests use fake commerce/LLM/cache/socket boundaries and3 route tests replace the
orchestrator. Those verify logic, not provider acceptance or audible quality.
This new test uses real TCP/WebSocket libraries and production orchestrator but
no real provider key, microphone, browser audio device or paid traffic. Live
ElevenLabs agent authorization/configuration, sample-rate agreement, microphone
capture/playback and full commerce-tool use still require an authorized real
session. A key alone does not establish spend permission. No claim of complete
voice production readiness is made by the loopback test.

Provider sources inspected:
https://elevenlabs.io/docs/eleven-agents/libraries/web-sockets
https://elevenlabs.io/docs/eleven-agents/api-reference/eleven-agents/websocket

## Checkpoint14: remove unused drone compliance remnant

User explicitly allowed deletion if no real use. Drone subsystem was already
removed359dc1b, with migration f3a91c07b2d4 and follow-up CI/docs removal. The old
compliance_service.py had no imports/callers in repository search, no registered
route, no test, and only two hardcoded flight exclusion circles. It checked the
destination only, so could not validate a flight path, and has no current commerce
use. Remove this orphan, not a functioning compliance integration. Voice has
already had repair/test checkpoints; it is not an untouched later subsystem.
Live microphone/provider acceptance remains unverified, as checkpoint13 states.

## Checkpoint15: voice broker admission is not completed cart action

Two regressions failed before changes. Voice tool ignored publish result and
claimed action_executed even when broker returned failure. It now requires an
explicit positive broker confirmation and says QUEUED/action_requested, never
completed. Existing queue/routing foundations preserved. Tests cover positive and
negative confirms; actual downstream cart mutation and UI acknowledgement are
separate, not claimed by a broker receipt. Existing unit test broker fixture now
supplies the real publish-result contract instead of an unconstrained AsyncMock.

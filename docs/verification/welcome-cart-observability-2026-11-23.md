# Welcome and cart latency diagnosis

No runtime cause is asserted from a successful OpenSearch line alone. Hybrid search awaits OpenSearch and Milvus concurrently. The vector search had a25-second timeout on the native search task, but its semaphore acquisition was outside the deadline. This patch covers both the wait and the call and passes the timeout to the SDK too. Cancelling a to_thread await cannot kill native computation; the SDK timeout is also necessary. No new provider requests, model changes or mocked runtime data.

Welcome previously performed freshness, behavior and four sequential retrieval pools without an overall deadline. A DAL exception could return without UI output. New75-second welcome budget and45-second stage budgets bound cooperative work, log stage start/completion/type/duration, and attempt a real error notification on failure within3seconds. Cancellation propagates. Row publishing now propagates failures instead of reporting a delivered row. It is not a guarantee of delivery if Redis/websocket is unavailable, that failure is logged too. Event-loop CPU blocking cannot be preempted by an asyncio deadline.

Router errors were already caught, but the conservative formatter dropped error_type extras. New allowlisted error type, HTTP status and category are formatted in the message, so JSON and text modes retain them. Never print raw provider exceptions, response bodies, keys, prompts or messages. A1.9-second failure cannot be identified as authentication, rate limit, quota, malformed output or connectivity from the old line. It is earlier than the8-second outer deadline. No historical grep can recover a field that was never serialized. No automatic key rotation or quota purchase is appropriate.

The API and worker own separate process-local ModelRegistry instances. Both can load the text encoder, so CPU/RAM contention is plausible on a slow laptop, not established as the cause. This patch does not disable either model, change the profile, or loosen the25-second embedding deadline.

## Cart and recommendation path

The current card ADD dispatches HTTP /ai-ordering/cart/add, not q.ai.cart.add. Websocket readiness gates the HTTP dispatch; disconnected requests can queue and later flush. Mutation is performed in API, cart state is relayed through Redis/websocket. New pending copy does not claim a successful add; disconnected3-second unlock reports the request remains queued, not cancelled. Cart writes are not cancelled or replayed by a new timeout. Added request/service stage timing marks request, catalog read, cart read, persist and operation completion/failure. Recommendation timing marks readiness/search/completion or failure.

Complement-on-add and alternative-on-remove remain active optional read-only followups, wired by813ec7e96055ae4e763a3298096293aac8f3763b. q.ai.cart.recommendation handler waits for readiness, checks current membership, searches real catalog, rechecks membership/exclusions and emits product_carousel. Empty catalog-evidenced results intentionally emit no recommendations.30-second consumer search timeout remains unchanged. q.ai.intent.removal_recovery records discard behavior, not the replacement cards. No claim of success on the owner's live machine.

## Layout history

The overlay at0c901da already rendered both product_carousel and proactive_suggestion with horizontal ProductCarousel.3e9dc36 retained that structure. Current welcome can emit up to four vertically stacked carousel messages, each with an Insight. PR31 only exported AIReasoning in production frontend, changing no layout. A stalled first sequential personal pool blocks all subsequent welcome rows. The history checked does not establish a removed per-product vertical list; no speculative layout replacement included.

## Read-only owner checks

Use the established combined Compose files and .env.dev, never print the environment. Existing API logs around the original request are needed, alongside worker logs; worker logs alone cannot show the HTTP router failure. For the old correlation3b9a647f-766d-42a3-962b-3d2c738c946d, capture API log lines containing that ID and neural_core.router near15:52:52..15:52:54 UTC. No new chat request needed. The old formatter cannot recover omitted error_type. After an approved update, new router lines expose safe status/type/category.

Read-only commands: combined-compose ps; combined-compose logs --since30m --timestamps --no-color api api-worker; docker stats --no-stream airdeliver-api airdeliver-api-worker. Inspect /ai-ordering/cart/add status and timing, websocket connection, cart_add, cart_recommendation, matrix_stage, hybrid_stage, text embedding deadline events. Do not send secrets or full request bodies. Correlation IDs and timestamps locate the request, but stage durations alone do not prove CPU contention.

## Verification

Full disposable migrated PostgreSQL19/Redis1060passed4skipped, including controlled timeout, cancelled stage, blocked semaphore, strict UI failure, conservative-formatter privacy and cart timing tests. Frontend151tests/27suites, TypeScript/production build pass. Test doubles are limited to fault/transport injection in tests, never runtime implementations. Existing real catalog, Redis persistence and queue-contract suites remain. Actual deployment, native Milvus server cancellation, live Groq failure class and owner's CPU cause remain unverified. No owner-machine command, migration or provider request executed.

# Native async Redis limiter candidate

## Scope and contracts

Python3.13.18, FastAPI0.165.0, redis-py8.1.0, SlowAPI0.1.10, limits5.8.0 inspected locally, no dependency upgrade. Existing `limiter`, `build_limiter`, `install_rate_limiting`, `storage_unavailable`, `.limit`, `.exempt`, `.enabled` call sites retained. Existing429 error payload and Redis outage503 + Retry-After1 preserved. Default100/minute, explicit auth/ordering limits and root health exemption preserved. Internal Redis counters move to v2 namespace, so a rollout resets current rate windows; this is a disclosed behavior change, not durable business-state loss.

Problem: installed SlowAPI invokes synchronous Redis from async request handlers. Socket timeouts bound stalls but do not make them nonblocking. Decision: native redis.asyncio, atomic single-key Lua increment+expiry, bounded32connections and32inflight admission,0.25s socket timeout and0.6s total admission deadline. No threads, no fake cancellation. CancelledError propagates to async Redis I/O. Backend errors fail closed, no process-local fallback when Redis configured. Explicit USE_REDIS=false retains bounded10000-key in-memory dev mode. Clients are lazy per event loop and closed on lifespan exit, allowing test/dev-loop isolation.

Only request.client defines identity; no arbitrary forwarding-header parsing. Deployment proxy trust remains unverified and unchanged. No claim that this implements a global multi-region quota, provider request ledger, or overall WebSocket message quota.

## Verification

- Baseline joint logging/limiter local951passed4skipped20warnings.
- Candidate full suite953passed4skipped20warnings.
- Real disposable Redis150concurrent HTTP requests, limit100:100success,50rate-limited, elapsed0.082s, maximum5ms heartbeat gap0.0408s on this host. This is a small local responsiveness/concurrency check, NOT production capacity or p99 certification.
- Separate delayed-native-I/O test proves exempt health stays responsive and caller cancellation reaches the awaited operation. Existing real Redis tests cover independent-instance quota sharing, expiry, key isolation, outage503 and health exemption.

## Gate status

BE-G1 contract compatibility: localPASS for inspected callers, CI pending. G2/G3 business accounting/CAS N/A, only ephemeral admission counters. G4 privacy/proxy posture PARTIAL, no auth redesign and proxy deployment unverified. G5 resource/cancellation localPASS for admission bounds, no full-system pool/load qualification. G6 localPASS, CI pending. G7 cleanup localPASS, low-cardinality metrics/traceparent still pending. G8 evidence caveats stated. FE contract impact429/503 preserved; browser UX/RTL/network behavior NOT RUN. Not production-qualified.

Before merge: greenCI, parent confirmation, then rolling restart changes only after user execution approval. No deployment, provider request, migration or credentials touched. Rollback is previous main commit; Redis v2 counters expire automatically and no durable business data is changed.

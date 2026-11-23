# Shared sales response boundary

PR36 is the first step of the owner-approved restoration plan, after PR35. It keeps the HTTP support adapter and its public response contract but adds a reusable `SalesResponseService` with an explicit request object. The existing support `_shopping_response` now delegates to it. Current evidence, brief and request metadata are copied per request before network awaits; another caller cannot change displayed price/spec evidence during generation.

This boundary owns model-authored copy, typed claims, independent review, deadline, system-notice failure and text/card pairing. It cannot mutate a cart, call checkout, read private customer context or start provider activity on import. Callers still own retrieval/current-row verification and authority for their own effects. This isolates the sales presentation layer for later optional worker and opening adapters without making a cart commit depend on a model.

No old files or handlers are removed. No provider/model selection changes, live provider calls, migrations, payment calls or owner operations. Later restoration adapters are NOT silently activated here. Per-PR merge approval remains required. Natural-language review remains defense in depth, not a proof of no hallucination. Actual model quality and production latency remain untested.

Verification:1100 backend passed,4 skipped, using migrated disposable PostgreSQL19 and existing real HTTP/current-row tests. Focused tests cover bounded/deduplicated request contracts, non-catalog recommendation rejection, provider-unavailable no-call behavior, support adapter compatibility and in-flight evidence isolation. No UI change.

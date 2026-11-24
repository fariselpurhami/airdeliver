# Commerce OS threat model and hardening ledger

Baseline: November 23, 2026. Scope is the four-file commerce logic and its actual HTTP, worker, Redis, SQL, search, model and UI boundaries. This is a living evidence ledger, not a claim of a vulnerability-free or globally production-ready system.

## Assets, actors and trust boundaries

Assets: customer identity/session history, consented preferences, carts/orders/payments, catalog provenance, provider credentials, model budget/availability and operational logs. Actors: authenticated customers, anonymous visitors, merchants/catalog importers, external web content, provider responses, webhook senders and operators. Treat customer/catalog/web/model text as untrusted data. An authenticated transport or model response does not authorize a cart/order action or turn a catalog claim into supplier evidence.

Boundaries: browser to authenticated API; optional anonymous chat to session memory; API to Redis/SQL and message bus; worker to current catalog; product/web evidence to model; model JSON to reviewed prose/cards; provider payment/webhook to bound order; application to logging/CI/package supply chain.

## Finding ledger

| ID | Evidence / current observation | Risk and next verification | Fix / status |
|---|---|---|---|
| SEC-01 | ai_support.py optional user dependency; neural_core_service.py binds signed-in history to owner plus session digest. test_neural_session_isolation.py exists. | Anonymous session IDs remain caller-controlled. Test guessing/reuse, retention and whether any private context can enter anonymous history. | Existing owner isolation verified by prior tests. Anonymous isolation review open; focused PR required if confirmed. |
| SEC-02 | ai_ordering.py cart routes use current active user and inject current_user.id, checkout cancellation/capture have bound owner checks. ai_checkout_service.py checks payment owner. | Build route-level cross-user matrix, missing/expired token tests, payment-ID replay checks and cart review ownership; include all alternate endpoints. | Partial coverage in test_ai_ordering_http.py, test_paypal_capture_security.py and payment tests. No universal authorization certification. |
| SEC-03 | support payload bounds4096 text/7MB base64; strict cart quantities/IDs, current SQL currency/stock checks. | Verify actual byte decoding/image decompression limits and malformed nested JSON across every public path, not only DTO constructors. | PR35/37 evidence boundaries; remaining input audit open. |
| SEC-04 | Shared writer/reviewer treats catalog/input as data, checks declared product IDs/fields/numbers/URLs. Legacy NLU prompt branches remain contradictory. | Prompt-injection/exfiltration through product attributes, web snippets, history, image OCR and model output. Review every branch before reconnecting. | PR35/36/37 shared boundary, PR38 diagnostics. No general claim that independent model review proves semantic entailment. |
| SEC-05 | Main AsyncLimiter uses native Redis, shared admission,0.6s budget, explicit503 on storage failure. Support-specific limiter is per authenticated user or caller session and fails open. | Session rotation and global/IP quota behavior, expensive model concurrency, optional opening up to8calls. Test combined middleware plus endpoint policy and cache outage. | Real Redis load tests exist. Repeated local load failures under full-suite resource pressure need separate diagnosis; tests not weakened. No new cap silently imposed. |
| SEC-06 | JsonFormatter drops arbitrary extras and redacts configured secrets, bearer values and exception bodies. Legacy FreeLLMService logs some raw exception strings; NLU logs raw query fields. | Secret/PII exposure through message text and alternate logger configurations. Audit current configured output, not only extras. | PR38 safe stage/reason diagnostics. Further exact logging audit/fix PR required. |
| SEC-07 | Secret history guard scans reachable git history with checksum-pinned gitleaks. Several CI actions use major tags; dependency audit not observed in inspected workflows. | Known-vulnerability and supply-chain compromise coverage is not equivalent to secret scanning. Inventory locked dependencies, images, actions, model revisions, downloads. | Existing secret scan green. Dependency/SBOM/advisory and immutable-action review open. No network scan or package update represented as done. |
| SEC-08 | Cart CAS/receipts prevent blind mutation replay; recommendation worker only reads and rechecks cart/catalog after model work. | Redis/AMQP uncertainty, duplicate/out-of-order events, native work cancellation, SQL sessions spanning external awaits, slow publication. | PR37 real SQL/Redis tests plus existing broker characterization. Freshness is not a lock on merchant stock. |
| SEC-09 | Current catalog gate marks demo/local provenance, current availability, currency and prices; model cannot assign card facts. | Merchant source compromise, stale index/cache, synthetic data leaking into checkout, conflicting imported specs. | PR35 card disclosure and PR37 recommendation filtering. Held PR29 inventory source design still excluded; supplier verification not implemented here. |
| SEC-10 | CustomerMemoryService explicit preference extractor/consent path, legacy inferred memory writer deliberately unwired. | Consent withdrawal, deletion, cross-user/vector filtering, stale assistant assertions and sensitive inference. | Existing memory tests partially cover SQL. Legacy vector recall must remain gated until lifecycle and permissions verified. |

## Release evidence gates

Each fix gets its own PR, exact-head CI, current-base/unchanged-main merge gate, tests at the actual affected boundary and scoreboard updates. A green unit test cannot stand in for SQL/Redis/AMQP/UI execution. Live provider quality, deployed service behavior, actual merchant inventory, security scanning results and real multimodal execution need their own evidence. No live provider calls, spending, production migration/reindex/seed/deploy, secret rotation, deletion or visibility changes are authorized by this document.

Order: unblock PR38 first, model opening/Insight, staged per-item search/comparison/consultation, consented context/observability. Security findings are fixed alongside the feature boundary they affect. High-risk confirmed findings can interrupt that order with an explicitly reported reason.

## Safe commerce diagnostic boundary, November 23 follow-up

The current `StructuredLog` path now drops raw customer/model/catalog/search prose, cache keys, arbitrary exception strings and budget values before creating the log record. Only selected numeric counters/timings, booleans, bounded operational labels and correlation identifiers survive. Exceptions retain their class name, not their body or traceback. The original emitter remains explicitly legacy and is not used by the public logger methods. NeuralCore intent/target-count/task and completion timing now survive the final formatter rather than disappearing in discarded extras.

Evidence: `test_commerce_safe_diagnostics.py` exercises the actual logger-to-formatter boundary in JSON and text modes, malformed metadata and exception bodies. This closes the inspected NLU message-text bypass, not every logging finding in SEC-06. Other services, legacy-only methods and alternate configuration still need their own audit. These logs identify stages and timing, not the exact rejected customer/model text; do not infer inventory absence from zero candidates.

### FreeLLM search-log follow-up

Two additional message-text leak sites are now bounded: short search-term fallback logs only input length, and the older commerce orchestrator logs only route boolean, product count and query length. The original query/search terms still flow through search, fallback and the response unchanged. No search or orchestration capability was removed. `test_llm_search_log_privacy.py` drives both actual methods with controlled model completions and checks LogRecord plus final formatter output. Other service logs and legacy exception/alternate-handler behavior still need review.

## Bounded visual decoding follow-up, November 24

Engine image decoding now rejects excessive encoded input and decoded bytes before image parsing, then checks declared dimensions/pixel count before load/RGB conversion. Existing base64/data-URI and first-frame RGB behavior remains. Default limits: 7,000,256 encoded characters, 5 MiB decoded bytes, 25 million pixels, 16,384 pixels per edge. These limit compressed-image expansion without claiming all malformed codec paths or native work deadlines are solved. The existing decoder remains the model entrypoint, with invalid input rejected before model acquisition.

`test_bounded_image_decode.py` uses actual Pillow PNGs, malformed/truncated bytes, oversized dimensions, byte/encoded limits and a model-registry sentinel. Full disposable SQL/Redis suite: 1192 passed, 4 skipped. No actual recognition quality or live model execution claimed. Decode offloading and vision inference admission/cancellation remain next runtime work.

## Vision native admission/cancellation follow-up, November 24

The current vision encode path moves decode, model acquisition and inference to native worker execution behind a process-wide two-slot gate shared by request-scoped engines. The queue and await share one deadline. Timeout/cancellation returns to the caller without releasing a still-running native slot; only the native worker releases it. Image resources close on success/failure. The prior encoder remains explicit legacy, not called by the current method. A hung native worker can occupy a slot until process restart; this is bounded admission, not forced thread termination.

`test_vision_native_admission.py` uses actual executor threads and controlled tensor/model work to verify timeout, cancellation, cross-engine admission, off-loop decoding and failure cleanup. Full disposable SQL/Redis suite: 1195 passed, 4 skipped. No provider calls, external model downloads or recognition-quality claim. Vector-store native search cancellation remains separate work.

## Worker cold-start recovery follow-up, November 24

Owner reported text warmup budget exhaustion, degraded worker health503 and startup-not-ready message rejection. Current fix adds validated warmup/startup/recovery settings, dev budgets1200/1500s, and automatic degraded-AI retries. Fast-sample criterion remains5s; steady37s encodes do not become ready under a25s request deadline. Native loader futures are reused across caller deadlines, registry retry creates a new rejection generation only after the prior native attempt releases the model lock, and OpenSearch resources are reused across retries. Pre-handler readiness failures retain the original broker message with delayed requeue, not capped drop. Original capped startup policy remains explicit legacy.

Full disposable SQL/Redis suite1201passed4skipped. New tests include actual loopback HTTP503-to200 recovery, actual native-loader single-flight after timeout, registry rejection-generation reset, cold timing sequences, persistent slowness rejection and message disposition. Existing uncertain cart-write replay suppression remains unchanged. Controlled model/broker interface tests do not prove owner's hardware will meet readiness; owner rollout/retest remains needed. Earlier dropped delivery is not automatically recoverable by this code.
## Native vector-search admission follow-up, November 24

Current text and visual Milvus searches now share a process-wide eight-slot native gate. Queue wait and native await share a deadline, an SDK timeout is forwarded, and only completion of the worker releases its slot. Caller cancellation/timeout does not admit unbounded replacement work across request-scoped engines. Existing per-engine semaphore remains, text failure policy and result hydration remain unchanged. This covers text/visual search calls only, not legacy memory mutation or alternative-query/bootstrap calls.

`test_vector_native_admission.py` drives actual executor threads and current text/visual entrypoints, cross-engine contention, cancellation, failed workers, cancelled waiters and SDK timeout forwarding. Full disposable SQL/Redis suite: 1198 passed, 4 skipped. No live vector-store/model quality claim and no provider calls.

## Restoration release follow-up, November24 04:38

Shipped source revision694cec5. PR73restores source research before catalog, but untrusted page evidence still relies on exact quote membership plus independent model entailment/identity review. Model review is not proof against prompt injection. PR79restores setup and image hint routes without compatibility/identity guarantees. PR75blocks synthetic offers across storefront/search/support/cart/checkout while retaining stored rows. PR70daily recency affects only real offers and retains historical seen state. PR82literal hard features remain partial: substring-boundary followup89pending, no unit magnitude inference. PR81only prepares reversible quarantine, never owner execution, restore provenance/fullDR remain open.

SEC-05 remains open: Redis replacement84passed repeated local full suites but both CIbackends still failed exactquota at49ratherthan50 rate-limited responses. Bounded diagnostic classification added, no quota assertion weakened and no failed head merged. Main still uses earlier32connection limiter. Do not interpret a separate green run as resolution.

Pending83coverage,84Redis,85query rewrite,86strategy,87per-target sources,88typed adapter,89literal boundaries are not shipped by this snapshot. The historical35preserved/15degraded/5lost audit remains as-of03:30, not current final counts. Every live_verified flag remains false. No owner deployment, provider execution, migration, seeding, rotation or deletion was performed.

## Current boundary ledger, November24 06:19

This section supersedes the shipped-state claims in the04:38 snapshot above, which remains historical evidence rather than current status. Main is cd339c0 through PR102. PR92 replaced the old Redis limiter with bounded native admission after an approved measurement split. Required isolated100/50quota and0.2sheartbeat gate plus separate deliberateGC/process/Redis pause characterization remain enabled. SEC-05 is not closed: real-process mixed-loadp99/max and GC tail behavior remain unmeasured. Support-specific fail-open/session-rotation behavior remains a separate finding.

SEC-02/08: new reviewed whole-cart lifecycle uses authenticated owner, five-minute snapshot-bound record and atomic one-shot consumption before effects. Reviewed clear affects only the active cart and preserves pending orders. Save reuses unpaid cancelled Saved List records and reports SQL-success/cache-cleanup uncertainty, never blind retry. Legacy clear/save endpoints remain available with their existing semantics. Actual HTTP/SQL/Redis tests are in test_cart_lifecycle_review.py; they do not prove universal authorization or cross-store transactionality.

SEC-04/09: per-component setup requirements require literal customer spans and independent scope review, plus current catalog/scoped permits rechecks after copy. Independent model review remains a semantic trust boundary, not proof. Context and constraints are kept separate from merchant/source evidence. Per-component scope is currently recomputed from customer turns rather than durable typed session scope.

SEC-10: ordinary HTTP opt-in collection and revocation tests now reach canonical SQL. Recent customer-only context reaches setup/research, and image copy preserves the hard brief. Pending PR105 separately carries consented hints to setup/research with recheck before publication. Pending PR104 carries displayed current-customer removal reason only to optional advice; no inferred motive/profile or automatic re-add. These pending changes are not shipped by this snapshot. All live verification flags remain false. No owner/provider/DR gates were executed.

## Shipped checkpoint, November24 06:54

Main a23251f includes PR104 displayed literal removal context, PR105 separate consented setup/research hints, PR107 narrow same-unit English explicit capacity bounds, PR108 strict read-only legacy intent/query callers with safe failure logging and PR109 durable reviewed setup scope. Their exact latest heads passed required CI before merging. This supersedes earlier pending-status notes, not their residual risks. PR110 ordinary catalog target scope remains pending required CI. Semantic review is still not proof; no real-provider or deployed verification, physical compatibility, full unit conversion, universal strict-adapter migration, productionp99 or ownerDR certification. All live flags remain false.

## Scoped constraint checkpoint, November24 07:35

PR110 and112 are merged after exact-head required CI: positive and negative ordinary catalog target/setup scope persist separately, union additions and reset only with the existing literal independently reviewed replacement. Target/component identity changes withhold rather than infer a new identity. Current SQL scope filters and post-copy checks remain. These changes supersede earlier pending110/per-target-exclusion notes, not semantic risk or all-live-false status. Source research remains informational evidence, never a claim the catalog satisfies hard requirements. PR112 post-push verification is still awaited by this snapshot. No owner/provider/DR action occurred.

## PR114-116 scoped checkpoint, November24 08:29

SEC-05: local synthetic actual-process HTTP/SQL/Redis/strict-adapter characterization
now recorded, GC enabled. Rerun steady p99=441.91ms/max754.34ms; allocationpressure
p99=155.07ms/max173.59ms, maxGC60.74ms. This is not fullapp/model/provider/remoteRedis
load evidence. Required exact100admit/50quota/<0.2s isolated gate unchanged. Earlier
ledger0.6s description is historical; current limiter queue+EVAL budget is1second,
Redis socket timeout0.5s. A stopped process/eventloop cannot honor a wallclock SLO.

SEC-04/06: PR115/116 migrate original recovery/productcopy and specialized synthesis
failure boundaries to strict adapter, typed errorlogs, cancellation and truthful
failure copy. Controlled adapter tests do not prove successful model entailment.
Unreviewed legacy ecosystem planner, successfulprose/sourcepolicy and optional
cartcopy still need scoped work. No original foundation or voice/cartmutation
path removed, no ordinary user rerouting into unreviewed legacy handlers.
No provider/owner actions or live flags promoted.

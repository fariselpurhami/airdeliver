# AI brain inspection: stage map and priorities

26November2026. First evidence-backed pass, not a completed exhaustive audit.
Code basis: Q01120758fa; source-truth additions17e90ce1are separate/inactive;
C01c3b9be32session preparation separate/inactive. Nothing merged or deployed here.

## Finding

Intent is already important, but not yet a shared durable organizing state.
The largest reliability problem observed is disagreement between separate prose,
identity/claim records and the actual decision. The independent reviewer catches
some semantic errors; fail-closed is essential but repeated withheld responses
are not product maturity. Preserve both orchestration foundations while measuring
parity, then add a single source-bound intent/decision contract rather than a
third competing engine. Do not equate longer answers with depth.

## Stage map

All service paths below are relative to backend/api/app/services/.

| Stage | Real implementation | Works under inspected evidence | Weakness / missing proof |
| --- | --- | --- | --- |
| Entry points | api/v1/endpoints/ai_support.py to conversation/neural_core_service.py; ai_ordering.py opening/reset to conversation/ai_nlu_service.py; orchestration/worker_entrypoint.py chat handler | Main support HTTP, opening/reset and worker code have real owners. Ordering WebSocket explicitly rejects commands and relays responses only. | Different surfaces are not one demonstrated end-to-end brain. Worker code existence does not establish deployed queue consumption. Voice remains last and is not accepted here. |
| Intent | RouterDecision/_analyze_intent versus GlobalCommerceIntentEngine/CommerceIntentPayload | Typed schema, exact user-span targets, bounded signals; current task and question propagate to writer/review. Test-first fix preserves neutral compare/understand without an emotional signal. | Two schemas/policies, competitor-priority legacy instructions and heuristic failure routing can disagree. Controlled tests do not prove multilingual/indirect-goal accuracy. |
| State | SessionMemory and AINLU MemoryStore; target_constraint_scope/constraint_continuity | Authenticated support session key is owner-bound; roles/history bounded. Retained target/setup requirements and explicit replacement checks exist. | Bounded history re-derives goals, preferences and decisions; preferred/rejected options, reasons and decisive missing evidence are not shared typed durable decision state. General max-weight is not a dedicated typed field. |
| Evidence planning | NeuralCore staged product/catalog search, query_rewrite, legacy search plan | Literal targets, bounded query rewrite, per-target evidence and partial-comparison disclosure paths. | Task label drives evidence work; no shared typed goal-to-evidence-needs plan. Semantic source selection and decision-blocking unknowns remain implicit. |
| Retrieval | catalog/ai_commerce_engine.py, retrieval/staged_search_service.py | Keyword/semantic concurrent work, bounded native admission, rank fusion, current SQL hydration/filtering, SQL fallback; ranker cannot add identities. | Exact-tier historical descending-price order is not intent/value optimization. No fresh human-adjudicated held-out ranking/recall benchmark; no million-catalog or production-load proof. |
| Source research | research/product_knowledge_service.py, tavily_boundary, research_evidence_budget | Bounded lookup, exact contiguous quotes, target coverage and independent source review. Empty source/catalog never proves nonexistent. | Active packer selects small term-scored windows that can omit context. Source-truth branch adds provenance/metadata guards, but publication/effective-date/model/market authentication adapter and active product-status route remain missing. |
| Writer | shopping_copy.py, compact_copy_contracts.py, reviewed_recommendation.py | Exact claims/names/IDs/numbers validated; structured transport; request snapshot; synchronous independent review retained. | Generated prose and claim lists lose bindings. Internal-ID leakage and missing comparison claims observed. Inactive template/segment variants did not solve fact-slot reliability. No silent ID stripping/guessed claim repair. |
| Semantic review | GroundingReview, RecommendationReview, SourceReview | Controlled real reviewer accepted correct mapping and rejected swapped material, unknown promoted to confirmed, explicit weight-limit violation. Offline replays preserve results. | Four contrasts are not reviewer accuracy certification. Same provider/model, boolean verdicts and input selection can share error modes. Structurally valid claims do not establish correct prose attribution. |
| Composition | sales_response_service, opening_batch_copy, customer_status, AIChatOverlay.tsx | Adaptive task shape, separate opening batch, operational status mapping, Markdown paragraphs/lists and separate action/cards.008/010real text-renderer pixels checked. | Different copy contracts/adapter budgets remain; text-renderer preview is not full app/card/action/accessibility acceptance. No fixed headings are required for depth. |
| Saved memory | memory/customer_memory_service.py, shopping_memory_policy, personalization_fence | Optional SQL taxonomy, explicit preference evidence, consent-generation locks, erase/publication fence, user-current words win. Legacy inferred vector recall disabled. | Learning-off and erasure intentionally differ. Cross-surface consistency, broad-language explicit preference support and durable decision continuity remain separate. No private personality inference. |
| Quota/failure | provider_capacity modules, free_llm_service and support adapter | Bounded turn/admission estimates, actual usage meter, quota axes, cancellation and honest notices have tests. | Estimated tokens are not exact tokenizer usage. Different adapter paths/budgets and all-worker/account enforcement need operational proof. No paid scale, production SLO or infinite free usage claim. |

## Tests actually run for this inspection

| Slice | Result | Scope |
| --- | --- | --- |
| Entry/intent/session/roles/router/reset |60passed | Controlled model adapters, no provider. |
| Staged retrieval/query/vector/spec/Tavily/attribution |98passed | No new provider/model download/store mutation. Initial bad filename ran no tests, corrected invocation produced this result. |
| Writer/review/opening/memory/status/quota usage |208passed,20skipped | Skips need DB/Redis; not counted as boundary proof. |
| Latest full local Q01 suite before audit-doc addition |2383passed,532skipped,22warnings | No claim skipped integration boundaries ran. Hosted exact-head CI is separate. |
| Product-truth direct binder |190focusedpassed | Five red direct-entry cases first. Inactive source preparation only. |

Counts overlap; do not sum them as unique coverage. Existing warnings include
Pydantic, AsyncMock and JWT test-key warnings. No new provider calls in this code
inspection. Prior development16requests/34306measuredtokens+8000unknown reserve,
not16successful replies. Old48/50experiment remains historical.

## Priority plan

1. **Intent parity baseline before a new layer.** Build paired/multi-turn cases for
   identical products but different goals, hard constraint changes, absent facts,
   and advised versus requested actions. Run actual support and legacy adapters
   on the same source-bound user turns. Acceptance: task, scoped constraints,
   evidence needs and next step agree without hidden inference or actions.
2. **Deterministic fact/identity interface.** Keep current gates/reviewer. Use the
   existing inactive experiment evidence to design one bounded proof of facts
   bound to product/field at authoring time. No duplicate engine, auto-claim repair,
   ID stripping or retry-until-pass. Acceptance: unseen domains and comparisons,
   with exact rendered evidence and same review/call/latency constraints.
3. **One additive source-bound decision snapshot.** Reuse explicit spans and
   retained constraint scopes; record user goal, decision under consideration,
   unresolved evidence, and permitted next step. Test current-turn updates,
   cancellation, persistence failure and stale state before activation. Do not
   turn inferred motive into fact or permission.
4. **Real product-truth adapter.** Authenticate publisher/model/publication
   precision/effective date/market. Keep historical release, current regional
   availability, discontinued status and merchant stock separate. Test natural
   dates, timezone/day precision, multi-product pages and conflicting regions.
5. **Retrieval quality against those intents.** Human-adjudicated held-outs,
   lexical/dense/fusion ablations, Arabic/mixed-language/no-match/constraints,
   current model/revision and p50/p95/p99/memory. Preserve historical ordering
   until a measured change is separately justified.
6. **Whole-route composition and operations.** Mounted HTTP/SQL/Redis, copy/review,
   stale-card/consent races and actual mobile/desktop UI; all adapters covered.
   Only then owner quality acceptance and separately authorized rollout.

## Not yet inspected exhaustively

The large legacy pipeline is not line-by-line finished. Remaining targeted work:
all downstream command/plan handlers, behavior and meta-cognition influence,
opening/legacy parity, cancellation across native work, generated frontend action
handling, full consent-erasure races, benchmark labels and operational queue
wiring. Repository names/comments such as elite, cognitive or confidence are not
proof of capability. No comparison against external frontier models is established.

## Source records

- Source file paths and tests listed above, exact revisions at the top.
- intent-first-architecture-audit-v1.md, shopping-development-receipt-v2.json.
- Separate product-status-evidence-preparation-v1.md and source compatibility audit.
- PR266/267/268 preserve one-item separation and unaccepted rollout gaps.

## Follow-on behavior and dormant-path inspection

46focused behavior/meta/adapter tests passed,22Redis-dependent skips. The active
meta-cognition implementation intentionally reports unavailable/uncalibrated and
never grants transaction authority. No learned confidence artifact is proved.
Active synthesis and genius-response facades call reviewed_legacy_answer; old
forceful sales templates inside *_legacy_unreviewed methods are retained dormant
source, not evidence those instructions run on current customer traffic.

A distinct live-code concern remains: _handle_initial_suggestions_bounded calls
BehaviorEngine.analyze_financial_dna, which classifies recent price history by
fixed150/800thresholds and passes its tier to get_fresh_homepage_matrix. That tier
can affect fallback price ordering. The price list has no currency normalization
in that routine, and observed prices are not a person's explicit budget, wealth
or intent. Code-path evidence establishes influence, not a harmful observed live
outcome. This needs an intent-versus-behavior contrast test and a preserving design
decision, not deleting the behavior foundation or silently changing all ranking.
Do not mistake persona/segment vocabulary for authenticated personal facts.

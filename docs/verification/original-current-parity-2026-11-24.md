# Original-to-current behavior audit

November24,2026. Baseline: original pre-hardening commit8b82cf3; current9fdd1e8 (PR71 withdrawal head, not yet merged). Repository history contains the four originals; no resend is currently needed. No provider calls, owner-machine actions or stored-data changes performed.

## Scoreboard: 35 preserved, 15 degraded, 5 lost

These are the existing55 grouped inventory rows, not independent feature counts. Some rows overlap. Lost means no equivalent intended behavior in ordinary HTTP chat, even if a legacy method still exists. Preserved means code/path parity, not live certification. Dormant original helpers are marked preserved with an explicit dormant caveat.

All original named functions remain:42 FreeLLM,57 engine,27 cart,142 NLU definitions. Names alone do not prove behavior parity. The existing coverage ledger had stale wiring descriptions and is not a substitute for this audit.

## Highest-priority losses

1. Fresh web evidence for product questions, regardless of catalog availability. Specs, comparisons and consultation must not require a stocked local card. Restore a general source-level evidence contract, exact product identity, attributable claims and honest unavailable outcomes. No manufacturer-only shortcut.
2. Ecosystem/setup planner and separate component discovery, with evidence-backed compatibility rather than original name-based harmony claims.
3. Image identity/title enrichment and context-aware query rewriting in addition to vector retrieval. Identification uncertainty must remain visible.
4. Full constraint and strategy bridge: RAM/storage, exclusions, per-target missing evidence, persona/retention strategy, without invented budgets or fake urgency.

## Important retained or restored behavior

Hybrid retrieval/fusion/SQL fallback, current-row cards, staged per-target catalog search, gift clarification, cart operations, read-only model cart followups and model opening/Insight all have source paths. Opening rate429, card grounding rejection and freshness exhaustion are degraded reliability, not proof those paths are missing. Voice is a separate retained provider path, not live-certified. Payment/carrier/handoff completion is outside the four-file parity claim.

## Evidence anchors

- Historical8b82cf3 four service files and old websocket-to-worker browser flow, including original NLU pipeline2224..2452, ecosystem2704, vision3333, web3878, synthesis3949, specs5030.
- Current NeuralCoreService._handle_staged_product_search, _catalog_response, _shopping_response, _handle_visual_search and _handle_message dispatch.
- Current FreeLLMService.consult_catalog explicitly disables web evidence; consult_on_product delegates to it while _legacy_consult_on_product still contains the old lookup.
- Current worker._cart_recommendation_observed -> CartSalesService; opening _generate_dynamic_row_copy -> generate_lifestyle_matrix -> write_opening.
- Original semantic writer invokes fact= but engine signature accepts fact_text; original recall and idle/implicit helpers have no discovered traffic caller.
- Current controlled full-suite PR71 withdrawal run:1227passed5skipped. No claim this suite certifies all behavior or live model quality.

Machine-readable companion JSON contains original and current method/class line anchors and mapped test leads for every row. These are implementation anchors, not a claim that each method is reached by ordinary HTTP.

## Full canonical matrix

| ID | Status | Capability | Finding |
|---|---|---|---|
| CAP-01 | preserved | SearchFilter parsing, validation, cache serialization, input normalization | Implementation and intended active source path retained; see mapped tests. Preserved means source-level behavior, not deployed/provider certification. |
| CAP-02 | preserved | ModelRegistry text and vision loading, device/dtype, startup rejection/readiness | Implementation and intended active source path retained; see mapped tests. Preserved means source-level behavior, not deployed/provider certification. |
| CAP-03 | preserved | Collection/index bootstrap and intent hydration | Implementation and intended active source path retained; see mapped tests. Preserved means source-level behavior, not deployed/provider certification. |
| CAP-04 | preserved | Query embedding, model readiness and inference admission | Implementation and intended active source path retained; see mapped tests. Preserved means source-level behavior, not deployed/provider certification. |
| CAP-05 | preserved | OpenSearch plus Milvus text retrieval, reciprocal-rank fusion, cache IDs, current SQL row hydration, SQL fallback | Implementation and intended active source path retained; see mapped tests. Preserved means source-level behavior, not deployed/provider certification. |
| CAP-06 | preserved | Complement bundles, explicit complement evidence, active/stock checks | Implementation and intended active source path retained; see mapped tests. Preserved means source-level behavior, not deployed/provider certification. |
| CAP-07 | degraded | Fresh homepage matrix, tier/freshness exclusions and fallback selection | Opening is still wired, but lifetime seen filtering can exhaust a bounded candidate set; daily real-data rotation PR70 remains unmerged. |
| CAP-08 | preserved | Genius alternatives with category and price window | Implementation and intended active source path retained; see mapped tests. Preserved means source-level behavior, not deployed/provider certification. |
| CAP-09 | preserved | Image vector encoding/search and OpenSearch materialization | Vector image retrieval retained with fresh SQL hydration at HTTP publication. Image identity enrichment is tracked separately at CAP25/49. |
| CAP-10 | preserved | Product ID fetching, common filters and SQL fallback | Implementation and intended active source path retained; see mapped tests. Preserved means source-level behavior, not deployed/provider certification. |
| CAP-11 | preserved | Semantic user-fact insert and similarity recall | Original semantic recall had no traffic caller. Original writer hook used incorrect fact= keyword against fact_text, so successful original persistence is not established. Retained, deliberately gated, not a working-memory regression. |
| CAP-12 | preserved | Milvus connection retries/backoff and OpenSearch client lifecycle | Implementation and intended active source path retained; see mapped tests. Preserved means source-level behavior, not deployed/provider certification. |
| CAP-13 | degraded | RAM/storage extraction, broad-query cleanup, search constraints | Original capacity/constraint helpers retained in NLU. HTTP ShoppingBrief does not carry the full RAM/storage/exclusion contract. |
| CAP-14 | degraded | Typed product-target array, occasion, sentiment, intent, cart action and deduplication contracts | Separate literal targets and task now flow through HTTP, maximum3 targets; original richer occasion/sentiment/cart contracts are not fully bridged. |
| CAP-15 | degraded | Persona, retention modes, four-phase response policies and sanitizer | Reviewed model prose is wired, but original persona/retention/four-phase strategy is not fully represented by current HTTP contract. Unsupported secrecy/stock claims must not return. |
| CAP-16 | preserved | Product serialization and JSON sanitation | Implementation and intended active source path retained; see mapped tests. Preserved means source-level behavior, not deployed/provider certification. |
| CAP-17 | preserved | Correlation logs, bounded task supervision, distributed locks/idempotency | Implementation and intended active source path retained; see mapped tests. Preserved means source-level behavior, not deployed/provider certification. |
| CAP-18 | degraded | Recent Redis conversation memory, consented saved-shopping preferences and behavior/DNA cache | Recent HTTP session and consented saved color/material/style hints connected; behavior/DNA and full original NLU history are not unified into ordinary text. |
| CAP-19 | preserved | UI Redis gateway, typing, payload types and strict row publication | Implementation and intended active source path retained; see mapped tests. Preserved means source-level behavior, not deployed/provider certification. |
| CAP-20 | degraded | Global model intent router with heuristic failure route | HTTP has a model router, not equivalent original intent taxonomy. Ecosystem intent absent; fallback is an honest system notice. |
| CAP-21 | preserved | Welcome/internal/reset/cancel/sync command router | Implementation and intended active source path retained; see mapped tests. Preserved means source-level behavior, not deployed/provider certification. |
| CAP-22 | degraded | Smart cart actions and text commands | HTTP add/remove review is real and confirms before mutation, but richer smart-cart planning/commands remain separate. Do not restore inference-selected side effects. |
| CAP-23 | lost | Ecosystem planner, component searches and collection prose/cards | Original pipeline invokes ECOSYSTEM_BUILDER and component searches. Ordinary HTTP router has no ecosystem intent or component-planning dispatch; legacy method still exists. |
| CAP-24 | degraded | Opening matrix: personal/bestseller/trending/deal pools, diversity, freshness, stages and streaming | Model opening/Insight was restored via generate_lifestyle_matrix -> write_opening. Owner observed429 and grounding rejection; four concurrent writer/review chains remain. Seen exhaustion remains pending PR70. |
| CAP-25 | lost | Vision identification and query optimizer with recent-context references | HTTP images bypass intent and go directly to image-vector search. Original _resolve_vision_query -> analyze_product_image and context query optimizer are not reached. |
| CAP-26 | degraded | Universal per-target search; strategic exact/ranked/mid/broad search; ranking/alignment | Shared staged_search now connects HTTP and NLU exact/ranked/mid/broad tiers. Full original optimized-query/constraint planning is not yet equivalent. |
| CAP-27 | preserved | Older _execute_search exclusion/price filtering and smart alternatives | Original _execute_search itself had no pipeline caller, unlike _execute_strategic_search. Retained; its over-budget fallback is not an authority to bypass current hard budget. |
| CAP-28 | lost | Informational web/spec/comparison synthesis, targeted specs, main product prose, missing-product recovery | Original _synthesize_response/_safe_web_search provide informational web synthesis and enrichment. Ordinary HTTP uses card-only writer, so noncatalog specs/comparisons fail or lack fresh web facts. |
| CAP-29 | degraded | Multi-target extraction versus informational query concatenation | Current per-target retrieval is improved over original combined informational query, but per-target web source acquisition/completeness is absent. |
| CAP-30 | degraded | Consent-aware memory collection and seen-product persistence | Consented preference collection exists in HTTP and NLU; HTTP browsing and original seen/behavior completion do not have full equivalent coverage. |
| CAP-31 | preserved | Legacy inferred memory, implicit behavior update, idle nudges, dynamic time/nudge templates | Idle/implicit/dynamic helpers had no active trigger/caller in original; inferred memory was broken by keyword mismatch. Retained, consent-gated or dormant, not promised live. |
| CAP-32 | degraded | Removal recovery alternatives and optional confirmation prompt | Read-only optional removal worker uses model copy/current rows; original rich reason/strategy recovery is not completely shared. Same-category bounded window is retained without superiority claim. |
| CAP-33 | preserved | Meta-cognition strategy hooks | Strategy hooks retained, but calibrated learned confidence was not established in original. unavailable assessment is honest gating, not restored quality. |
| CAP-34 | preserved | Validated cart/item/operation contracts and decimal totals | Implementation and intended active source path retained; see mapped tests. Preserved means source-level behavior, not deployed/provider certification. |
| CAP-35 | preserved | Authoritative Redis load/sync, compare-and-set updates and mutation receipts | Implementation and intended active source path retained; see mapped tests. Preserved means source-level behavior, not deployed/provider certification. |
| CAP-36 | preserved | Add mutation, publication/stage timing and optional recommendation event | Implementation and intended active source path retained; see mapped tests. Preserved means source-level behavior, not deployed/provider certification. |
| CAP-37 | preserved | Direct intelligent bundle fetch and model sentence, bounded timeout and fallback | Optional worker now calls CartSalesService shared model writer/reviewer with current complement rows; legacy direct helper retained. Tests cover SQL, Redis and actual AMQP boundary separately. |
| CAP-38 | preserved | Save cart as cancelled-order record/list | Implementation and intended active source path retained; see mapped tests. Preserved means source-level behavior, not deployed/provider certification. |
| CAP-39 | preserved | Remove mutation, alternative retrieval, model analysis/copy and fallback reasons | Remove mutation and asynchronous alternative advice are connected. Fresh cart membership/evidence checks preserve no-replay mutation boundary. |
| CAP-40 | preserved | Analytics and removal/conversion-adjacent events | Implementation and intended active source path retained; see mapped tests. Preserved means source-level behavior, not deployed/provider certification. |
| CAP-41 | preserved | Clear cart and pending-order cancellation | Implementation and intended active source path retained; see mapped tests. Preserved means source-level behavior, not deployed/provider certification. |
| CAP-42 | preserved | SearchStrategy, RecommendationResponse and interaction response contracts; sanitizers and limits | Implementation and intended active source path retained; see mapped tests. Preserved means source-level behavior, not deployed/provider certification. |
| CAP-43 | degraded | Singleton/client lifecycle, configured models, admission, deadlines, retries and completion transport | Transport and bounds retained;429 retry ignores Retry-After and opening fans out four chains. Owner failure is confirmed; rate-limit remediation not merged. |
| CAP-44 | degraded | generate_response plain/JSON/context adapter | Legacy generate_response still returns empty string on provider failure. Reviewed adapters withhold unsupported sales copy but not all legacy callers have typed failure handling. |
| CAP-45 | preserved | Spontaneous scene/vibe and lifestyle matrix | Opening generate_lifestyle_matrix -> write_opening now produces reviewed model intro/Insight. Original random scene/vibe helper stays retained; invented context is not evidence. |
| CAP-46 | preserved | Strict shopping-preference extractor | Implementation and intended active source path retained; see mapped tests. Preserved means source-level behavior, not deployed/provider certification. |
| CAP-47 | preserved | Legacy memory-worthy fact extractor | Extractor retained. Unconsented original inferred-memory writer is intentionally not reactivated; consented collector replaces its customer traffic purpose. |
| CAP-48 | preserved | Visual-context explanation | Original analyze_visual_context had no caller outside its service. Remains dormant, not a confirmed lost normal-chat capability. |
| CAP-49 | lost | Product-image identification and optional Tavily title enrichment | Product-image identity and optional Tavily title enrichment remain in FreeLLMService but ordinary HTTP image requests only call vector retrieval. |
| CAP-50 | lost | Tavily web search | Tavily method remains in legacy NLU/voice; ordinary text/spec/comparison/consultation no longer acquires fresh web sources. |
| CAP-51 | degraded | Product consultation with web/context/history | consult_on_product now delegates to consult_catalog, explicitly external_web_evidence=False. Structured catalog consultation retained; original web/context behavior is not equivalent. |
| CAP-52 | preserved | Model search strategy and deterministic failure strategy | strategize_search retained in internal handle_commerce_interaction. That orchestrator had no external original caller; do not call it a removed normal-chat path. |
| CAP-53 | preserved | Search-term extraction / English rewrite | extract_search_terms retained in same dormant orchestrator. Separate active NLU optimizer bypass is included under CAP26. |
| CAP-54 | preserved | Local relevance ranking, grounded-ID recommendation and factual intro/reason | Local ranking/grounded selection retained; shared HTTP model writer is connected. Original orchestrator route was dormant, not proof of live coverage. |
| CAP-55 | preserved | Parallel strategy/term commerce orchestrator with consultation/carousel branches | Original parallel orchestrator already had no external caller. Retained, not counted as newly lost. Its useful contracts should be integrated rather than adding a competing pipeline. |

## Release rule and remaining acceptance

Each restoration requires an intended-entrypoint regression that fails before the change, source/identity/outage/cancellation coverage and existing hard constraints. SQL/Redis/AMQP/HTTP integration tests do not establish real model accuracy. Real provider quality remains an owner-approved acceptance gate.

PR71 removes only synthetic preview behavior, preserving stored records. PR70 real-data daily rotation must be rebased afterward. The initial source-spec draft is unpushed and incomplete, it must not be treated as restored universal lookup.

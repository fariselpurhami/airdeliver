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

## Reproduced concurrent intent-state loss

Controlled simultaneous support requests sharing a session hydrate separate copies
of the same state, then last-write-wins SET loses one turn: expected2, stored1.
An explicit strict-xfail regression records the desired invariant without calling
this gap passed or hiding a failing test as acceptance. No provider/real session
was touched. Each write being awaited is not cross-request serialization.

Existing infrastructure already has atomic compare_json_required and owner reset
generation fences, but support session hydration/persistence uses resilient get/
set paths and has no per-session revision/lease across the full turn. A correct
fix must decide concurrent-turn behavior: bounded serialization versus rejecting
stale snapshots before publication. It must work across workers, preserve owner
reset fencing, detect lease expiry, and never silently merge contradictory hard
constraints. A process-local lock or append-only history fix would not settle
in-flight answers based on stale intent. Distributed Redis/cancel/outage tests are
required before claiming this fixed. This is now a priority alongside writer
reliability, ahead of adding a durable decision state on unsafe persistence.

Follow-on controlled failure/cancellation cases: a forced write outage still
publishes an ordinary conversation reply with no durable turn. The proposed
continuity-notice invariant is recorded as a second strict expected failure,
not an implemented product-policy choice. Cancellation before model completion
leaves no half-turn, and simultaneous different sessions retain their own turns.
Combined local slice:9passed,2expected failures. These are controlled-cache
service tests, not mounted HTTP/real Redis or cancellation-at-every-boundary proof.

### Smallest distributed-state design candidate, not activated

Prefer stale-snapshot rejection before publishing over holding a distributed
lease throughout model calls. Reuse existing atomic compare semantics, but the
support commit must atomically compare the exact hydrated snapshot AND the owner
reset generation/reset-pending state. Checking generation then doing a separate
CAS leaves a reset race. Generic compare_json_required alone is insufficient.
An anonymous session still needs snapshot CAS; authenticated keys remain owner
bound. A missing cache value and a failed read must be distinguishable. Commit
must return explicit committed/stale/reset/unavailable status instead of logging
and swallowing failure. No provider retry, hidden replay, silent constraint merge
or global/process-local lock. Only a committed current snapshot can publish an
ordinary answer; rejection should return an honest retry notice. UX wording is
still a product-policy candidate, not established user approval.

Tradeoff: CAS intentionally makes one concurrent request retry rather than
preserving both automatically. It avoids queueing provider calls behind a lease,
lease renewal/expiry complexity and stale answers, but the user experience and
all entry points need agreement. Reset-pending, generation change, stale snapshot,
write outage, read outage, TTL expiry, cancellation and owner isolation require
real temporary Redis tests, plus HTTP response proof. Legacy queue memory is a
separate state owner and cannot inherit support safety from this design.

## Queue and native-cancellation follow-on

31focused worker/vector/vision tests passed,2temporary-Redis cases skipped locally;
26additional embedding/staged-search/intent tests passed (overlapping prior
inspection counts, not a unique total). Native text/vector/vision calls retain
shared capacity until the underlying thread finishes after caller timeout/cancel.
Timeout is not proof native work stopped. Staged CandidateRanker.rerank is lexical
bounded work, not another hidden model call. semantic_trim has no active call in
the inspected NLU module, so its direct encoder is not labeled an active leak.

Legacy process_message locks a user+message-content fingerprint, not the entire
user/session. Different concurrent messages are not serialized by that lock.
Legacy history append uses Redis LPUSH/LTRIM/EXPIRE under reset-generation fencing,
not the support whole-snapshot SET. Therefore the reproduced support lost-update
mechanism must not be attributed to legacy without its own contrast test. Ordering
of concurrent user/assistant turns remains unverified. Worker creates a fresh NLU
service per chat delivery, so instance _current_intent_payload is not evidence of
cross-delivery sharing in that route. Generic retries do not establish exactly-once
copy publication; cart uncertainty has a distinct non-replay path and is not chat.

Frontend ordinary text routes to support HTTP; only explicit button commands enter
mutation routing, then checkout opens a shipping step rather than direct payment.
CANCEL_INTENT in the legacy handler means order cancellation, not cancellation of
an in-flight answer. Frontend loading gate reduces same-tab text overlap but does
not settle multiple tabs/devices, image requests or API callers. Its support fetch
has a local45second controller. resetChat changes session state without a visible
support-request generation guard in the inspected path. A delayed pre-reset reply
potentially rendering afterward is a source-level concern requiring a mounted
frontend deferred-response test, not a reproduced UI incident or a server
privacy-fence bypass. Keep server reset publication fencing and client stale
response suppression as different obligations.

## Behavior price-scale characterization

8controlled tests including public facade passed. Actual classifier, no model
allocation:20observations100each gives LOW;1000each gives HIGH;19at100plus one15000
gives HIGH. Missing/negative/nonfinite observations return MEDIUM. A synthetic
numeric rescaling changes tier with no explicit goal input, confirming fixed-scale
average sensitivity. This is NOT an asserted exchange rate, prediction of wealth,
or a held-out ranking benchmark. Source code shows downstream tier affects fallback
candidate selection. Those facts justify further intent-first contrast testing,
not deleting behavior code or changing all ranking. Owner explicit budget/current
intent should be the grounding, not inferred affordability from viewing prices.

## Paired intent metadata grounding audit

20controlled adapter/goal/contract tests passed. For the same neutral explicit
Atlas product request, injected legacy structured output retains unsupported
budget999ornegative1and URGENT/FRUSTRATED labels; support drops unsupported budget
and sentiment. Legacy does remove an invented competitor. These are controlled
parser/postprocessing contrasts, not measured model misunderstanding. Tests assert
observed behavior to make the mismatch visible, not certify it as desired policy.

Important impact boundary: budget_max has no downstream read in this inspected
legacy module. Sentiment-specific persuasive instructions found at6153onward are
inside dormant _generate_genius_response_legacy_unreviewed, not the active writer.
The active reviewed_legacy_answer re-extracts a current grounded brief and does not
forward sentiment or inferred budget into writer evidence. Therefore metadata
mismatch is proved, harmful current budget filtering or emotional prose is NOT.
Category still selects strategic/informational search, source lookup and writer
task. Legacy competitor-priority prompt can disagree with task-first support
policy; an actual held-out classification/route consequence needs separate proof.
Do not attribute dormant tone instructions to current customer traffic.

Next useful parity cases: identical named products with explicit price versus
material versus suitability goals, changed hard constraints, incomplete facts,
competitor merely used as a source, negated action and current-versus-prior goal.
Assert normalized source-bound task/evidence/next-step state across real adapters,
not exact prose or inferred motives. Preserve both foundations; avoid adding a
third parser until mismatch evidence defines the shared contract.

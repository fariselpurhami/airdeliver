# Intent-first architecture audit

Owner direction: authenticated messages phonemsg-01M8B320J78GRABA7HXN97VTRJ and
phonemsg-01M8B342J9SD5STPXK786Z3RD8, November26. Intent is to be the organizing
foundation, not a prompt label. This audit describes code, not deployment proof.

## What is real

| Layer | Existing code | Evidence and limit |
| --- | --- | --- |
| Understand the present turn | conversation/neural_core_service.py RouterDecision and _analyze_intent | Typed action intent, shopping task, advice goal, exact targets, brief and explicit customer signals. Current/history user spans ground many fields. A schema-valid task is still a model interpretation, not proved correct. |
| Preserve constraints | SessionMemory, _handle_message_with_context, constraint_continuity.py and target_constraint_scope.py | Brief and target/setup constraints persist. Explicit replacement gets a separate check. History is bounded to five turns. No durable explicit goal/decision ledger exists. |
| Choose evidence work | _handle_staged_product_search and _handle_staged_catalog_search | Comparison/specification/consultation can enter researched answers; search/price/objection follow catalog routes. Each target is represented and current SQL facts rechecked. Typed task controls work, but exact practical purpose and decisive unknowns are not a shared typed contract. |
| Design the answer | product_answer_policy.py and sales_response_service.py | Listed-price gets short shape, most other catalog tasks adaptive. Advisory strategy distinguishes concern/price/general evidence. Cards/brief/request evidence are snapshotted. Shape remains coarse; a strategy label is not a complete intent model. |
| Bind facts and identity | shopping_copy.py | Exact claim field equality, names, IDs and numeric gate before independent review. Separate generated prose/claims still lose bindings. Inactive reference/segment experiments are not solved writer reliability. |
| Check meaning | GroundingReview | Four required booleans include task fulfillment. Four controlled live-review contrasts accepted correct material facts and rejected swaps, unknown-to-confirmed and hard-constraint violation. This is targeted evidence, not reviewer accuracy certification. |
| Carry a decision forward | SessionMemory.history and retained constraints | Conversation and hard constraints survive within limits. Preferred option, rejected option reasons, decisive missing evidence and next decision are not typed durable state. Re-derivation can drift. |
| Keep actions separate | Cart review handlers and checkout navigation | Intent does not authorize an external action, payment or factual assertion. This separation must remain. |

Paths in the table are under backend/api/app/services/ unless named otherwise.
The healthy support and shared sales adapters converge, but legacy recommendation,
opening, research and consultation interfaces differ. Passing a direct sales
harness does not certify router, retrieval or these adapters end to end.

## Where the foundation is still partial

1. A broad PRODUCT_SEARCH plus shopping_task does route work, but does not encode
   what decision the person is trying to make or why an unknown blocks it.
2. advice_goal and customer_signal are transient router fields, not a versioned,
   source-bound decision state across turns. Hard constraints are better retained
   than intent/decision continuity.
3. Current bounded brief has no typed general max-weight constraint. A weight
   requirement may live in required_features or current text, leaving arithmetic
   and task-fit semantics to filtering/review rather than an explicit decision rule.
4. Retrieval query normalization is reviewed and never fact evidence, but many
   paths still begin from a named query/category. Source-selection planning is
   mostly task-driven, not a documented evidence-needs plan.
5. Product-truth date/model/market adapters remain inactive/missing. Correct intent
   cannot compensate for absent source authentication or merchant inventory.
6. Current real held-outs are small. Two writer+review successes and several
   fail-closed replies do not establish maturity, consistency or broad depth.

## Next slice, not an activated redesign

An additive intent snapshot should separate explicit user goal, immutable source
spans, hard constraints with scope, current decision, unresolved evidence needs,
and authorized next action. It must retain uncertainty rather than claim access
to hidden intent. New current words should update scoped fields, not silently
replace unrelated constraints or revive old preferences. Reuse the same snapshot
for evidence planning, writer, reviewer and follow-up evaluation.

Before implementation, contrast pairs must distinguish identical products with
different goals: material lookup versus outdoor-use suitability; price lookup
versus negotiation; lighter choice versus medical comfort; current local listing
versus merchant arrival guarantee; comparative advice versus purchase instruction;
new preference versus explicit hard-constraint replacement. Each has a positive,
negative/unknown, and multi-turn continuity case. Success includes the right
next step or no-pick, not response length or fixed headings. No automatic actions,
new provider spend, extra synchronous stages or activation is approved by this doc.

A new intent layer must not replace existing foundations or conceal failures.
Existing synchronous writer/reviewer remains, no ID stripping or guessed claim
repair, and owner quality acceptance stays separate from code/CI acceptance.

## Semantic contrast regression checkpoint

Captured controlled drafts now replay through the actual preflight and independent
review boundary. The correct mapping passes; swapped facts, unknown-as-confirmed
and explicit weight-limit violation pass structural equality but fail the captured
review verdict. This explicitly demonstrates why structure alone is insufficient.
17focused tests pass,7DB-dependent cases skipped locally. No claim of running
those7or fresh provider review during replay. Next intent-contract work must keep
this distinction between evidence-valid shape and decision-valid meaning.

Seven controlled intent contrast tests now exercise actual _analyze_intent and
shared writer/reviewer propagation: same card, different material/call-use/price/
negotiation/objection/comparison goals, plus a prior price turn changing to missing
microphone evidence. Current question, task, strategy and evidence reach both
stages unchanged; ungrounded urgency, competitor and customer signals are cleared.
24related tests pass. Controlled router/writer outputs mean propagation proof,
not real intent-recognition accuracy. No new active intent state was introduced.

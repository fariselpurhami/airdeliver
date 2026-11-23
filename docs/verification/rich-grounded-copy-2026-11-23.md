# Rich, grounded recommendation and welcome copy candidate

## Contracts and state

Preserves CognitiveResponse fields, selected-ID grounding, recommendation ranking, welcome row event types and content/reason string fields. Optional compare_to_id is additive; no first-product or query-text anchor inference. Last Groq acceptance request stays unused. No dependency upgrade, deployed model switch, migration or customer-memory widening.

Current behavior defect: selected-ID checks did not validate reasons; welcome row copy accepted arbitrary JSON prose, and deterministic fallback invented personalization/premium/market-trend claims. The row-copy method only exposed3names/categories. New renderer computes bounded catalog clauses and explicit current-set price/rating/tie comparisons, attributes only from supplied material/style/use fields. Null/invalid rating stays unknown rather than displayed as zero. Unknown price is never free. Reference deltas need explicit current reference ID. Catalog attribution is not independent truth verification.

LLM editorial mode remains: it receives current bounded item facts plus allowed item-bound claims, chooses and orders claims with approved connectors, returns typed claim bindings. Server renders the verified content/reason strings. Free-form model prose is rejected and replaced with rich factual fallback. This is constrained editorial composition, NOT a semantic entailment model and NOT unrestricted bespoke prose. If the desired style requires arbitrary novel wording, that quality target remains unproven and needs separate labeled entailment evaluation. No hidden second-model validation call.

Greeting no longer fabricates current search or local time-of-day. Existing row selection remains, but its bestseller/trending/personalization heuristics are not certified. Existing confidence_score is model/fallback confidence, not calibrated relevance evidence; user-interface treatment still needs explicit evaluation. Other AI routes beyond recommendation filter and welcome-row copy are outside this patch.

## Evidence and tests

Local982passed4skipped20warnings on candidate before latest-main joint integration. Tests exercise model-copy success, invented/failing output, exact typed claim bindings, wrong/cross-item claims, connectors/HTML/schema rejection, intro/fallback grounding, unknown numeric facts, decimal deltas/ties/currency, and HTTP response serialization. No provider request made. No deployed UI, long-copy mobile/RTL, fresh catalog read-through or learned semantic quality qualification yet.

A60case human-reviewed evaluation set is planned in docs/catalog/README.md on the separate manifest branch:20alternatives,20complements,20sparse/conflicting/adversarial cases, SKU-family holdout, exact snapshots, two reviewers, factual precision/relation precision separated from relevance/detail/readability scores. No such merchant-labeled set exists yet, so quality is NOT proven.

## Gates

BE contracts/local tests pass for inspected paths. Security/factual scope is bounded by catalog truth, not inferred world knowledge. Resource tests only bound copy/item counts; performance/real provider behavior NOT RUN. FE contract shape preserved, browser visual/RTL/error-state gates NOT RUN for rich copy. Main joint integration and CI pending. Not production-qualified; no blanket40point score. Parent review required before merge, with clear caveat about constrained LLM wording.

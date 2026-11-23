# Shared staged per-target retrieval restoration

November23,2026. This focused step reconnects staged retrieval and separate product targets. It does not claim the entire legacy consultation/web/search-planning capability is restored.

## Current path

Router optionally returns at most three literal customer product/category targets and a search/comparison/specifications/consultation task. Every target must occur in customer-authored recent context; invented targets fall back to clarification. Model wording is not an execution instruction, product identity or commercial evidence. Prior single-query behavior remains for a router response without targets.

HTTP runs targets sequentially against the shared SQL session, five-second total search budget per target and24-second total staged evidence/write/review budget. Partial timeout/failure withholds the complete comparison rather than quietly pretending all targets were checked. Up to three targets can make up to nine search calls: high30, mid10, broad5. The existing provider writer/review eight-second total cap remains.

Shared staged-search service preserves historical NLU high-exact, high-ranked, mid-ranked and broad tiers, deduplication and bounded results. Existing NLU strategic entrypoint calls it, while old implementation is retained explicitly as legacy. Exact-tier historical descending price order is preserved, not asserted as a value ranking. Category restrictions survive broad fallback rather than being dropped. Search tier is not exact identity, fit or stock evidence.

Round-robin candidate selection gives each target a chance under the shared five-card cap. Fresh SQL card construction, budget/stock/demo labels, model-only prose and independent review remain. Response evidence records target, retrieval tier and retrieved IDs, explicitly not proof of a commercial claim. Missing target/spec/compatibility evidence stays unknown. Cards are reread after model work, and changed fields withhold stale output. Existing single-target alternatives remain, not a fabricated cross-target substitute.

## Evidence and limits

1156passed,4skipped full disposable PostgreSQL19/realRedis backend suite. Twelve new tests cover every tier, preserved category filters, cancellation, literal target grounding and mounted HTTP routing through real SQL and Redis history. Controlled search return values and model transport are explicit boundaries. Price changing during generation withholds; missing second target remains identified as no_match in writer evidence. No actual model/provider calls, real indexed-search recall claim or persuasive prose quality score.

Next focused steps: richer explicit constraints and target-specific comparison coverage; safely reconnect existing consultation/search strategy and web-source handling without trusting raw web snippets as instructions. This PR uses current structured catalog specs only. No general-knowledge web answer is passed off as catalog evidence. No dependency/schema/image changes, no owner rollout or migration.

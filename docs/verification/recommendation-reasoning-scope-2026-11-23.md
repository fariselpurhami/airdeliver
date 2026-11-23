# Recommendation reasoning restricted to selected products

Reasoning-key filtering now runs for every parsed model result, not only when selected IDs included an invented product. A valid selected-ID list can no longer pass along reasoning attached to unselected or nonexistent IDs. Selected-product reasoning and existing catalog fallback preserved.

Regression runs under both existing async backends. Full local PostgreSQL19/Redis suite804 passed,4 skipped,20 existing warnings. No model/provider calls. This enforces ID/key scope, not factual accuracy of free-text reasons about a valid selected product.

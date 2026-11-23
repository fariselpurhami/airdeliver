# Explicit unknown catalog price in model/ranking data

FreeLLMService sanitization now emits price=null,price_status=unknown for missing/invalid/negative/nonfinite prices, distinct from an actual listed0.00. Re-sanitization preserves unknown. Ranking, lifestyle selection and fallback sorting handle null. Model user JSON carries price status/currency and policy says unknown never means free. Removed unsupported fallback price-praise wording.

Tests cover missing/invalid/boolean prices, listed zero, repeated sanitization, actual model-message JSON and mixed-price lifestyle fallback. Full local832passed4skipped20warnings real PG19/Redis, controlled model outputs only. No provider requests.

Scope incomplete until UI update: existing AIChatOverlay product card still coerces null to0.00. This checkpoint establishes backend semantics but does not claim customer display is fixed. Next frontend checkpoint must render Price unverified and avoid a priced add action for unknown prices, with tests/build and actual visual inspection. Current checkout still rechecks catalog.

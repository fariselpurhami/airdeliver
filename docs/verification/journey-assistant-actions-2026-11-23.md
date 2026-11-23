# Journey item1: explicit reviewed actions, partial, human handoff held

Separate unmerged change based on main424741d. No provider/LLM/email/payment request or owner data/deployment/migration. Existing model-driven routing extended, not replaced by a keyword/rule-based conversational substitute.

- Model can propose CART_ADD/CART_REMOVE with named product/quantity. Target must appear literally in customer's message and resolve to exactly one normalized catalog name, then fresh DB product. Ambiguity asks clarification. No inference-driven mutation.
- Typed review_cart_change proposal carries server-created stable UUID review ID, product/currency/quantity and operation. Explicit confirmation button uses existing authenticated cart endpoints, with stable idempotency key, then refreshes authoritative cart. No auto-execution. Uncertain outcome locks the button and routes to cart refresh, no blind retry. Removal explicitly means entire line. Catalog/stock revalidated at mutation boundary.
- Both Air Assistant and Order with Air render the shared action UI. Ordering response no longer drops structured actions. Air Assistant uses existing authenticated API client, so owner context reaches backend.
- Tracking action opens only a validated local order path. Human-handoff renders an honest unavailable state and existing help page; it creates no ticket or callback. Actual support queue/destination is unresolved and this item is NOT complete.
- Ordinary typed text no longer executes destructive substring commands, e.g. a negated clear-cart sentence cannot clear it. Existing explicit UI internal command path retained.
- Help text no longer promises live merchant inventory or a human line that is not connected. Existing help sections/components retained.

## Tests

Full disposable migrated PostgreSQL19/Redis backend1010passed4skipped before stable review-ID refinement; focused latest4passed. RealDB+Redis+HTTP acceptance: proposal alone changes nothing, customer confirm maps exact ID/quantity, same review key replay stays quantity2, remove empties actual cart. Inference uses fixture output, not live Groq. Optional broker recommendations use fixture, no actual recommendation relevance proof.

Frontend118tests22suites, TypeScript and production build pass; tests assert no auto-mutation, exact request, stable key, uncertain failure, safe tracking path, no model-destination/legacy-userID action execution, preserved action payload and negated text safety. Component fixture mobile pixels inspected, not full live browser journey.

## Open gates

Exact-name match is deliberately conservative. Pronoun/elliptical cart requests need grounded catalog-choice/session referents, not guessed product IDs. No broad natural-language task-completion claim; live model evaluation remains unauthorized. Human support queue, acknowledgement destination/operator policy and full end-to-end escalation remain absent. Canonical-cart durability is separate item2 and held migration. Review receipts currently inherit Redis retention; not durable across cache loss. PR21 must be reviewed separately for per-order tracking correctness. No shipped mocks.

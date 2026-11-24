# Legacy recovery/copy strict callers

Additive continuation of PR108. The original missing-item category/complement
recovery and legacy product response generator now use the existing strict model
adapter when available. Older injected generate_response adapters still work.
No voice/cart mutation caller or ordinary HTTP routing changed. No provider calls.

The actual strict adapter with controlled transport is tested for success, blank
completion, transport failure and cancellation. Missing-item transport failure now
reaches its pre-existing safe original-query retrieval fallback, instead of being
silently converted to an empty completion and then a different category plan.
Cancellation propagates before retrieval. Success retains deduped
category/complement retrieval. Product response failure returns only listed
name/price with explicit inability to assess fit. Error logs retain error type,
not provider exception or customer prompt contents.

12 focused tests pass, including PR108 and existing behavior contracts. These are
controlled model and search boundaries, not actual provider entailment or SQL
quality proof. Legacy architecture still has unreviewed ecosystem planner,
response branches and optional cart copy callers. Preserving those foundations
is not a claim that their broad prose/fallback policy is fully hardened. The
ordinary HTTP reviewed setup/research path remains separate. Do not route users
back to legacy handlers solely to claim parity. No canonical55/live flags change.

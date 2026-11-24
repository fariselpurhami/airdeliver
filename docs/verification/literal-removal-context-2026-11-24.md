# Literal removal context

The router may retain a bounded removal reason only when it is an exact span of the current customer message and the intent is removal. Prior assistant text, inferred motives, sensitive profiling and budget guesses do not qualify. The review UI shows the reason before the customer presses remove. The authenticated removal endpoint carries that optional field through the confirmed cart mutation to the separate read-only recommendation worker. Add events strip it. Recommendations receive it as untrusted customer-stated context, never as source facts or instructions.

No reason is required, and existing requests without it retain their shape. Optional broker failure cannot undo removal. The worker rechecks current cart/catalog before and after model copy and never re-adds anything. Exact text membership does not prove semantic reason extraction; real-model multilingual interpretation remains unverified. Existing idempotency identifies the cart mutation, not optional advice delivery, so retries do not create a reason-based second removal.

Tests cover current-span preservation, absent-span rejection, bounded authenticated HTTP forwarding, real Redis removal to optional event, and PostgreSQL/Redis worker evidence reaching the shared reviewed model request. No provider calls or owner-machine actions.

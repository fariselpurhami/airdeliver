# One cart line per product

Hydration rejects duplicate product IDs instead of letting add inspect only the first matching quantity or remove silently collapse all duplicate lines. Existing valid carts and operation semantics stay unchanged. Corrupt duplicate state is preserved, not merged or erased without customer review. Checkout retains its independent combined-quantity validation.

Four regressions cover add/remove/save/sync with duplicate lines whose combined quantity exceeds99. Each fails before state write, saved-order insert or success/preview. Full local migrated PostgreSQL19/Redis suite774 passed,4 skipped,20 existing warnings. This guards state invariants, not stock reservation or full cart concurrency.

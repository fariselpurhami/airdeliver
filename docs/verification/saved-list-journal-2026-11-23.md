# Prepared saved-list idempotency in canonical cart journal

Prepared save_list locks canonical customer cart, creates existing-style Saved List Order/items, clears canonical cart, and records mutation outcome in the same PostgreSQL transaction. Same operation ID/revision replay returns original saved order ID plus current cart without clearing later additions. No Redis dual-write/delete inside commit. Existing customer traffic unchanged.

Real migrated PostgreSQL19 tests cover new-session postcommit replay after newer cart, two competing saves with same ID creating one order, and rollback restoring cart while removing both saved order and receipt. Full local822passed4skipped20existing warnings. Existing Order.total_price schema stores a floating representation, so tests compare Decimal(str(value)) numerically, not cosmetic trailing zeros. That legacy schema remains unchanged in this checkpoint.

Depends on prepared canonical journal migration1b8de657a098. User-stack application/rollout is a morning decision, not performed. Legacy Redis save route is not silently switched and must not be called idempotent yet. No provider calls, deployment or data category change.

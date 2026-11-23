# Journey item2: prepared offline Redis→PostgreSQL import and rollback plan

NOT executed on owner systems. Migration1b8de657a098 remains held. Canonical traffic is NOT enabled. Existing Redis carts remain unchanged. This PR prepares a dry-run-default command and insert-only transaction, not a live cutover or durability claim.

## Review gates before any run

1. Approve schema migration separately, back up SQL+Redis and prove restore on disposable copies. No automatic upgrade-head, because that can include unrelated held migrations.
2. Inventory ALL legacy writers: HTTP add/remove/clear/save, AI worker/NLU/voice commands, checkout price refresh, payment webhook/worker cleanup, session reset and recovery. Freeze them and drain in-flight operations. A flag is operator acknowledgement, not proof that writers stopped. Until a verified runtime gate exists, no apply or cutover.
3. Export legacy ai_cart owner snapshots under freeze using bounded SCAN, never KEYS. Snapshot include source timestamp/Redis persistence backup outside logs, owner/key mapping and TTL. Missing/expired keys are not proof a prior cart never existed. Keep export encrypted/private and never commit it.
4. Produce reviewed JSON bundle: version1, UUID batch_id, carts array of user_id/state. Max10kowners/20MiB per bounded run. Validate every cart, duplicate owner/product, exact owner/product foreign keys, USD currency. Recompute totals from validated lines. Invalid owners/products quarantine the entire batch, no partial commit. Do not silently discard inactive/out-of-stock cart lines; checkout revalidation is separate.
5. Run dry-run command, inspect status counts and digest. Dry run only reads SQL and prints counts, no cart PII. Review separate owner-level quarantine privately if needed. Existing canonical rows are never overwritten. Same exact batch replay is idempotent.
6. Under approved continued freeze and backup, apply exact reviewed digest with explicit writers-stopped acknowledgement. Single SQL transaction inserts canonical revision1 and immutable import receipt, does not write/delete legacy Redis or enable runtime. Concurrent canonical initialization conflicts and rolls back.
7. Independently reconcile every imported row/count/hash and run customer-safe canaries on disposable environment before proposing runtime switch. Runtime read/write switch and cache-derived publication require a separate fully tested implementation. Do not run current journal.clear_cart as fulfillment cancellation, it still has legacy pending-order cancellation semantics needing item6 integration.

## Rollback, before versus after canonical writes

Before any canonical customer traffic: leave imported SQL rows+receipts intact, keep/return read/write routing to unchanged legacy Redis while frozen, validate legacy export and resume only after operator review. No deletes or migration downgrade required. Current code already has only legacy runtime, so prepared imports do not change routing at all.

After canonical customer writes: NEVER flip to stale Redis. Freeze all writers again, export highest canonical revision per owner, reconcile paid/order cleanup, prepare a separately reviewed compare-and-set reverse projection using each frozen legacy snapshot as precondition. Preserve SQL journal/audit. Resolve conflicts manually. This reverse projector is intentionally not implemented until runtime cutover design is approved; rollback after traffic is a blocker, not a fake one-click promise.

## Command

From apps/api: python -m app.commands.prepare_cart_import --bundle /private/cart-bundle.json

Apply exists only for later authorized use: add --apply-digest with reviewed SHA256 and --writers-stopped. It runs no migration and does not connect Redis. Credential values stay in mounted environment/vault, never flags or chat. No owner bundle was exported, inspected or applied for this PR.

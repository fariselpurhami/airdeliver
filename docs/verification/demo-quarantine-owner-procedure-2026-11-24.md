# Owner-controlled reversible demo quarantine, preparation only

No owner database or volume has been changed. Customer-facing surfaces are already gated real-only after PR75. Stored synthetic catalog rows are retained so prior orders, cart references and audit history do not break.

## Before any owner apply

1. Run existing scripts/backup_dev_db.sh against the already-running named database container. It creates a private archive, readable archive index and read-only preflight. It does not prove restoration.
2. Restore that archive into a separate empty PostgreSQL19 target using the existing backup image restore workflow. Never restore over the current database or attach old volumes. Verify all required schema/data counts and the marked product snapshots, not merely archive readability.
3. Keep the archive off the application volume with private permissions. Keep a copy of the exact marked product manifest and its archive hash. Stop seeding/import jobs for the quarantine window.
4. The new preparation tool plan mode requires both current database and isolated-restored database connections, verifies distinct database names, compares total product count and every marked product id/sku/active/timestamp, then saves a private manifest. Connection URI goes through environment, never command history/chat.
5. Inspect the marked rows/count. Apply changes only is_active=false for those exact unchanged marked rows inside a transaction. No deletion, relabeling, inventory modification, migration, order update or cache purge. This removes them from customer catalog without breaking references.
6. Read current states after apply and retain the receipt. If commit is uncertain, inspect current rows before any retry. A receipt prepared before commit is not proof of success.
7. Rollback requires exact unchanged after-state and restores original active states. Concurrent changes cause refusal, not overwrite. Retain old records and manifests until owner approves a retention policy.

## Current implementation limits

The helper is a prepared owner tool, not executed on the owner's computer. ActualPG test covers quarantine/rollback, row preservation and stale-plan refusal. Full restore automation and comprehensive source-versus-restored database comparison remain owner/release prerequisites. The tool compares product snapshots, not every table. A supplied restored connection alone is not proof the archive was used; operator must verify the actual restore provenance. No claim of completed deletion or disaster-recovery certification.

No owner command batch should be sent until remaining restoration/release gates finish. This note is the basis of the one final batch, not an instruction to run it now.

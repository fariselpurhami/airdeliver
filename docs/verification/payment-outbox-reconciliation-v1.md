# Payment-event recovery runner, opt-in only

Prepares bounded reconciliation of already committed payment outbox events. It never creates an order, starts/captures/refunds payment, changes inventory, awards points or applies a migration. No runner is added to API startup or deployment. Existing dispatch_pending and stable event IDs/backoff/row locks stay authoritative.

Default script mode prints pending/due counts only and never opens a broker connection. --dispatch enables one bounded publication pass; --dispatch --watch is an explicitly opt-in dedicated process with60second cadence,1..50row batches and a30second pass deadline. SIGTERM/SIGINT stops between passes; cancellation rolls back the open transaction. Fixed numeric summaries/class-only failures contain no payload/customer text.

14tests pass, including actual migrated PostgreSQL concurrent runners/skip-locked uniqueness, committed crash recovery, NACK backoff, same-ID retry and stop/cancel/bounds. Transport is fake, no external broker/provider delivery occurred. Delivery remains at least once: crash after broker acceptance/before DB commit can duplicate the same ID. Consumer deduplication and real broker restart receipts are still required before enabling recurring production delivery. This does not close rewards idempotency or live fulfillment.

Operational invocation from apps/api, with existing configured environment:

- `PYTHONPATH=. python scripts/reconcile_payment_outbox.py` reads counts only.
- Dispatch/watch is intentionally NOT enabled by this patch. Choose deployment supervision and verify delivery scope/consumer replay first.

No spend, provider/payment calls, held cart migration activation, deployment mutation or whole-platform certification.

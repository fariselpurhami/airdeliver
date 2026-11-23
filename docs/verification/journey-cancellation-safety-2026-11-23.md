# Journey item6, cancellation safety boundary, not complete refund/support

Additive hardening of existing cancellation, no provider request or owner mutation. Existing service/route/UI entrypoints preserved. No merge or rollout.

Cancellation now requires exact owned order, row lock and fresh state. Missing/other account shares not_found. Paid/nonpending cannot cancel here. Orders with provider reference or active setup lease are held for provider reconciliation, never pretend that a local update voided an external payment. Only unpaid local drafts without provider setup can cancel; audit written in same transaction. Repeated canceled target is idempotent. Current cart is always preserved, including absent target, refusal and failure.

HTTP reports actual state and error code, no generic accepted for a known refusal. Older service adapters returning None retain202 compatibility, not used by current implementation. Frontend sends resolved exact order ID and keeps payment/recovery context until successful outcome. Uncertainty says no refund/cancellation confirmed and tells customer to inspect existing order.

Tests: independent disposable PostgreSQL sessions prove payment-state lock waits, then cancellation sees committed paid state and refuses. Ownership, provider initialized, repeat, audit-once and unrelated cart preservation. HTTP outcome code contracts. Frontend113tests21suites, tsc/build pass, payment context preserved on refusal. Full backend result recorded in parent report.

Remaining item6 gates: actual provider void/cancel/refund, support queue, refund/return policy and human acknowledgement. No refund code fabricated and no policy selected. Broad cancellation can race external acceptance, so provider-initialized orders intentionally stop. This is a partial draft, not a completed after-sales workflow.

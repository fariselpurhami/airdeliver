# Item 6: returns and support structure, held design

No customer-facing policy, support ticket, callback, RMA, return label or refund is created by this draft. No provider calls, migration, activation or promises. Existing help and assistant entrypoints remain unchanged.

## Product facts and unresolved proposal

US partner stores/inventory only. Stores are intended legal sellers; airdeliver brands purchase/delivery and collects payment. The repo currently contains no named store integration or agreement establishing dispatch/return obligations. Thirty days from delivery is a proposed return window, not an approved or verified partner term. Return costs, conditions, exclusions, fees, refund treatment, operator ownership and response times remain unspecified.

## Proposed durable records

- SupportCase: owner from authenticated session, exact owned order, stable request key and payload fingerprint, kind, customer message, opened_at, assigned queue/operator and version. Duplicate exact retry returns same case; conflicting key fails. No customer-supplied owner/assignee.
- ReturnCaseLine: purchased order line, seller/origin, quantity requested, reason/condition, approved policy snapshot and seller RMA, status and evidence references. Lock quantities across all return cases, refuse more than delivered minus already-returned quantity. Multi-store orders split into seller-specific cases, never assume one address or policy.
- ReturnPolicyVersion: seller, approval source, exact delivered-at anchor and destination timezone, configured window and conditions/exclusions, return shipping payer, original shipping refund, fees, support queue, effective/expiry times. No implicit 30 days, free return, prepaid label or full refund. The schema requires explicit values but does not authenticate their source.
- CaseEvent: immutable actor/status/time/evidence and customer-visible wording. Keep internal notes private. Access is owner-only or authorized admin, same missing/foreign response, paginated no-store reads.
- RefundAttempt: source settled payment, remaining refundable cents/currency, line allocations, approved shipping/fee adjustments, provider idempotency key, fenced attempt state, provider receipt and verified settled result. Never report a refund from a database status alone.

## State boundaries

Request submitted -> under review -> approved or declined. Approval records eligibility and conditions, not a refund or label. Approved -> awaiting parcel -> received -> inspected -> refund pending -> refunded or partial refund. Each external step has an uncertain/reconciliation state. Provider-confirmed receipt is required before settled refund claims. Evidence decides damaged/wrong-item cases; do not auto-refuse them by generic category rules. Cancellation before shipment remains a separate flow from a return after delivery.

Use verified delivery event per shipment/line as window anchor. Manual fulfillment evidence and carrier evidence are different sources. Owner must decide how unverified delivery timestamps and split deliveries are reviewed. Do not start return windows at order creation, label creation or payment time.

## Support intake and honest UX

Only expose Submit when a real accountable queue and persistence exist. Persist before reporting a case ID, with an owned confirmation view and retry-safe state. Until configured, say human support is unavailable, no ticket or callback created. Do not invent an email, phone, hours or SLA. Preserve a locally reviewable draft but do not send it to any third party. The current help page has decorative search/contact modules and online wording, so it requires a separately tested design/behavior pass before treating it as an operational support channel.

Customer-facing status: request received, being reviewed, next required step, approved conditions, shipment received, refund processing, refund confirmed. A refund-processing message includes the verified provider state and clearly separates submission from receipt by the bank. No countdown without supported policy.

## Security and operations gates

Owner approves policies per real seller and legal/payment model. Queue ownership, staffed coverage/escalation, retention/access policy, evidence storage and redaction must be set. No card data or passwords in support messages; evidence uploads need type/size/scan controls. Audit admin transitions, protect CSRF/auth, bound rates and message lengths, escape user content, retain only needed data. Notifications are in-app until external delivery is separately authorized/configured.

## Implementation sequence

1. Confirm actual partners and official contractual return/dispatch terms. Do not infer terms from a storefront or commerce platform.
2. Review migration for support/case/event/refund records, unapplied until approved.
3. Implement owner-scoped intake, idempotent append-only workflow and admin queue with PostgreSQL concurrency/authorization tests. No provider side effects.
4. Merge cancellation/manual-fulfillment dependencies deliberately; reconcile per-origin delivery evidence.
5. Add approved sandbox labels/refunds and webhook signature/amount/owner tests. Refused/uncertain operations remain explicit.
6. Customer design pass, mobile/desktop and accessibility proof, then separate owner rollout decision.

The accompanying strict schemas are unwired design contracts. Availability always reports intake disabled, ticket not created, return not accepted and refund not started, even when sample configuration is complete. Fixture policy values are synthetic only.

Verification: 8 focused contract tests passed. Full disposable PostgreSQL19 and Redis suite: 1014 passed, 4 skipped. No frontend changes or external/provider calls.

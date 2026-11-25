# Canonical commerce journey, source map v1

Read-only architecture baseline. Source inspected November25,2026. No held cart migration activated, money/provider call made or policy inferred. Tests and source do not certify production acceptance.

## Customer journey and authoritative boundaries

| Step | Active entry | Authority / durable state | Honest UX and remaining acceptance |
|---|---|---|---|
| Discover | ai-support/chat; ai-ordering session suggestions; AIChatOverlay | NeuralCoreService, catalog_result, strict model schemas, local claim validation, independent review | Cards are current local catalog or explicitly synthetic, never merchant-stock proof. Fallback cannot imply completed action. Live model adherence and capacity remain open. |
| Inspect product | ProductDetailsCard and product overlay | Current structured card eligibility, exact product identity | No inferred price/stock. Add is a request, HTTP202 is not confirmed cart mutation. Mobile/focus/scroll controls inspected in overlay work. |
| Review cart change | ai-ordering/cart routes plus lifecycle review confirm | AICartService, Redis cart snapshot/CAS, mutation receipts where supplied | Refresh/replay and changed-catalog recovery must use current authoritative cart. SQL cart_journal model/migration exists but remains held. Legacy endpoint source is not a mounted alternative. |
| Start checkout | checkout page exports CheckoutStart, then useAIOrderingStore.confirmCurrentOrder | Mounted ai-ordering checkout options/confirm | Authenticate, review address and payment choice. Dormant raw-card prototype in checkout/page is not the active UI. |
| Validate order | AICheckoutService.handle_confirm_order | SQL products locked, active/non-synthetic/stock/quantity/currency/Decimal prices checked; owner-bound checkout request and frozen checkout_data | Price change refreshes cart and asks for review. Stock is checked, not reserved. Current amount is item subtotal, not a verified tax/shipping/fee quote. |
| Initialize payment | PaymentOrchestrator through durable order setup lease | Pending order committed before provider I/O, idempotency key,30second setup lease, persisted handoff | Unknown provider outcome is not failure or permission to pay again. Reuse/reconcile same operation. No real payment acceptance performed here. |
| Complete payment | Signed Stripe/PayPal webhooks, PayPal capture route | Verified amount/currency/owner/transaction then PaymentCompletionService row lock | Provider truth, not browser redirect, marks paid. Wrong owner/amount/transaction fails. |
| Publish paid result | payment_outbox_service | Paid state and event rows commit together; broker confirms then delivered timestamp | At-least-once, stable event IDs. Consumer replay safety and a recurring reconciler need explicit acceptance. Only completion/replay callers to dispatch_pending were found. |
| Clear paid cart / rewards | PaymentCompletionService after paid commit | Exact checkout cart snapshot CAS deletion; rewards best effort | Changed/new cart preserved. Missing snapshot preserved. Rewards failure does not undo payment; durable idempotent rewards remain separate. |
| Fulfill | Admin feature-flagged fulfillment API/page | Paid guard, expected from-state, next-state guard, audit and in-app notification in transaction | Manual operational record, not verified carrier status. No automatic delivery, carrier scan or ETA invented. |
| View orders | orders/me and orders/me/{id}; customer tracking page | Owner-filtered SQL order record | Tracking is the local record. Carrier/live ETA integration remains an owner decision. |
| Cancel | ai-ordering/checkout/cancel with exact order | Owner-locked pending unpaid local draft without provider IDs/lease only | Cart preserved. Paid/provider-initialized orders require reconciliation. This is not a provider cancellation/refund facility. |

## Canonical order/payment state

OrderStatus source: app/models/enums.py. Payment setup has additional identifiers/lease/snapshot on Order; status alone is insufficient.

- PENDING plus no provider identifiers/active lease: local unpaid draft. Exact owner may cancel locally.
- PENDING plus setup lease or provider handoff: provider outcome may exist. Reconcile same operation, do not infer no charge.
- Verified payment from PENDING or FAILED: PROCESSING, is_paid=true, paid_at and transaction identifier persisted with outbox rows.
- Duplicate same-transaction paid completion: no new payment events/rewards; attempts pending event delivery.
- Different transaction identifier or unsupported order state: reconciliation required, not a silent overwrite.
- Manual paid fulfillment: PROCESSING -> ASSIGNED -> IN_TRANSIT -> DELIVERED, expected from-state and evidence required.
- CANCELLED local draft is idempotently returned. Paid or provider-initialized state is not cancelled/refunded here.
- SAVED_FOR_LATER exists in the enum. Do not interpret it as a financial or fulfillment state without its caller context.

## Inventory and amount invariants not yet closed

1. SQL stock checks do not reserve or decrement inventory. The source search found inventory writes in real_catalog_import, not payment completion. Concurrent successful purchases need a reviewed reservation/deduction/release design with expiry/cancel/refund semantics.
2. Item subtotal is Decimal-verified but does not establish final landed total. Merchant countries, taxes, shipping, fees, delivery promise and refundable components need grounded policy plus an immutable quote.
3. US launch address validation checks shape only, not carrier deliverability. No global checkout claim is supported.
4. Payment retry/cancel/refund and paid-order reconciliation need sandbox receipts before real-money operation. No real provider work is authorized in this task.
5. Outbox events are at-least-once; dispatch failure stores backoff. Recurring reconciliation and consumer deduplication must be exercised through actual broker failures/restarts.

## Dashboard truth before polish

Sources: admin.py stats/orders, dashboard/page.tsx. AdminOrder already includes currency in the API, but dashboard display/chart assumptions still need correction.

- total_revenue currently sums total_price for DELIVERED/IN_TRANSIT, with no currency grouping or explicit paid/settled definition.
- active_users_today counts distinct ordering users after a naive server-local midnight. It is not all active users.
- Chart uses latest100orders client-side, sums all statuses and currencies by created_at. It is not a complete settled-revenue time series.
- Dollar prefixes are hardcoded in metric/chart/activity display.
- Next dashboard repair should add server-defined currency-separated measures, explicit UTC/window bounds, source timestamps, completeness/pagination and honest labels. Preserve existing visual foundations.
- Queue/outbox backlog, payment reconciliation, inventory freshness, provider readiness and consent/privacy failures need permission-scoped sources before adding health widgets. No guessed green statuses.

## Required acceptance order

A. Close human status/history exact-head CI and merge, then first compact/schema repair. No full token-chain closure until representative chains pass and live safe diagnostics are reproduced with owner authority.
B. Inventory/quote/payment/outbox invariants in isolated real SQL/Redis/broker tests. Do not activate held migration or choose merchant policy implicitly.
C. Browser guest/auth/wrong-owner/customer/admin journey: refresh, network loss, replay, duplicate click, multi-tab, mobile, keyboard, focus and accessible uncertainty recovery. No real charge.
D. Currency-aware dashboard truth, then operational coverage.
E. Owner-approved sandbox/deployment/merchant/fulfillment decisions, recovery/canary/rollback/load and bounded live model acceptance. Text first, voice last.

## Source index

- apps/api/app/api/v1/api.py, endpoints/ai_ordering.py, endpoints/ai_support.py, endpoints/orders.py, endpoints/webhooks.py, endpoints/admin.py
- apps/api/app/services/neural_core_service.py, ai_cart_service.py, ai_checkout_service.py, payment_completion_service.py, payment_outbox_service.py, real_catalog_import.py
- apps/api/app/models/order.py, enums.py, cart_journal.py
- apps/web/app/(main)/checkout/page.tsx, components/checkout/CheckoutStart.tsx, ShippingAddressForm.tsx, CheckoutForm.tsx, hooks/useAIOrderingStore.ts
- apps/web/app/(admin)/dashboard/page.tsx
- tests/test_staged_search_postgres.py, test_checkout_postgres.py, test_checkout_idempotency.py, test_payment_outbox.py, test_manual_fulfillment_postgres.py, test_cart_persistence_outcomes.py

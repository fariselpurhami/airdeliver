# Item 3: US shipping/tax preparation, not active checkout

This is an unwired, offline-only policy module. It does not change live charges or turn an estimate into a final total. No default commercial rates, tax exemptions or service regions are selected.

## Proposed contract

Owner-reviewed versioned shipping policy: allowed US regions, integer-cent flat fee, optional free threshold, expiry and approval reference. There is no implied lower-48 or territory coverage. ShippingAddress still validates US format, not deliverability or tax jurisdiction.

Catalog snapshot: active USD products, quantities and fresh inventory/prices from the owning database. No floats or coerced money. Duplicate lines refused. This module validates snapshots, not their origin. Production integration must fetch them server-side, never accept client prices or stock as authority.

Tax: require an explicit final amount from a reviewed assessment covering the exact address, catalog lines and shipping fee. A state-level rate is not a full address-level tax decision. A zero amount is explicit, never a fallback for missing state policy or failed provider. The tax assessment carries source/operator reference and expiry. References are metadata, not proof of permission. There are deliberately no real rates in the code or fixtures.

Output: subtotal/shipping/tax/total in integer cents plus USD decimal display and earliest expiry. Always offline_review_only, ready_for_payment=false and stock_reserved=false. A SHA256 binding changes with address/items/shipping/policy and is not a secret or an authorization token. Quote output omits raw address.

## Required integration before activation

1. Owner specifies coverage, shipping fee/free threshold, tax assessor/provider and tax policy. Legal/accounting review determines obligations, not this calculator.
2. Authenticated server quote endpoint reads fresh owned cart and catalog, stores immutable quote with owner, policy/tax versions, full breakdown and expiry. UI reviews changed total before any provider call. Signatures/digests alone do not authorize a charge.
3. Reservation rows with product locks in deterministic order, exact per-order quantity and expiry. Payment settlement and expiry compete under one durable fence. Reconcile ambiguous provider state before release, no late paid order allowed after stock resale.
4. Freeze provider amount/currency/quote, require exact match at capture/webhook. Durable provider reconciliation and stock ledger required, tested against independent PostgreSQL sessions.
5. Merge cancellation safety and manual fulfillment changes before stock-release integration. No moving a paid order backward to free stock.
6. Shadow compare without charges, canary on explicitly approved sandbox, then independent owner-approved migration and rollout plan.

Current main checks catalog price/stock under product locks but does not reserve stock. Concurrent checkouts can still promise the same units after transaction release. That gap is NOT closed by this module. This draft must not be marketed as a finished checkout policy.

## Verification

13 focused policy tests passed. Full disposable PostgreSQL 19 + Redis suite: 1019 passed, 4 skipped. No frontend changes, provider calls, migration, owner-policy values or live checkout wiring. Fixture amounts are synthetic and not a recommendation.

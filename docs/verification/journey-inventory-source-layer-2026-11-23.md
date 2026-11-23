# General inventory source layer, additive draft

This is a general source layer for multiple partner merchants and future airdeliver-owned stock, not a single-merchant pilot and not a provider selection. No adapters, partner calls, sample catalog, credentials or commercial account are shipped. Current catalog and checkout paths are unchanged.

## Shape

SourceIdentity has independent source and seller keys, legal seller, source kind and US inventory/seller country. Any number of sources can coexist. No Shopify, WooCommerce, BigCommerce or retailer-specific fields. One partner may expose many origins; one legal seller may have multiple sources. The launch category codes are clothing, accessories, electronics, makeup, beauty, personal_care and sports. Product category labels are not rewritten.

ProductSourceBinding is an optional side table referencing an existing product and a unique source/variant/origin. Each purchasable listing has one authoritative source binding. The same physical item from different sellers/variants/origins is represented by distinct listing Product IDs, never silently routes one cart line to a different seller. A future comparison layer may group equivalent listings without merging seller identity. Existing products have no invented seller or backfill.

OrderLineSourceSnapshot records identity and terms per order item plus purchased external variant/origin/category. Future checkout must call the unwired preflight in its existing transaction before provider handoff. It locks line/binding/source, validates trusted stored terms, inserts once and returns the existing snapshot on retries. A database trigger blocks snapshot updates/deletes. Current checkout never calls it, so unbound legacy products still work exactly as before, not falsely marked ready for a partner checkout.

InventorySourceAdapter is a protocol for cursor catalog, price, stock, placement, shipment/tracking events, returns and reserve/commit/release hooks. There is deliberately no concrete adapter and no invented partner response. Unsupported capability is a refusal, not an empty list or fake success. Future implementations need typed error/timeout reconciliation, verified signatures, authenticated account binding, idempotent request keys and actual contract tests.

Capabilities and commercial terms are separate. A technical catalog feed is not permission to resell, collect payment or use airdeliver branding. Gates require approved/current stored terms, supported and permitted operation, allowed category, and explicit checkout/collection/branding permissions for purchase/reservation. Return actions require a verified policy reference. These fields are source metadata, not authority by themselves. No client flag or external text can approve terms. Provider configuration stays disabled until independently approved and verified.

## Reservation hook contract, still open

Stock snapshots carry observation, expiry, revision, variant/origin and availability. They are not reservations. Reserve/commit/release commands carry stable UUID, exact order line, source, origin, quantity, expected revision, expiry and fencing number. Held responses need a source reservation reference and aware expiry. Unknown is explicit. Never assume retry failure means reservation failure.

The durable coordinator is NOT implemented: reservation table/unique request keys, deterministic product/source lock order, atomic capacity ledger, payment/expiry fence, reconciliation before release, dead-letter handling, webhook verification and late capture recovery remain gates. Partner stock needs provider-held reservations or agreed atomic placement semantics; a local ledger cannot stop sales on a partner's own site. Owned stock later uses the same hooks but needs its own authoritative warehouse ledger and real implementation. No fake local adapter is included.

## Shipment, payment and return boundaries

Group lines by seller/source/origin for quoting and fulfillment; snapshot per-shipment tax/shipping allocation before payment. An aggregate order can have multiple shipment states, not one blanket delivered flag. Events retain event ID, revision, occurred time and evidence reference. Signature verification, deduplication and monotonic/out-of-order handling belong at the verified provider ingestion boundary. A label_created event is not carrier_accepted. Never accept client-submitted delivery/refund events as truth.

The three-day target is anchored at verified paid purchase. Business/calendar day semantics and partner dispatch commitments remain undecided. No guarantee or artificial ETA. Thirty-day returns remains an unapproved proposal, with policy/cost/eligibility per seller and actual delivered line. Pending tax/merchant-of-record classification is not decided by source flags. Existing multiple payment providers are not removed; Stripe-only launch direction requires separate authorized wiring/configuration.

## Migration and integration gates

Migration 3da1f52cc823 depends on held cart migration 1b8de657a098. Unapplied to owner infrastructure. PR20 reset independently extends that cart revision, so the migration graph must be deliberately rebased/merged before any combined upgrade. Do not blindly upgrade heads. Backup, staging rehearsal, snapshot retention and owner approval required. Downgrade removes provenance and must not be used without reviewed retention/export.

Source-side tables and snapshot service are unwired. They do not certify existing live inventory, dispatch, tax, payment, returns or checkout readiness. No mutation endpoint is exposed. Future integration needs owned/admin auth, validated source configuration, a registry that refuses unregistered sources and quotas, secret references through secure configuration, fresh quote and reservation enforcement plus outbox-driven order placement. Do not dynamically import adapter names supplied by partner data.

## Inputs needed from owner

- Source/merchant identities and official API/contract access for any sources he chooses. Architecture accepts many, not a forced single provider.
- Per-source permission for airdeliver-branded own checkout/payment collection, categories, US origins and seller-of-record details.
- Actual dispatch commitments and returns/cost policy, support/fulfillment owner, and tax/legal review.
- Whether each source supports atomic holds, stock revisions, idempotent placement and signed shipment/return events. Missing capabilities remain unavailable.
- Separate approval for migrations, sandbox provider tests and rollout. No credentials in chat.

## Verification

Full disposable migrated PostgreSQL19 plus Redis suite: 1022 passed, 4 skipped. Follow-up 16 focused contracts/real-database tests passed, including two independent session attribution attempts for one line, both source kinds in one order, missing legacy attribution refusal, stable snapshot after source edits and database rejection of snapshot updates. No frontend changes. Migration was run only on a throwaway local database; no owner migration, source registration, provider call, deployment or merge.

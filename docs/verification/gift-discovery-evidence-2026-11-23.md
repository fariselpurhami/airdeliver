# Shopping discovery and evidence contract, 2026-11-23

## Confirmed failure

The live HTTP support service selected the first semantic result and constructed a fixed product-sales sentence, including a hardcoded dollar sign and stock from a local integer. The response schema contained no products collection and the HTTP client always appended plain text. A vague gift request could therefore become an expensive purported match with no card. The name in the owner's screenshot also occurs in the demo seeder, whose price/stock are synthetic. The exact owner database row has not been inspected, so this does not prove that row's provenance.

## Additive boundaries

- Existing router, hybrid/visual retrieval, session ownership and cart/action foundations remain. No migration, supplier integration or deployment is part of this change.
- Router v1 shopping brief distinguishes gift discovery from a concrete customer-supplied subject. Extracted subject/preferences must occur in customer messages, never assistant history. Model prompting is semantic routing, not a keyword classifier. Recipient alone must not become inferred tastes, category or luxury budget.
- Customer-explicit budget caps/currency are checked against their source span. Current cards above the cap, in another currency or with unknown price are dropped. No exchange-rate guessing. An unresolved budget asks clarification.
- Candidate IDs are bounded and deduplicated. A single fresh PostgreSQL read revalidates text and image candidates, preserving retrieval order while dropping deleted/inactive rows. Index/cache snapshots never supply displayed commercial fields.
- Cards distinguish `seeded_demo` from `local_catalog`. Either seed SKU or dataset marker flags demo. Neither source proves merchant stock. Local quantity is disclosed only as local stock; supplier availability, reservation and delivery remain unverified. No invented verified-stock state exists.
- Product prose is model-authored from a bounded evidence payload. A strict draft declares IDs and commercial field claims. IDs, amounts/currencies/stock states and exact catalog names are checked against the current cards. No external links or ungrounded numerical text. A second model pass independently judges implied claims, missing demo disclosure, undeclared products and whether the draft fulfills discovery rather than arbitrary recommendation.
- All writer/reviewer work shares one eight-second deadline, including retry backoff. Router has its existing separate eight-second deadline. Successful ordinary text turns use up to three inference calls (route, writer, review); images use two. More calls/latency than the previous template, no live latency claim.
- Invalid output, failed review, provider failure or database revalidation failure returns a labeled system notice. Rejected prose AND candidate cards are withheld. No fixed sales-copy fallback.
- Structured products travel over the actual support HTTP contract into the existing carousel. Client rejects malformed evidence rather than silently stripping cards and showing sales text. Cards show source disclosures and their own currency. Demo ADD is disabled on this carousel; this is not a global demo-checkout restriction. Existing server cart/checkout checks are unchanged.
- Deterministic operational cart review, tracking controls and support connection-status notices remain, outside product-sales copy.

## Limits and quality gate

Natural-language entailment is not mathematically guaranteed by JSON or a model reviewer. A model may misclassify a broad subject or both passes may share a blind spot. These are layered safeguards, not a claim of zero hallucinations. Existing live provider access, actual model quality, multilingual behavior and production latency have NOT been tested by this work. No provider request was made. Tests that control model transport test software boundaries, not real model intelligence.

Before calling the behavior model-validated, an owner-authorized live evaluation should cover: English/Arabic recipient-only gift, budget-only follow-up, explicit category follow-up, exact item, no matches, inactive/deleted row, mixed demo/real catalog, unsupported currency, misleading catalog text, invented product/price/stock in draft, reviewer rejection and provider timeout. Pass criteria: appropriate clarification, no unsupported claim, a current card for each product mention, demo disclosure, no auto cart/checkout, and measured latency. The evaluation requires separate provider-call permission and budget. Do not merge without per-PR owner approval.

## Local verification

Full migrated disposable PostgreSQL19 suite, mounted support HTTP serialization, current-row mutation/deletion/inactivity boundaries, source-span routing, budget enforcement, draft/claim rejection, review rejection and deadline tests. Frontend actual HTTP-store bridge, evidence rejection, source labels, currency formatting, TypeScript and production build. Mobile screenshot is the actual React overlay with a labeled test fixture, not live model evidence.

## Optional owner read-only provenance check

After this branch is available, from the repository using the owner's usual combined Compose files:

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T api python scripts/inspect_catalog_product.py --name 'Cartier LOVE Bracelet'
```

This existing-container command performs no rebuild, migration or write. It opens a PostgreSQL read-only transaction and returns at most ten exact-name rows with ID/SKU/price/currency/local inventory/activity/demo marker/update time. It does not expose credentials or full attributes. It can settle local row provenance, not merchant inventory. Command has not been run on the owner's machine.

Final local counts: 1093 backend passed, 4 skipped; 160 frontend passed across29 suites; TypeScript and Next production build passed. One full-suite run saw an unrelated real-Redis load test fail (100 successful responses but18 instead of50 throttled, the remainder were other statuses). It was not altered or weakened; the full suite was rerun and passed. Keep CI as a separate gate.

## Alignment with original sales design

Owner clarification preserves fixed cart-confirmation/tracking/handoff control text, but requires model product prose plus cards and an honest persuasive alternative when the requested item is unavailable.

History inspection found the earliest tracked neural-core (`0c901da`) was itself a separate template/rule-based tool path. The earliest tracked sales service (`10fa0ec`) already packaged search text and `product_carousel` together. Later/current `ai_nlu_service._execute_search` and `_find_smart_alternatives` perform staged search, `_generate_genius_response` includes an honest absent-product pivot, and its response builder pairs generated product/spec text with cards. `ai_cart_service` separately emits generated bundle/complement and removal-alternative carousels. These functions establish intended architecture, not proof that all were reached by the owner's latest HTTP request.

Initial PR35 diverged by allowing only neutral candidate copy and omitting fallback substitute retrieval and catalog specs. The alignment update adds requested-name/current availability context, bounded reuse of `find_genius_alternatives` for a known unavailable catalog anchor, generic functional-category hybrid expansion for a missing name, current-row/positive-local-stock/non-demo gates for substitutes, budget retention, structured `catalog_specs` and exact spec field claims. Writer/reviewer now support persuasive value/fit/tradeoff copy based only on those facts, with honest current-results absence disclosure and no global-stock assertion. An over-budget stocked item is explicitly distinguished from out-of-stock. A missing exact name is not proof it does not exist globally.

No existing sales service or complement logic is removed or replaced. This PR does not wire every older sales feature into HTTP chat. The wider original-vs-current regression audit is a separate read-only deliverable. Natural-language alternative relevance remains model-reviewed, not a calibrated guarantee. Merchant-stock sourcing still requires the held inventory-source architecture, not synthetic fields.

Alignment tests: real migrated PostgreSQL requested-item zero stock, missing anchor, genuine positive local-stock alternative, demo/zero-stock/over-budget exclusion, current spec data and claim mismatch. Full local suite1095 passed/4 skipped before the final status-label filter. Original head0c02d8b had all four GitHub checks green; the alignment update needs its own exact-head CI gate.

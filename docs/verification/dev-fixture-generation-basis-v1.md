# Local development catalog, generation basis v1

## Authority and limits

Owner request anchors: `phonemsg-01M867YVQVWGNFPB1NK6HN102N` (synthetic local seeder), `phonemsg-01M8681VZNESW42YF2N2R89PA3` (coherent normal product/cart testing), `phonemsg-01M868CYG2NVR12T0VMFP5GJBW` (traceability). Taxonomy comes from owner message `phonemsg-01M84BGYAG1YXF1XJWHM5GYGC5`:

| Code | Owner label |
|---|---|
| clothing | ملابس |
| accessories | اكسسورات |
| electronics | الكترونيات |
| makeup | مكياج |
| beauty | تجميل |
| personal_care | عنايه |
| sports | رياضه |

These are authored synthetic test values, not sourced merchant offers or actual inventory. No external source was available. No prices, stock, rating or specifications are claimed verified. Each row records its profile ID, generator version, local source document and image asset path. Source identifiers under `local:` or `airdeliver.local` identify generation, not reachable merchant pages. The initial file has exactly1000 rows, 143 percategory except sports142. No brands, fake sales, fake reviews, popularity or discount evidence.

## Traceability by field

* `sku`: stable namespace `ADL-DEV-v1-`, category and sequential variant index. No randomness or inventory impersonation.
* `name`: generic item name in `ITEMS`, deterministic finish, size/pack/format. No trademarks.
* `description`, `attributes`: same item profile and variant values used for the name. Names/descriptions/specs are synthetic and remain marked as such internally. Fixture traceability fields are metadata, not supplier verification.
* `category`: exact owner taxonomy above. The category maps directly to its own eight named item profiles. No cross-category random assignment.
* `price`: explicit `BASE_PRICES` percategory and peritem in `scripts/generate_dev_catalog.py`. Variant adjustments are documented test arithmetic: +5 USD performat/size variant except personal care/makeup which multiply packprice by packindex+1. These are authored plausible testprices, not market research or current retailprices.
* `currency`: USD, matching the current checkout/cart currency contract, not converted from anything.
* `inventory`: exactly40 perrow, an explicit testcapacity. It is never demand, real availability, stockurgency or merchant evidence.
* `rating`: absent/SQLNULL. Existing index schemas require numeric rating so index snapshots use0 for unrated. No reviewscore is fabricated.
* `tags`: category + genericitemname, not popularity.
* `inventory_verified_at`: fixturefile generation timestamp, not a real verification time. Actual-source imports require a timezoneaware stocktimestamp within24hours; fixturefiles are explicitly exempt from staleness claims.
* `image_url`: local original neutral SVG in `apps/web/public/dev-fixtures/`. Seven category illustrations, not accurate photos of1000 individualproducts. Generated locally from simple shapes, no scraped/brand/photo/provider content. `image_kind` explicitly retains that limit. Original category illustrations were rendered and visually checked as a contact sheet.
* `licence`, `image_licence`: synthetic local data and original local neutral artwork. These are not thirdparty permissions.

## Operation

Defaultoff: `AIRDELIVER_DEV_FIXTURES=false`. Enabling is accepted only when validated `APP_ENV=development`; production/staging and conflicting `ENVIRONMENT`, `NODE_ENV` or `ENV` productionmarkers fail closed. A shared catalogpolicy admits the new fixtures only in this explicitly opted-in localmode; old `ADL-DEMO-v1` remains hidden. Product model, cart arithmetic and persistence are unchanged. Provenance exists in SQL and both indexes, never silently relabelled real. UI cards do not get a DEMO badge. Model evidence identifies `dev_fixture` and `fixture_in_stock`, not `local_catalog` realstock. Structuredcopy review remains, with additional deterministic rejection of fixture popularity/discount/urgency claims.

Production/default catalog, semantic SQLreconciliation and checkout reject fixtures, even if accidentally present in a production database. Diagnostics count them separately, never as `real_eligible`. Fixture visibility does not grant paymentauthority.

## Owner-only local steps

No deployment, seed, migration, provider or ownerdatabase actions were executed for these steps. Back up your local catalog first. Use the existing base+dev Compose combination, not standalone dev. Build the changed API image if your existing image does not have new dependencies; these files add none. `--no-deps` keeps held migrations/dependency operations out of this command.

1. Add `AIRDELIVER_DEV_FIXTURES=true` to the local environment file used by your existing dev Compose. Ensure `APP_ENV=development`. Recreate only the API/worker services you already run with your normal base+dev command, using `--no-deps`, so they read the flag. This is opt-in; switching back to false hides fixtures without deleting records.
2. Dryrun, no writes/indexing/models: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec api python scripts/import_real_catalog.py --file fixtures/dev_catalog_v1.json`
3. Review the SHA256, source metadata, rows/create/existing counts and seven categories. Apply only that exact reviewed SHA:
   `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec api python scripts/import_real_catalog.py --file fixtures/dev_catalog_v1.json --apply --reviewed-sha256 SHA_FROM_DRYRUN`
4. Apply commits SQL first, then uses the existing pinned local embedding and reviewed Milvus/OpenSearch sinks, nondestructively. It can load/download the pinned model if uncached; requires those local services and model resources. Index/schema incompatibility is a hard failure, never a drop or schema repair. A printed SQLcommitted/pending status means partial progress, not completion. On partialfailure fix the reported local prerequisites then rerun the same reviewed file; SKUidentity and SQLids remainstable. Rows from another source are never overwritten, and no existing rows are deleted.
5. The initial file is directly usable. To regenerate localtestvalues with fresh timestamp, use `python scripts/generate_dev_catalog.py --output fixtures/dev_catalog_v1.json` within the opted-in devcontainer. Review its newSHA beforeapply.
6. Browse/search, ask product questions, inspect opening, add/remove products, review carttotals, open shipping form. No modelreply is claimed successful without your local provider retest. Opening still respects recency/diversity and independentcopyreview, so up10perrole is not a promise of40cards every time.
7. Stop before confirming payment. Current checkout confirmation creates a pending order and can initiate a real payment gateway. Syntheticrows remain blocked there. Safe offline checkout validation is the existing actualSQL/injectedgateway automated suite, not a fake production checkout. Interactive sandbox payment would require separately verified testcredentials/configuration and authority; this change does not enable it.

Fixtures prove deterministic data loading, SQLidentity, bounded pipeline behavior and local functionality where tested. They do not prove real offers, rights in thirdparty data, productquality, arbitraryLLM understanding, livepayments, owner rollout success or production readiness.

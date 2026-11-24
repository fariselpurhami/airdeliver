# Versioned synthetic local fixtures

`dev_catalog_v1.json` contains1000 deterministic, generic testproducts in the owner's seven categories. Source and generation basis: [field provenance and owner steps](../../../docs/verification/dev-fixture-generation-basis-v1.md).

Normal import format is version1 JSON: envelope `version`, `source_id`, `source_kind`, `authorised_source_url`, `rights_confirmed`, `offers_authorised`, `products`. Each product requires `sku`, `name`, `description`, `category`, `price` (decimal string with exactlytwo fractionaldigits), `currency`, `inventory` (integer), `image_url`, `source_url`, `licence`, `image_licence`, `inventory_verified_at`. Optional: `attributes`, `tags`, `rating`. Unknownfields reject. Atmost1000rows/16MiB; duplicateSKU reject. Actualsourceimports require actualrights/offer authority, publicHTTPS sources, freshstocktimestamp, no syntheticmarkers. Validators check shape and consistency, not legalrights or productreality.

This checked-in file is explicitly `source_kind=dev_fixture`. `rights_confirmed`/`offers_authorised` refer only to these synthetic testrecords and originalartwork, never permission for realcommerce. It cannot import unless `APP_ENV=development` and `AIRDELIVER_DEV_FIXTURES=true`. No CSV interface is claimed; JSON is the exact supported format.

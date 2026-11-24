# Empty opening, real catalog diagnosis

Owner live evidence: user3, total100, active100, positive stock100, demo100,
all inspected eligiblepools0. This establishes no real offers in that local DB,
not a Groq/ranking/cooldown failure. Do not remove demo markers, invent stock,
reseed synthetic data or delete/quarantine rows to make cards appear.

Additive fallback now distinguishes currentSQL catalogempty/demo-only/no-real-
eligiblestock/all-real-recent/unpublishedeligiblepool. Modelcopyfailure remains a
separate stage. Counts are not sent to the customer, only accurate status text.
Read-only inspect_opening_catalog.py uses actual timestampcooldown and currentSQL,
not the obsolete legacy seen-set. Redisfailure explicitly makes cooldown unknown.
Tests use actual migratedPG19. No provider/model/write in diagnostics.

Existing product creation is admin-authenticated POST /api/v1/products/. It writes
real supplied data to SQL, not a supplier connector. ProductCreate accepts SKU,
name, description, price, currency, inventory, category, image, tags, rating,
is_active. Supply actual records only; description must be a nonnull string;
use exact unique SKU<=128chars, name<=255, category<=128 to fit current SQL model.
No invented rating. Set valid uppercase3letter currency, positive actualstock,
activeonlywhenreal, nonnegative currentprice. Current cart supports USD only;
do not relabel nonUSD inventory. No paid account/key needed for manual actual
inventory entry. Requires existing administrator credentials and actual product
facts, image rights and authority to list/fulfil. Public web specs are not stock.

Opening bestsellers/trending SQLpools can see newly created realrows without
indexing. Their names are internal pools, not proof of sales/trends. Admin create
currently does not index OpenSearch/Milvus. Search/vector parity requires a separate
reviewed indexsync, not the syntheticseeder or an unapproved rebuild. A merchant
feed/import connector is not claimed to be available here. No ownerwrites run.

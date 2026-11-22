# Cart command invariants

## Scope and contracts

Backend HTTP/queue cart command validation and live catalog checks. Same routes,
public service methods,202 accepted envelopes, UI event shapes, optional bundle/
recovery paths. No feature/file removed. Existing valid integer inputs preserved;
invalid/bool/out-of-range identities and quantities are rejected. Frontend code,
visual/a11y modules N/A; HTTP consumer schemas checked through TestClient.
Python3.13/FastAPI0.165.0/Pydantic2.13.5/SQLAlchemy2.0.54/asyncpg0.32.0.
No upgrades, model/prompt/retrieval changes, schema migration or provider calls.

## Evidence and invariant

Sixteen newly added regression cases failed before the change. Internal cart
commands admitted nonpositive/unbounded quantities and invalid owner/product IDs.
Product existence alone let inactive/out-of-stock items into the cart; existing
line price/name remained stale. Cumulative quantity could exceed inventory/99.

Invariant: an add command must have bounded valid identifiers/quantity, current
active product and enough inventory at read time, and current price/name for the
changed line. API input and service validation both enforce relevant boundaries.
Add reads product with populate_existing, checks cumulative quantity before any
cart write, and refreshes the changed line's display facts. Stock is NOT reserved;
copy explicitly says it is checked again at checkout. Concurrent stock changes
can still happen after read. Checkout remains the purchase authority.

Native Pydantic/PG reads are used instead of new locks/infra. Trade-off: invalid
or unavailable adds fail without mutation, existing read/write race remains.

## Verification

* Baseline full suite633pass2skip.
* First added regression batch16fail19pass before changes.
* Full after changes668pass2skip20existing warnings, actual disposable migrated
  PostgreSQL19 and independent DB sessions for product facts.
* Six PG cases,12 internal command cases,17 HTTP schema cases added.
* Redis/cache publish transport is controlled in these tests; actual Redis
  concurrency, broker, browser event delivery and paid LLM NOT RUN here.
* compileall/git diff checks executed before checkpoint; no configured backend
  linter/typechecker, explicitly NOT RUN. No new endpoints/dependencies.

## Residuals, gates and rollback

Confirmed separate issues, not hidden by this patch: Redis cart read-modify-write
can lose concurrent edits; cache adapter error suppression can still create a
false cart-success path. HTTP optional recommendation wiring, actual accessory
compatibility and retrieval quality need separate work. Customer retention/
consent/deletion decisions remain unapproved and unchanged.

BE G1 PASS preserved valid contracts, G2/G3 N/A no financial CAS introduced;
G4 limited PASS runtime field checks, not full AuthZ/security certification;
G5 PASS bounded inputs, existing pool budget unchanged; G6 tests/compile PASS,
linter/typecheck NOT RUN; G7 no new retention/cleanup, cache-success residual
explicit; G8 PASS evidence honesty. BE traps1/2/3/4/5 N/A;6 PASS no new lease/
network/timer;7 PASS no eager clients;8 PASS scoped schema bounds and unchanged
exports, broad privacy audit still pending. FE runtime gates N/A.
System verdict READINESS_BLOCKED by residual cart persistence/concurrency and
unverified live acceptance, no production qualification claimed.
Rollback code only, no DB migration/data deletion/reseed. Invalid inputs would
again be admitted if reverted; avoid rollback absent an actual regression.

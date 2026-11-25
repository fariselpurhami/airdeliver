# CAP-23: setup/component code acceptance

Active HTTP SETUP_DISCOVERY plans generic categories with independent review,
then uses shared staged SQL-backed search and model-authored/reviewed copy.
The retained NLU ecosystem entrypoint extracts/reviews the current hard brief,
uses the same service and rechecks consent before publication. Its original
unreviewed method remains dormant, unchanged. No parallel planner replaces it.

Component identities now reject case/space duplicates before retrieval. Scoped
requirements/exclusions still require literal spans, exact component identity
and independent assignment review. Prior component scope cannot silently vanish.
Setup collection selection now takes at most one candidate per planned component
in retrieval order, avoiding multiple alternatives for the first category
consuming the aggregate budget. It does not optimize combinations. A shared row
cannot stand for two components. One aggregate currency/cap applies without
conversion. Each planned component has explicit selected IDs or a missing
selection status in writer/reviewer evidence. Completeness and compatibility
remain unverified, even when every query has a candidate. Retrieval relevance is
not physical compatibility, inclusion of all essential parts, or merchant proof.

Controlled plan/selection tests and real disposable SQL original-entrypoint tests
cover duplicate plans, literal/scoped assignment, missing components, competing
first-component alternatives, aggregate cap, currency, stale price, synthetic
rows, out-of-stock, planner rejection, invented/omitted budget, writer outage,
review rejection, target timeout and cancellation before/during writing. No cart,
message broker or conversation mutation is made by the read-only bridge. Existing
mounted HTTP/Redis setup dispatch and scoped-state tests remain part of the full
regression.39 focused cases pass. All2204 collected cases covered in fresh
disposable PostgreSQL19/realRedis runs:1099passed/3skipped and1100passed/4skipped,
with two bootstrap duplicates.

Code closure requires exact-head scan and both storage jobs plus fast-forward.
Live model planning, source adequacy, compatibility meaning and owner runtime
are still unverified and parked. No provider calls or owner-machine actions.

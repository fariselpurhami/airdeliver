# Recommendation catalog truth checkpoint

## Scope and contracts

Backend-only surgical strengthening, frontend modules N/A. Existing public
methods, query/model/prompt contract, search/ranking heuristics, bundle selection,
cart handlers and response shapes remain. No dependency upgrades or schema
migration. No user cache, collection, volume or product data is changed here.

Confirmed installed versions: Python3.13, FastAPI0.165.0, Pydantic2.13.5,
SQLModel0.0.50, SQLAlchemy2.0.54, asyncpg0.32.0, pymilvus3.0.2,
OpenSearch-py3.2.0, sentence-transformers6.3.0, torch2.15.0+cpu,
pytest9.1.1. No new SDK APIs; SQLAlchemy populate_existing executes against
real PostgreSQL19 and rehydrates existing session identity-map entries.

## Defect register and decision

Confirmed defects, four failing PostgreSQL regressions before changes:

* Bundle cache returned serialized product snapshots without checking current
  price, name, deactivation, deletion, or a changed anchor price/budget.
* Vector-alternative index filters were not reapplied after PG hydration, so
  stale index facts could surface currently inactive/out-of-budget/category rows.
* SQL alternative fallback did not exclude inactive products.

Invariant: cache/index supply candidate IDs, PostgreSQL supplies current display
facts and domain filters. Options were invalidation-only, short TTL, or readback.
Readback is used because TTL/invalidation alone cannot prove current facts.
Trade-off is extra database reads and possibly fewer recommendations, rather
than presenting stale catalog claims. No compatibility-learning substitute is
introduced. Current metadata still does not prove accessory compatibility.

Bundle cache writes bounded ID lists, accepts legacy snapshots only as candidate
IDs, hydrates live rows, removes anchor/deleted/inactive/out-of-budget items, and
continues existing retrieval when cache is malformed or has no valid rows.
The anchor is rehydrated as well. SQLAlchemy populate_existing refreshes rows
already in the identity map. Read-committed readback reflects facts at read time,
not an inventory reservation or protection against changes after the response.

## Verification ledger

* Baseline full suite:626pass2skip before these changes.
* Added first four PG regressions:4fail before fix, with actual persisted stale
  price/name, deactivation/deletion and independent-session mutation/readback.
* Final full disposable migrated PostgreSQL19 suite:633pass2skip20existing
  warnings. Seven added PG tests include ID-cache round-trip, identity-map
  refresh, and malformed cache preserving existing retrieval.
* Python compileall and git diff checks executed separately before checkpoint.
* Retrieval transport IDs/cache bytes controlled in tests; actual Milvus/
  OpenSearch integration remains covered by CI, not these PG regressions.
* Lint/typechecker NOT RUN: repository has no configured backend linter/typechecker
  in this checkpoint environment (ruff/mypy not installed). No invented pass.
* Live merchant inventory, GTE relevance, customer cart session and browser E2E
  NOT RUN. No paid LLM calls. No claim of enterprise throughput/security proof.

## Gate and trap audit

BE G1 PASS for preserved exports/schema; G2/G3 N/A, read-only catalog truth,
no accounting/CAS mutation added; G4 limited PASS for no new secrets/auth surface,
full security audit NOT RUN; G5 bounded cache consumption and alternative limit,
existing DB/network pool limits unchanged; G6 executed tests/compile PASS,
lint/typecheck NOT RUN; G7 existing logs/TTL preserved, no lifecycle change;
G8 PASS for scoped evidence and residuals. FE gates N/A, no UI changes.
BE traps1/2/3/4/5 N/A, no webhook/transition/CAS/event claim/accounting change;
trap6 PASS, no new leases/timers/network fetches; trap7 PASS, no eager clients;
trap8 PASS for preserved signatures and bounded cache/alternative reads.
Diagnostic rubric is not a release override. System verdict remains
READINESS_BLOCKED pending broader security, compatibility and live integration
acceptance. This checkpoint is an executed catalog-data integrity fix, not
PRODUCTION_QUALIFIED and not a complete platform certification.

Rollback: revert this checkpoint code only. No database migration/reseed needed.
Existing snapshot cache remains readable; new ID cache requires this reader.
On rolling back to old code, old reader rejects ID entries and falls through to
normal retrieval until TTL expires, rather than changing persisted products.

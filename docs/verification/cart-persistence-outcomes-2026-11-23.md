# Cart persistence outcomes

## Scope, evidence and preserved contracts

Python3.13/FastAPI0.165.0/redis-py from existing lock. Redis7 runtime family
matches Compose redis:7-bullseye; disposable test server is exactly7.4.2,
downloaded official tarball with SHA256 pinned in CI. No production dependency
upgrade or infrastructure change. Existing best-effort cache methods preserved.

Confirmed false-success boundary: authoritative cart state used best-effort
cache methods that suppress Redis errors. Reads could look like a missing cart;
writes could fail while add emitted success/confirmation. Corrupt cart hydration
reset state to empty and allowed an add to overwrite it. Five initial regression
cases failed before the change. A disconnected Redis test initially passed for
the wrong reason (missing method); after implementation it exercises actual
socket failure, not method absence.

Invariant: missing cart is distinct from unreadable/corrupt cart, and success
requires backend acknowledgement. Add strict required JSON read/write/delete
methods to the cache contract. NoOp explicitly inherits unsupported-operation
failure, never fabricated persistence. Redis implementation calls native GET/
SET/DEL without best-effort error suppression and checks SET acknowledgement.
Zero DEL is valid idempotent absence, not a fake affected-row success.

Cart add/remove/sync strict read/write failures raise CartPersistenceError;
clear uses strict delete. API returns503,Retry-After2,no-store with generic
reconciliation wording, not202. Worker receives exception for existing retry
policy. No automatic blind mutation retry added. Native timeout can mean an
uncertain commit, so response asks refresh before retry rather than guaranteeing
no change. Existing valid event shapes/routes remain. Corruption is preserved
for recovery, not deleted/reset silently. No customer retention policy changed.

## Executed verification and boundaries

Before:5failed1passed new tests, with caveat above. After:677pass2skip20existing
warnings through real migrated PostgreSQL19 and an isolated real Redis7 server.
Real Redis tests execute read/write/TTL/delete, malformed stored JSON, actual
server termination/socket failure, and successful cart add followed by outage.
Controlled-transport tests cover no false preview/success/confirmation after
write failure, no overwrite after read/corruption, clear failure, NoOp rejection,
and HTTP503/no-store/Retry-After contract with no internal error disclosure.
Compileall and diff checks executed before checkpoint. Lint/typechecker NOT RUN,
not installed/configured; no false toolchain qualification claim.

Frontend source inspected: useAIOrderingStore rejects non-OK responses and
shows an error for cart commands. Separate cart/page.tsx optimistically removes/
clears and swallows rejected HTTP promises. That UI divergence predates this
checkpoint and remains a confirmed follow-up. No frontend code changed here;
visual/accessibility/browser tests NOT RUN, no claim of full-stack completion.

## Residuals and gates

Redis read-modify-write concurrency can still lose edits. Save-cart uses a DB
commit plus best-effort Redis cleanup, a separate dual-write/reconciliation risk;
not fixed by this checkpoint. Strict PubSub/UI delivery is separate from cart
persistence acknowledgement. Inventory read is not reservation. No paid LLM,
no prompt/retrieval/model change, no migration/reseed or file/feature deletion.

BE G1 PASS valid method/routes preserved, intentional failure status defect fix;
G2/G3 N/A no new accounting/event/CAS;G4 limited PASS generic failure/no secret
logs in new paths, not complete audit;G5 tested actual Redis timeout boundary,
concurrent mutation unresolved;G6 test/compile PASS,lint/typecheck NOT RUN;
G7 failure surfaced, existing TTL preserved;G8 PASS scoped evidence.
BE traps1/2/3/4/5 N/A;6 PASS no fake native cancellation or leases;7 PASS lazy
Redis connection preserved;8 PASS signatures, generic errors and explicit
residuals. FE G2/G3 pending cart-page reconciliation, other FE modules N/A for
this backend-only patch. Verdict READINESS_BLOCKED for platform due confirmed
remaining races/UI/save cleanup, no production-qualified or scale claim.

Rollback code only, no data migration. Revert revives suppressed persistence
failures, so only for a reproduced regression, not routine operator recovery.

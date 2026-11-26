# C01 session policy preparation, 25 November 2026

## State
Additive, inactive preparation. Existing auth routes and NextAuth behavior are unchanged. No migration applied. Local PostgreSQL cases require the established disposable GitHub Actions environment and will skip elsewhere. Do not call this C01 complete or deploy this service alone.

## Owner-approved policy
Single-use refresh. Reuse revokes its entire session family. Logout revokes the current session. Disable revokes all sessions. Existing configured expiration durations do not change. Rotation descendants inherit the family's absolute expiry, so refreshing cannot extend its lifetime silently.

## Transaction contract
Lock the user, then session family for all policy mutations, including disable/logout. One successful rotation consumes an old digest and inserts its replacement in one commit. Store SHA-256 digests of high-entropy opaque refresh tokens, never raw refresh tokens. Used credentials remain until family retention cleanup so replay is detectable. A random or foreign token must not revoke a valid family. Commit replay revocation before raising an authentication rejection. Propagate database failures and cancellation without returning a new token.

Concurrency tradeoff: legitimate concurrent refreshes are indistinguishable from replay under the accepted strict policy. One request can win while reuse revokes the whole family, invalidating the winner's descendant. Clients must single-flight refresh across requests/tabs. This design favors replay containment, not a grace window.

## Atomic rollout still required
1. Review migration source and run upgrade only in specifically authorized environment. No real DB approval exists.
2. Backend login must create a session family and bind access JWTs to its ID. Refresh returns rotated refresh credentials and updates the cookie with unchanged expiry policy.
3. All access-token surfaces, including WebSocket tickets and optional-auth paths, must check active session state consistently. Current stateless legacy JWTs need an explicit transition policy, not a silent fallback around revocation.
4. Add authenticated logout and disable integration. Clear cookies on logout but do not confuse clearing a cookie with server revocation. Password-change/account-removal policies need explicit treatment.
5. NextAuth must keep refresh credentials server-only, single-flight refresh and rotate atomically. Do not expose refresh credentials in the browser session payload. Wire signout to backend revocation and document failure outcomes.
6. Test HTTP, cookies, multiple clients, cross-worker replay, disable/re-enable, logout, expired families, wrong-user tokens, cancellation, storage failures, network timeout after commit and lost replacement response.
7. Migration/rollback/retention/observability review, full exact-head CI, guarded merge and postmerge. Only then discuss activation.

## Evidence
Owner policy accepted in authenticated conversation on 25 November 2026. Current backend auth.py is stateless; current frontend auth.ts reads only the access token from login and expires it rather than rotating backend refresh credentials. No existing backend logout route was found in the inspected auth surface.

Sources read:
- https://www.rfc-editor.org/rfc/rfc9700.html
- https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html

These sources inform security design, not owner approval for migration or deployment.

## Additional offline fault checks

Eleven mocked transport/storage boundary cases pass for issue/rotation flush or commit outage, cancellation propagation, replay revocation commit ordering, unknown/foreign-token non-revocation and failed-revocation error propagation. The five real PostgreSQL tests still skip locally; these mocks do not establish transaction rollback, row locking or concurrency. No new migration was executed, no active auth route was changed and C01 disposable-CI migration authority remains unresolved here.

## Offline ancestry reconciliation, no migration execution

Current main05b95d32 was merged locally without changing deployed state. A new static AST graph test first failed because this prepared migration branched from f96bc435e876 while existing customer-memory/cart-journal migrations already extend that revision. Its parent now points to current graph head1b8de657a098, retaining a single future head. The graph test reads source literals only, never imports Alembic or runs DDL. Twelve static/fault tests pass; five real PostgreSQL policy tests remain skipped locally. Nothing pushed and no migration/rollback/database/schema action executed. Disposable-CI migration approval remains unanswered and active auth/NextAuth wiring remains absent.

## Scoped disposable-CI approval, 26 November 2026

The owner replied directly to the narrow disposable GitHub Actions migration
question with a conditional go-ahead if this is the professional/better option.
Testing real PostgreSQL transaction/lock semantics is better than claiming mocks
prove replay containment. Scope: synthetic hosted Actions DBs only, never his
machine or a real DB. No active auth/NextAuth rollout is authorized by this step.

The prepared migration now enforces hosted Actions, local PostgreSQL authority
and an airdeliver_test_* database name before additive DDL. Five refusing-scope
mock tests failed first, then six scope tests passed. No local DDL was executed.
18offline static/fault/scope tests pass;9PostgreSQL tests locally skip. Added real
DB cases cover absolute expiry, strict old-token retry after a lost successful
response, rollback after a synthetic post-flush failure, and disable waiting on a
rotation user lock. Actual CI execution and exact-head full results remain pending.
The existing GitHub Actions synthetic seed/model exception remains unchanged.

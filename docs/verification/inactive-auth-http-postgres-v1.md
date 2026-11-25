# S03: inactive login and refresh rejection

## Verified red boundary

Test-only head b137d36c: the complete PostgreSQL 19 CI suite reported 3 failed, 2743 passed, 3 skipped in189.86s. HTTP login and refresh for a disabled account returned200 instead of401. A refresh token issued before account disable also continued returning200 after a committed disable in a separate PostgreSQL session.

Evidence: https://github.com/fariselpurhami/airdeliver/actions/runs/45678107023/job/139431007059

Command: `poetry run python scripts/verify_postgres_integration.py`.

## Small additive fix

`authenticate_user` and the refresh endpoint now reject an inactive User at their existing unsuccessful-authentication branch. Existing generic401 responses and token/cookie formats stay unchanged. Password hashes, signing keys, schema and dependency versions are untouched.

Five new HTTP/PostgreSQL tests cover inactive login, inactive refresh, disable after token issuance, active login continuity and bad/unknown credentials. The password-validity branch is controlled in these policy tests; actual Argon2/bcrypt/password behavior is covered separately. Synthetic fixture writes are limited to disposable GitHub Actions.

Verified after fix locally: `python -m pytest -q tests/test_security_core.py tests/test_deps_auth.py`, 27 passed, one existing test-only short-key warning. Full fix-head CI and postmerge results remain pending, not claimed here.

## Remaining limits

An already issued access JWT can still be cryptographically decoded until expiry. Protected active-user routes perform their separate database guard. This change is not global access-token revocation, refresh rotation, one-time use or cross-worker replay prevention. C01 session policy is still held for the owner's decision. A database outage remains fail-closed, and S02 covers refresh outage/cancellation and concurrent reuse; no new deployment acceptance is implied.

A request that read an active account before a concurrent disable commit can still finish token issuance. This fix guarantees the tested sequential committed-disable boundary, not a serializable account-disable barrier. Defining a stronger revocation guarantee belongs to the session-policy decision.

Reference mapping, not certification: OWASP API2:2023 and ASVS5.0.x V6/V7/V9.

- https://github.com/OWASP/API-Security/blob/master/editions/2023/en/0xa2-broken-authentication.md
- https://cheatsheetseries.owasp.org/IndexASVS.html

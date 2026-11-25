# S02: refresh HTTP PostgreSQL scalar boundary

## Verified red reproduction

Test-only revision 862af0c2 ran the existing complete PostgreSQL 19 integration command, `poetry run python scripts/verify_postgres_integration.py`, in disposable GitHub Actions. The rustfs job reported 3 failed, 2738 passed, 3 skipped. Valid refresh requests via both Authorization header and cookie returned HTTP 500 instead of 200; four concurrent valid requests also returned 500. Invalid/expired/access/missing/unknown-token rejection, controlled outage and cancellation cases passed.

Evidence: https://github.com/fariselpurhami/airdeliver/actions/runs/45670689669/job/139404830391

## Minimal fix

`auth.py` now unwraps the SQLAlchemy result through `.scalars().first()` rather than treating the ORM Row as a User. Token format, signing keys, cookie/header precedence, stateless reuse and authorization roles are preserved. No schema, dependency, deployment or real-data change.

## Tests and classification

- Verified locally after fix: `python -m pytest -q tests/test_security_core.py tests/test_deps_auth.py`, 27 passed, one existing test-only short-key warning.
- Verified locally: 10 HTTP/PostgreSQL cases collected. These fixtures refuse writes outside GitHub Actions or a named `airdeliver_test_*` PostgreSQL database.
- Pending: full exact-head CI after fix, green HTTP/PostgreSQL outcomes and postmerge checks. This note does not claim those results before they run.
- Controlled outage and cancellation use injected sessions at the HTTP dependency boundary. This is not a live database/network fault-injection certification.
- The tests mount the actual auth router. Whole-application ingress/middleware and owner deployment acceptance remain separate.

## Remaining scope

S03 inactive-account rejection is separate. C01 session rotation, revocation and replay policy remain held for the owner's decision. Concurrent reuse tests document the current stateless behavior, not a claim of replay prevention. Existing outage behavior is fail-closed HTTP 500 without an access token, not a new availability contract.

Security reference mapping, not certification: OWASP API2:2023 Broken Authentication and ASVS 5.0.x V6/V7/V9.

- https://github.com/OWASP/API-Security/blob/master/editions/2023/en/0xa2-broken-authentication.md
- https://cheatsheetseries.owasp.org/IndexASVS.html
- https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html

Source code takes precedence over this note if later revisions differ.

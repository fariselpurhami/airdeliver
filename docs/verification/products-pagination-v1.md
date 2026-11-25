# S08: bounded products pagination

## Verified reproduction and fix

Before the fix, mounted products HTTP tests reported13 failed,8 passed. Negative skip, nonpositive or excessive limit, invalid page and giant integers reached SQL construction; page1 did not override an explicit skip even though later pages did. No provider call or database write was involved in this reproduction.

Command: `python -m pytest -q tests/test_products_pagination_http.py`.

The existing route now validates skip0–100000, limit1–100 and page1–100001; calculated page offsets above100000 are rejected422 before query execution. Page always overrides skip, including page1. Default limit100 and response list shape remain unchanged. Both slash and no-slash route registrations use the same checks.

Verified after fix: `python -m pytest -q tests/test_products_pagination_http.py tests/test_product_image_contract.py`,29 passed. SQL-boundary assertions inspect PostgreSQL-compiled LIMIT/OFFSET and verify rejected input never reaches the controlled session. This is real ASGI route validation with a controlled SQL result, not a production database load test. Full exact-head CI passed at03daf9ee8d02e9e78e4dc7c0dee6487d23bbf8c6, including both PostgreSQL storage jobs, frontend/typecheck/build/tests, Docker smoke and secret scan. Evidence: https://github.com/fariselpurhami/airdeliver/actions/runs/45683581301/job/139450169414 . Final documentation-head CI and postmerge remain pending.

## Rationale and limits

The100-item maximum follows the repository's existing orders/notifications limit. Offset100000 is an engineering guard against arbitrarily expensive deep OFFSET work, not a measured performance threshold or a claim of million-product browsing. Requests beyond that window now fail explicitly instead of silently scanning arbitrary depth. A future cursor/keyset contract is needed for larger traversal; no index migration is introduced here.

No ordering, catalog eligibility, category filtering, serialization, product write behavior or authorization change is included. Existing lack of a stable ordering means separate pages may shift during catalog updates; this fix is not a snapshot-consistent browsing contract. Large-but-valid offsets still have database cost. No throughput/latency guarantee follows from these tests.

Reference mapping, not certification: OWASP API4:2023 Unrestricted Resource Consumption. Source code and actual run receipts take precedence over this note.

https://wstg.owasp.org/latest/16-API_Testing/06-API_Rate_Limiting_and_Resource_Consumption/

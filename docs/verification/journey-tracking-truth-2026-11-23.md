# Journey item5: owned order detail and honest status display

User approved eight journey gaps, one at a time, US/USD launch. This PR addresses tracking/history truth only. No merge/deploy/migration/provider/email/payment call performed.

- Add authenticated GET /orders/me/{order_id}, query scoped to both order ID and owner, one response for nonexistent/other-owner records. Full positive32-bit DB ID bounds. SQL errors return a safe503. History/detail no-store. Existing paginated history preserved.
- Add stored order currency to the existing response model. Missing/invalid money is visibly unavailable, never inferred USD. USD is still the launch checkout currency; CAD exists only as a test fixture to detect hardcoded dollars.
- Tracking fetches one owned order, not newest100 history rows. Every-minute visible/online refresh, explicit manual refresh, stale-view warning on refresh failure, sign-in and missing/account-scoped errors. No invented ETA/carrier position. The last-updated field is the order record timestamp, not time of last carrier scan.
- Profile history uses the existing authenticated API client, readable canonical status labels, stored currency and real tracking links. All original history pagination and other profile modals retained.

## Evidence

Full backend on disposable migrated PostgreSQL19/Redis:1009passed4skipped20existing warnings. Focused HTTP+DB6passed:102owned orders, old one excluded from newest100 but direct detail succeeds; other-owner and absent share404; malformed/out-of-range IDs422;503does not leak error. Response excludes address/payment/internal checkout payloads. Auth-required boundary test.

Frontend initial full121tests22suites, TypeScript and production build pass. Added history contract test after initial run. Mobile390px and desktop1280px actual rendered component with production CSS inspected; fixture data, not logged-in live stack. Provider-free UI tests cover direct fetch, CAD vs USD, missing/expired session, refresh outage/stale view and recovery, malformed paths, unknown money/status. No shipped mocks.

## Deliberately outside this PR

No carrier/status-transition pipeline, ETA, refund/return implementation, cart runtime cutover, stock reservation, fees/tax policy, payment sandbox or reset rollout. These remain separate items. No full deployed browser→API acceptance claim. The original32connection Redis load test passed in this main-based full run; the separate reset-branch combined harness issue is not considered fixed by this result.

# Item 8: saved notification history and honest actions

Scope: additive history endpoint and existing notification page. No provider, email, push or SMS call; no schema migration, deployment or automatic dismissals. Existing list route and UI foundations remain.

- Authenticated GET `/notifications/history?page=1&limit=20`, max 100 rows, owner-scoped count/rows, stable created_at/id ordering, no-store. Page limit bounded. Offset pages are a current view, not an immutable snapshot: new inserts can shift later pages.
- Order CTA only accepts a positive bounded internal `/tracking/{id}` route, never arbitrary URLs. Existing non-route CTA labels do not pretend to be working buttons.
- Recheck once a minute while visible/online, on focus or by explicit refresh. No push-delivery claims.
- Read mutations await server success and revalidate. Failures remain visible.
- Existing explicit dismissal and 4-second undo retained. One pending dismissal at a time, pagination paused during it; no late undo once deletion starts. Failure revalidates and shows uncertainty, not false success. Unmount clears an unsent timer. Mute is visibly unavailable rather than a fake success.
- Touch actions are visible on mobile and keyboard focus. Existing page filters are explicitly page-local.

Verification:
- Disposable migrated PostgreSQL 19 + Redis full backend: 1007 passed, 4 skipped. Actual HTTP database test inserts 105 owned and one other-owner notice, checks pagination beyond 100, no overlap, CTA serialization, no-store and invalid bounds. No provider call.
- Frontend full tests: 116 passed in 22 suites. Link allowlist, pagination, read failure, dismissal failure, undo covered. tsc and production build pass.
- 390px and 1280px rendered page-content fixtures inspected. Width remains viewport width. These are deterministic rendered content fixtures, not authenticated live-session proof; shell/auth/provider end-to-end remains unproven.

Not closed: provider dispatch/delivery receipts, customer preferences/consent, queue retries and retention policy require separate decisions and proof. This draft does not claim full item-8 closure or production readiness. No merge without per-PR approval.

## Design revision after owner review

Replaced the decorative communications-log heading with clear notifications/account wording and lowercase airdeliver. Added persistent cyan/violet atmosphere and a subtle grid behind the retained background foundation, a glass saved-updates panel, balanced desktop information rail, grouped cards, contained refresh/filter controls and explicit pagination. Mobile actions remain visible with touch targets. Empty/loading states now explain their state without claiming channel health. In-app-only caveat remains visible.

Latest frontend proof: 118 tests/22 suites, tsc and production build pass. Inspected 390px populated/empty/loading content fixtures plus 1280px populated fixture, no horizontal overflow. This revision remains rendered-content proof, not authenticated full-shell proof.

Account isolation follow-up: notification cache keys now include the authenticated account, no private fetch runs before sign-in, pending unsent dismissal is cleared on account change, and signed-out view asks the customer to sign in. Frontend suite now 119 tests/22 suites, tsc and build pass. No change to the inspected populated design.

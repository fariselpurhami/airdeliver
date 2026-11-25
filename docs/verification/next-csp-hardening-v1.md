# S09: Next configuration and document CSP

## Verified boundary

Before the fix: `NODE_ENV=production node --test scripts/security-config.test.mjs` failed both checks. `NODE_ENV=production node node_modules/jest/bin/jest.js --config scripts/jest-security.config.mjs --runInBand` failed all12 proxy cases. These exercised the real NextRequest/NextResponse classes with a controlled auth result, not a deployed authentication acceptance test.

After the fix: both config tests and all12 proxy tests pass. `node node_modules/typescript/bin/tsc --noEmit` passes. Existing frontend suite:41 suites/218 tests pass. Local production build via `AUTH_SECRET=<synthetic> next build --webpack` passes. The Turbo build could not resolve the local dependency symlink outside its tracing root; full GitHub CI retains the canonical Turbo build and must pass before merge.

Production ignores no TypeScript build errors and logs no full fetch URLs. Server image optimization permits only HTTPS images.unsplash.com and ui-avatars.com, with SVG optimization disabled. Existing arbitrary supplier/avatar/chat images use the existing CatalogImage presentation path browser-direct, keeping their image URL and fallback without giving the server optimizer arbitrary fetch authority. Browser-direct images are still a privacy/tracking surface, not vetted catalog content.

The document proxy creates a fresh nonce and overwrites client nonce/CSP headers before Next rendering. The nonce is threaded through the existing viewport inline script. Public prefix routes require segment boundaries. A client prefetch header no longer bypasses authentication. Auth redirects, admin redirects, public pages and normal authenticated continuation all receive security headers. Auth error logs contain a fixed event, not the exception. Nonce-bearing document responses use private/no-store.

## Actual browser/visual checks

Built production login page returned200 with14 nonce-bearing scripts, no application errors or normal-load CSP violations. Initial check caught a blocked viewport inline script; after nonce threading the check passed. A parser-inserted script without the nonce was blocked. A direct automation-evaluated insertion was not accepted as evidence because automation can bypass the page policy. No login submission, payment or live speech/model operation was performed.

Inspected desktop login screenshot:form, product cards and footer remain legible and aligned. Inspected390px mobile screenshot:existing PWA guard redirects mobile non-standalone login to the mobile root funnel; root headline, button and footer remain visible without horizontal overflow. This existing rule was preserved, not changed or represented as mobile login acceptance. Standalone mobile PWA remains unverified.

## Limits and rollout

Initial full CI:frontend Turbo build/typecheck/tests and security checks passed;backend2788 passed/3 skipped/1 historical move-manifest hash failure. A separate exact-source security evolution receipt preserves the immutable move manifest and verifies the changed source hashes. Full exact-head CI passed at1985d9d8, including canonical Turbo production build, typecheck, frontend tests, both PostgreSQL/storage jobs, Docker smoke and scan. Evidence: https://github.com/fariselpurhami/airdeliver/actions/runs/45696764895/job/139496077309 . Final documentation-head CI and postmerge pending. Production deployment and final environment allowlists are not accepted here. Styles keep unsafe-inline for the existing motion UI. Image/connect HTTPS and secure WebSocket sources remain broad; frame/form sources name the existing Stripe/PayPal surfaces. This is not a strict data-exfiltration policy or XSS immunity. Plaintext cross-origin production API/WebSocket destinations are not permitted by this CSP; use HTTPS/WSS or same-origin deployment. Development permits its existing HTTP/WS paths and unsafe-eval. Existing trustHost behavior, proxy host-validation assumptions, permissions-policy camera/microphone restrictions, API routing exclusions, third-party dynamic scripts and complete payment/PWA/voice journeys remain separate deployment verification. No dependency upgrades or provider/purchase calls were introduced.

Sources read: https://nextjs.org/docs/app/guides/content-security-policy , https://nextjs.org/docs/app/api-reference/components/image , https://nextjs.org/docs/app/api-reference/config/next-config-js/typescript . OWASP mapping is a reference, not certification.

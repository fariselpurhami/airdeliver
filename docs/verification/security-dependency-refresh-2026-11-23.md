# Security dependency refresh, first checkpoint

- Next and eslint-config-next: 16.3.6 to 16.4.6.
- React and ReactDOM: 19.3.0 to 19.3.1.
- sharp: 0.35.4 to 0.35.5.
- Lockfile regenerated with existing dependency policies. Existing scripts, features and APIs preserved.
- Full local frontend 107 tests / 19 suites, TypeScript and production build pass. Real production Next boot and catalog/featured/detail fixture screenshots at 390px standalone and desktop pass. No owner backend, provider or payment request.
- pnpm audit before: 52 findings, including 2 critical. After this checkpoint: 32 findings, zero critical, 21 high, 8 moderate, 3 low. This is NOT a clean bill of health. Remaining transitive findings are recorded for the next security lock refresh and must be checked through parent dependency compatibility rather than blanket incompatible overrides. No claim of app exploitability or remediation beyond these packages.
- Backend source unchanged in this checkpoint; no database/seed/migration/deployment action. Full CI required before merge review. Owner machine rebuild/restart requires separate approval.

Sources: https://registry.npmjs.org/next/latest , https://registry.npmjs.org/react/latest , https://registry.npmjs.org/sharp/latest , https://nextjs.org/blog/november-2026-security-release , https://github.com/vercel/next.js/security/advisories/GHSA-673q-mjm6-r5xr .

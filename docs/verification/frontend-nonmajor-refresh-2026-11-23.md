# Compatible frontend dependency refresh

Refresh direct patch/minor dependencies and transitive dependencies within the current declared ranges, keeping both root workspace and standalone app locks. Includes axios1.21.1, Tailwind4.3.5, Zustand5.1.0, Recharts3.11.0, updated React Three bindings, beasties0.5.5, Motion13.5.1 and compatible tooling updates. Major Stripe/Motion and pre-1.0 Three upgrades are separate checkpoints.

Both workspace and isolated standalone frozen installs with actual scripts passed, each with107 tests/19 suites and TypeScript. Production build and production boot/catalog fixture screenshots at390px and desktop passed. No provider, payment, owner-database or machine action. Includes the standalone build-policy correction from PR12; do not merge before that correction's checks pass.

Both lock audits now report3 moderate,0 high,0 critical, down from32 findings. Remaining advisories: postcss-selector-parser pinned by latest Tailwind Typography, glob/minimatch held by Jest/test-exclude dependency ranges. Not claiming these resolved. They require separately tested dependency adaptation, not arbitrary major overrides.

Existing upstream peer gaps remain: ESLint10 vs plugins declaring <=9, TypeScript7 vs ts-jest<7 and typescript-eslint<6.1. Tests and tsc pass, but this does not prove unsupported combinations fully compatible. Latest parent versions do not yet widen these peer ranges. No downgrade or hidden pin added. Follow-up must investigate current upstream support and adapt or replace the affected integration without removing features.

Source versions checked live through npm registry; security evidence from pnpm audit. Examples: https://registry.npmjs.org/axios/latest , https://registry.npmjs.org/tailwindcss/latest , https://registry.npmjs.org/zustand/latest , https://registry.npmjs.org/recharts/latest , https://registry.npmjs.org/jest/latest , https://registry.npmjs.org/%40tailwindcss%2Ftypography/latest .

# Remaining frontend lock advisories

Parent packages are already current but retain affected transitive versions. Add narrow parent>child overrides in BOTH workspace policies, not global overrides:

- Tailwind Typography selector-parser6.0.10 ->6.1.5, patched same-major parser.
- Jest runtime/config/reporters and test-exclude glob ->14.0.6.
- test-exclude minimatch ->11.0.9.

The glob/minimatch changes cross majors. Their exact consuming APIs were inspected and explicit contracts added: selector AST round-trip; synchronous glob.sync and async glob; minimatch named function; test-exclude shouldInstrument and sync/async file enumeration. These pass alongside107 frontend tests/19 suites, tsc and production build in root and isolated standalone contexts. Real production boot and desktop/mobile fixture catalog visuals pass. CI repeats contracts and actual install scripts in both contexts.

Both locks now report0 pnpm audit findings. This means no matches in that registry audit at check time, NOT proof the application is vulnerability-free. Existing peer support gaps ESLint10/TypeScript7 remain documented from the prior checkpoint. This checkpoint is security remediation, not a claim every package is latest. Other majors/backend/runtime upgrades remain separate. No payment/provider/owner database calls, deployment or owner-machine action.

Source metadata: https://registry.npmjs.org/postcss-selector-parser/6.1.5 , https://registry.npmjs.org/glob/14.0.6 , https://registry.npmjs.org/minimatch/11.0.9 . Advisory matches before changes were obtained through pnpm audit. Scoped contracts preserve the API shape consumed by current parents, not an unsupported blanket replacement.

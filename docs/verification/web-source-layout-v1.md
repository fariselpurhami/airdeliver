# Web source boundary

Application sources move to src/app, src/components, src/hooks, src/lib,
src/types, src/auth.ts and src/proxy.ts. Every implementation byte is unchanged
and recorded in the adjacent SHA256 manifest. Public assets and framework/build
configuration stay at the web package root. No duplicate route aliases are
created: Next sees one app and one proxy boundary.

TypeScript aliases, shadcn CSS path, Jest coverage and source-inspection tests
point at the canonical source. Existing assertion content is retained. Frozen
install, TypeScript, 214 tests across 39 suites, scoped security dependency
contracts and actual Next production build pass. Full exact-head CI with actual
Docker and backend storage matrices remains required. No UI source/CSS changes,
provider/payment calls, deployment, owner migration or spend.

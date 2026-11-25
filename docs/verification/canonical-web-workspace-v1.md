# Canonical web dependency graph, stage2

Root pnpm-lock.yaml is the application dependency authority for CI and both
Docker modes. Root private package.json pins pnpm12.6.0 and offers optional
web:dev/build/test aliases. Existing apps/web commands remain. Nested app lock
and workspace config removed only with coordinated root-context Docker changes.

Application importer, package resolutions and snapshots compare equal to prior
rootlock: no application version upgrade. Pnpm12.6adds its own package-manager
metadata YAML document and root empty importer; this is manager bootstrap, not
a second application dependency graph. Fresh frozen install,214webtests/39suites,
typecheck and Next production build pass. Standalone actualoutput inspected at
.next/standalone/apps/web/server.js, not guessed. No owner environment touched.

Docker uses a default-deny Dockerfile-specific rootcontext allowlist. API source,
secrets, env files, Git metadata and localnode_modules/.next are excluded. Dev
keeps/app andexisting sourcebind; rootdependencyvirtualstore copiedto/node_modules
preserves relativepnpm links. Builderkeepsworkspace shape; runnercopiestraced
standalone tree andservesfrom/app/apps/web. Production healthchecksstaticlogo,
not nonexistent/api/health. New CI builds bothimages,resolvesactualmodulesatdev
path,andstartsproductionstaticHTTPwithnoAPI/providercalls. TheseDockerchecks
mustpassbeforemerge,localDockerdaemonisnotavailable. Combineddevcomposeservice,
project,volume,migrationandcommandcontractsunchanged.

11focusedworkspace/hygiene/rootcontractspluscoldfrozeninstall/webtypecheck/tests/
buildpasslocally. Fullexactheadscan/frontend/rustfs/seaweedandDockerrequired.
Thisisbuildreproducibility,notscaleorliveproductionacceptance.

# Project root audit, November23

Repository references are evidence of use, but manual developer entrypoints,
licenses, migration history and useful documentation need no automatic caller.
Absence of a grep hit alone does not establish safe deletion.

## Deleted editor artifacts, pending CI

- Admin User: contents identify a Vim9.1 viminfo/history file, no application or
  account configuration. No references. Accidentally committed editor state.
- settings.json: only Python editor formatting preferences, no application config
  or reference. Root placement is not the standard .vscode/settings.json location.
  No real runtime/build behavior uses it. No settings values or secrets removed.

## Kept, useful

- Makefile: manual up/down/logs/restart shortcuts for combined dev Compose and
  external network. No CI/Compose caller. Repaired/documented, dry-run tests.
- dev-auto-watch.sh: optional nodemon development rebuild helper. Corrected
  dev-only Compose and wrong lockfile path. Not automatically started.
- .env.dev.example / .env.example: secret-free configuration templates consumed
  by setup/docs/Compose. Local .env and secrets/ are ignored runtime material,
  preserved without inspecting values. .git/ is repository metadata, untouched.
- .gitignore: protects credentials/cache/data/build artifacts from commits.
- .gitattributes: model/LFS binary handling, not application runtime.
- .github/: CI workflows for tests/integrations, deployment and security checks.
- apps/: actual API/worker/frontend source and their tests/build definitions.
- db_init/: pgvector initialization SQL, mounted by both base and dev Compose.
- docker-compose.yml / docker-compose.dev.yml: combined runtime/dev foundation.
- docker-compose.dev-setup.yml: isolated one-shot local configuration helper.
- docker-compose.seed-ci.yml and storage-rustfs-ci/seaweed-ci overrides: actual
  isolated learned-embedding and storage integration jobs.
- docs/: deployment, security, storage and verification instructions/evidence.
- infra/: container/build, Kubernetes, storage, backup and dashboard foundations.
- monitoring/: Prometheus/Promtail config mounted by base Compose.
- pnpm-lock.yaml / pnpm-workspace.yaml: reproducible workspace dependency graph,
  workspace discovery and native build-package controls.
- .pnpmfile.cjs: pnpm install hook for typography peer metadata. Currently read
  during install; removal requires a clean frozen-lock install comparison first.
- LICENSE.txt: repository licensing, not disposable because code does not import it.
- README.md / RUNBOOK.md / SECURITY.md: useful project/operator/security guidance.
  Some README claims/version badges are stale, retained for correction, not proof
  of production readiness.
- monorepo.structure: human-readable project map; useful but can drift.
- scripts/: actual configuration, backup, proxy verification and manual data/model
  tools. Individual model-download/catalog tools still need semantic audit, not
  deleted because they have no automatic caller.
- tests/: root load-test scenario. Does not prove million-user capacity by existing.

## Deleted stale duplicate schema dumps, pending CI

- schema.sql / clean_schema.sql: unused historical PostgreSQL16 schema-only dumps.
  No DROP, INSERT, COPY, custom functions or triggers. Both duplicate11tables
  from initial Alembic, but omit CREATE TABLE notification_subscriptions while
  later altering that missing table, so neither is a complete bootstrap. They
  omit current transaction ID, shipping and outbox/request-journal foundations.
  No executable caller: no Compose mount, CI/script or migration load. Re-running
  them against a migrated database would collide with existing CREATE TABLEs.
  Alembic is the single tested schema path. Historical migration comments about
  past installations remain valid and are not runtime file dependencies.

## Retained pending narrower validation, not marked safe-to-delete
- rootCA.pem: mkcert development public CA certificate, not a private key. No
  current repo reference found. Could have been manually installed in a browser;
  check certificate/TLS setup before removing rather than infer no use from grep.
- vercel.json: intended deployment configuration, no active Vercel deployment
  established. Heavy stateful API/WS path needs deployment review; configuration
  age does not authorize silently breaking an intended deployment target.

## Local-only folder reported by user

- docker/: absent in this checkout and no tracked contents. No project-relative
  reference found. Host /var/lib/docker mounts are unrelated Docker engine state.
  If empty on the user's computer, it is a local leftover safe to remove there;
  nothing was removed remotely. Git does not track empty directories.

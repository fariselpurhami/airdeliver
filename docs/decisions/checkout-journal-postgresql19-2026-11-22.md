# Checkout journal and PostgreSQL 19 verification, 2026-11-22

## Decision

PostgreSQL 19.0 is the current stable major release, released November 19, 2026. The official support table gives November 19, 2031 as its final release date. The application stack has now passed real PostgreSQL 19 verification, including pgvector 0.8.7 and asyncpg 0.32.0. **Deployment DB defaults remain on 16**, because the existing production backup container's published `latest` image maps to PostgreSQL 18, with no published 19 tag found. A verified 19-capable backup and restore path is a release gate, not an optional follow-up.

Nothing here upgrades an existing database, deletes a volume, or deletes historical rows. Existing dev data must remain on its current PG16 volume until an explicit migration is planned and restored successfully into a separate target. PostgreSQL 16 itself remains supported through November 9, 2028 according to the official table.

## Verified changes

- Durable owner-bound checkout request UUID, unique database constraint and frozen provider request. Replays do not create a second order or reread a mutable cart. An expiring, fenced setup lease keeps stale provider responses from overwriting newer attempts.
- Provider network operations occur after the durable database commit, not inside an imaginary distributed atomic transaction. Unknown outcomes remain pending; retry uses the same stored provider request and idempotency key. After a conservative one-hour window, reconciliation is required rather than another provider POST.
- Browser request identity survives retries/reloads; HTTP handoff does not require a connected socket. New request-bound handoffs cannot replace a different active checkout. Errors do not falsely promise that no charge occurred.
- CORS accepts browser origin normalization and the required checkout headers. HTTP tests cover UUID validation, owner injection, status mapping and no-store responses.
- Explicit TIMESTAMPTZ model/migration alignment fixes a reproduced two-hour round-trip shift. A populated naive timestamp column requires a verified source timezone. Existing timezone-aware columns are left unchanged.
- A historical fresh-install migration now tolerates cleanup columns that never existed in the initial schema.
- asyncpg 0.32.0 is locked and reflected in both pip requirements files. Unlike 0.31, its release notes explicitly include PostgreSQL 19 support. Other pre-existing pip-export drift is not claimed fixed.
- A prepared backend CI template at `docs/ci/backend-ci-postgres19.yml` starts a disposable pgvector/PostgreSQL 19 service, verifies server major, extension version and a real vector distance query, migrates through Alembic head, and runs the full test suite. Its helper refuses a database not named `airdeliver_test_*`. The active workflow remains unchanged: GitHub rejected modifying it because the existing credential lacks workflow scope. Activating this template is still pending; no permission was widened.

## Evidence

- Official PostgreSQL 19.0 release archive downloaded and checked against its published SHA-256. A native disposable server was built from it, without ICU/readline for this verification environment. This is not a Docker-image boot test or a production server configuration.
- pgvector 0.8.7 compiled against that server. `CREATE EXTENSION vector` succeeded and a vector distance smoke test returned 5.
- Exact locked asyncpg 0.32 / SQLAlchemy 2.0.54 / Alembic 1.20 / PostgreSQL 19.0 stack: **491 tests passed**, including fresh migration, independent concurrent checkout transactions, fresh-session replay, strict timestamp instant preservation and the repeatable CI helper.
- Same 491 tests passed on the disposable PostgreSQL 16.2 verification runtime. This old runtime is a compatibility test, not a recommended production patch level.
- Frontend: **50 tests passed** using the existing CI command's coverage setting, plus TypeScript and production Webpack build. The repository-wide global coverage threshold is not met and is not represented as met.
- Mobile rendering of the actual component's uncertain-checkout state was inspected at 390px: fields, full warning, profile review link and buttons fit without horizontal clipping.

## Existing-data gates

Do not run `down -v`, remove the named database volume, or point PostgreSQL 19 directly at PostgreSQL 16's data directory. Changing only an image tag is not a major-version data migration.

Before applying the timestamp migration to populated data, take and validate a backup. Establish what timezone the existing naive values represent. Neither the operator's current location nor the current PostgreSQL session timezone proves this. Supply the verified IANA zone as `LEGACY_TIMESTAMP_TIMEZONE` through the application container environment or Alembic `-x legacy_timestamp_timezone=...`. Empty installations need no historical-zone choice. A wrong supplied zone can preserve rows but change the represented instants. Downgrade to naive timestamps is intentionally refused.

A future 19 rollout must use the 18+ container layout: volume at `/var/lib/postgresql`, default PGDATA `/var/lib/postgresql/19/docker`. The upstream entrypoint checks legacy data directories and refuses unsafe initialization. Restore into a separate target, test data counts and representative instants, exercise checkout and a full backup/restore cycle, then plan the cutover. Keep the original volume and a tested rollback plan. The PostgreSQL 19 pgvector image publishes amd64 and arm64 variants, including the Intel architecture needed by the user's Mac.

## Remaining work

The backup image chain blocks the default major switch. No full Compose boot, Kubernetes rollout, existing-volume upgrade or real payment was performed. Stock is checked, not reserved. Provider merchant-account rotation binding, journal/client-key retention, legacy handoff/finalization cleanup and deeper payment/outbox recovery remain separate work. This checkpoint is not a platform-wide production-ready claim.

## Sources

1. PostgreSQL release announcement: https://www.postgresql.org/about/news/postgresql-19-released-3449/
2. PostgreSQL support and upgrade policy: https://www.postgresql.org/support/versioning/
3. PostgreSQL press FAQ: https://www.postgresql.org/about/press/faq/
4. Official release source/checksum directory: https://ftp.postgresql.org/pub/source/v19.0/
5. asyncpg 0.32.0 release notes: https://github.com/MagicStack/asyncpg/releases/tag/v0.32.0
6. SQLAlchemy PostgreSQL support: https://docs.sqlalchemy.org/en/20/dialects/postgresql.html
7. pgvector images and architectures: https://hub.docker.com/r/pgvector/pgvector/tags
8. pgvector PostgreSQL 19 build matrix: https://github.com/pgvector/pgvector/blob/35ab919b/.github/workflows/build.yml
9. Official container volume layout: https://github.com/docker-library/docs/blob/master/postgres/README.md
10. Official container old-data guard: https://github.com/docker-library/postgres/blob/master/docker-entrypoint.sh
11. Existing backup image tag list: https://hub.docker.com/r/prodrigestivill/postgres-backup-local/tags

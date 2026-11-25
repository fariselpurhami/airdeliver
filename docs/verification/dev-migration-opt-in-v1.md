# Development migration opt-in gate

Combined base+dev Compose previously ran upgrade-head and initial-data automatically on whole-stack startup. That is unsafe while a database revision is deliberately held. The dev migrator now defaults to a successful no-op with an explicit skip message. It performs neither Alembic nor seed work unless the owner explicitly sets AIRDELIVER_DEV_ALLOW_MIGRATIONS=1. No such activation is part of this patch.

Production Compose keeps its existing migration command unchanged. The migration source, downgrade restriction and initial-data implementation are retained. Existing initialized development databases can restart without advancing schema; a fresh database is not initialized by the default skip and needs a separately reviewed backup/restore/migration plan. Exiting0 here means skipped, not schema-current or initialized. API health is not proof of schema compatibility. Do not set the gate merely to silence an error or rebuild and retry an old migrator while a hold is active.

The owner reported a stale migrator could not locate revision0a7cd546f987 and exited255 before an upgrade step. At18:29 Cairo the owner supplied a successful READ ONLY query showing database airdeliver at revision0a7cd546f987 and both cart journal tables absent. This verifies the held schema after the failure; no rollback or stamp was needed. This patch runs no owner-machine command or migration and makes no rollback claim.

Tests execute the extracted shell with an empty PATH for default/invalid settings and inert local executables for explicit opt-in. They prove migration-before-seed ordering and that a failed migration cannot fall through into seeding. No live database or provider is contacted. Full exact-head CI remains required. Normal source-only refreshes should still use the approved service list and --no-deps.


## Source and image freshness are separate

Dev migrator mounts the current backend/api checkout read-only at /app, the same current source used by the dev API. Migration files, Alembic environment and models therefore no longer come from a stale baked-in migration copy. Production keeps immutable source packaging and has no dev bind mount. The explicit production build target makes the dependency packaging choice stable rather than implicitly using the last Dockerfile stage.

The dependency image still must be rebuilt after pyproject.toml, poetry.lock or Dockerfile changes. From the repo root, the existing combined Compose build of api-migrator refreshes its image without starting it or touching a database. A build is not migration approval; never follow it with a gate-enabled startup while a hold is active. Current checkout availability is required for dev; there is no silent fallback to an old embedded revision. Source inspection found the migrator, initialization module, migration files and setup-fs all have active consumers, so none was deleted as an allegedly unused leftover.

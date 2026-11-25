# Canonical frontend/web and backend/api

The owner selected flat frontend and backend boundaries. Sources move from
apps/web to frontend/web and from apps/api to backend/api. Relative apps/web
and apps/api symlinks are compatibility aliases, not duplicate code trees.
The existing airdeliver/apps/web package identity and root/app CLI commands
remain. Workspace globs exclude the aliases and discover the web package once.

Docker, combined Compose, CI, current scripts/docs and path assertions change
together. Container /app mounts, services, volumes, project names and migration
commands are unchanged. Immutable fixture/evaluation JSON bytes and SHA256
bindings are preserved. Historical verification documents retain their old
paths, which resolve through compatibility aliases. No business methods or
functions are removed. No owner stack, provider, spend, deployment or migration
action is performed.

Local validation: cold frozen install with identical application dependency
resolutions and only an importer path change; 214 web tests in 39 suites;
TypeScript; actual Next production build. Disposable PostgreSQL 19 and real
Redis backend splits: 1411 passed/24 skipped and 1130 passed/4 skipped. Two
bootstrap modules repeat to register existing SQLite compile hooks. Eighteen
focused ownership, compatibility, entrypoint and mount-path contracts pass.
The local Docker engine is unavailable; actual Docker integration and full CI
are required on the exact head before merge. This is not a production or scale
readiness claim.

# PostgreSQL 19 deployment and local bootstrap

The PG19 backup/restore and fresh-config Docker checkpoint passed CI: https://github.com/fariselpurhami/airdeliver/actions/runs/45062515486 . This does not certify the full platform as production-ready.

## Fresh local development without existing credentials

```sh
LOCAL_UID="$(id -u)" LOCAL_GID="$(id -g)" docker compose --env-file /dev/null -f docker-compose.dev-setup.yml run --rm configure --fresh
docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml -p airdeliver_dev up --build -V
```

Fresh mode generates development-only credentials locally. It records unique new PG19 and RabbitMQ volume names in `.env.dev`, rather than pairing new passwords with unknown old storage. It does not overwrite an existing `.env.dev`, original secret files, `.env`, or old volumes. No passwords need to be pasted anywhere. The default helper command below remains the preservation path for an existing setup.

## Existing local development checkout

Requires Docker Desktop with Docker Compose 2.24.4 or newer. Run from the repository root. The setup service reads existing local credentials without printing them. It creates `.env.dev` and `secrets/dev` with private file permissions. It does not overwrite `.env`, original secret files, an existing `.env.dev`, or any Docker data volume.

```sh
LOCAL_UID="$(id -u)" LOCAL_GID="$(id -g)" docker compose --env-file /dev/null -f docker-compose.dev-setup.yml run --rm configure
docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml -p airdeliver_dev config --quiet
docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml -p airdeliver_dev up --build -V
```

This is the combined base plus development flow. The explicit dev env file is necessary because Compose interpolates required base values before merging overrides. Production's required security values remain required.

Development starts a fresh PostgreSQL 19 cluster in `airdeliver_dev_postgres19-data`, mounted at `/var/lib/postgresql`, the PostgreSQL 18+ image layout. The old `airdeliver_dev_postgres-data` volume is unused and not deleted. Do not run `down -v` to perform this change. After verifying the new installation and deciding no old local data is needed, the owner can inspect and remove only the old named volume themselves.

Stripe is optional. Leave both dev Stripe keys blank if unavailable. A configured Stripe pair must be TEST keys. Missing adapters are unavailable, not successful payments. The helper preserves existing database and RabbitMQ credentials and refuses to guess them if absent. A new checkout without existing credentials needs separate explicit fresh configuration, not this preservation command.

## Production and Kubernetes

The PG19 server image is pinned by multi-platform digest. The backup image builds PG19 clients from the same pinned PG19 foundation and retains the prior backup scheduler, hooks, and daily/weekly/monthly retention from an immutable upstream image. Build context contains only `infra/postgres-backup`, not application secrets. The OS package installation is not fully reproducible because apt packages are not version-pinned.

Do not attach existing PG16 data and expect an in-place upgrade. Existing deployments need a verified logical backup and restore to a separate empty PG19 target, row checks, a cutover plan, and retained rollback data. Historical naive timestamps require the operator's verified timezone. The migration must not guess it. Never remove existing volumes or PVCs as an upgrade step.

A backup can be initiated inside the backup service with `/backup.sh`. Restore takes an archive and a new, unused target database name:

```sh
/restore.sh /backups/last/SELECTED_ARCHIVE.dump NEW_DATABASE_NAME
```

The restore creates the target itself and refuses any existing target. It does not clean, drop, or replace existing databases. A failed restore may leave a partial newly created target for inspection; it is not a completed cutover. Restore only trusted archives because PostgreSQL restore can execute SQL from them. Backups still need operator-managed off-host storage, encryption/access control, capacity monitoring, and recurring recovery drills.

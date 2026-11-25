#!/usr/bin/env bash
# Back up the already-running dev database without loading Compose or changing it.
set -euo pipefail
umask 077
# Resolve both the canonical script and the historical relative symlink.
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
if [ "${script_dir##*/}" = ops ]; then
  cd "$script_dir/../.."
else
  cd "$script_dir/.."
fi
mkdir -p backups
archive=$(mktemp "backups/airdeliver-dev-$(date -u +%Y%m%dT%H%M%SZ).dump.XXXXXX")
container=${AIRDELIVER_POSTGRES_CONTAINER:-airdeliver-db}

pg_command() {
  docker exec -i "$container" sh -ec '
    PGUSER=${POSTGRES_USER:-}
    PGDATABASE=${POSTGRES_DB:-}
    PGPASSWORD=${POSTGRES_PASSWORD:-}
    if [ -n "${POSTGRES_USER_FILE:-}" ]; then PGUSER=$(cat "$POSTGRES_USER_FILE"); fi
    if [ -n "${POSTGRES_DB_FILE:-}" ]; then PGDATABASE=$(cat "$POSTGRES_DB_FILE"); fi
    if [ -n "${POSTGRES_PASSWORD_FILE:-}" ]; then PGPASSWORD=$(cat "$POSTGRES_PASSWORD_FILE"); fi
    if [ -z "$PGUSER" ] || [ -z "$PGDATABASE" ]; then
      echo "Existing database identity is unavailable. No default database will be guessed." >&2
      exit 1
    fi
    export PGUSER PGDATABASE PGPASSWORD
    exec "$@"
  ' sh "$@"
}

if ! pg_command pg_dump --no-password --format=custom > "$archive"; then
  mv "$archive" "$archive.incomplete"
  echo 'Backup failed. Do not migrate or remove volumes. An incomplete archive was retained.' >&2
  exit 1
fi
pg_command pg_restore --list < "$archive" > "$archive.list"
# This only reads metadata/counts. It does not choose a historical timezone.
pg_command psql --no-password --no-psqlrc --set=ON_ERROR_STOP=1 <<'SQL' > "$archive.preflight.txt"
BEGIN READ ONLY;
SELECT current_database() AS database, current_setting('TimeZone') AS current_session_timezone;
SELECT count(*) AS current_product_rows FROM public.products;
SELECT coalesce(string_agg(format(
  'SELECT %L AS legacy_naive_column, count(%I) AS nonnull_values FROM %I.%I',
  table_name || '.' || column_name, column_name, table_schema, table_name
), ' UNION ALL '), 'SELECT ''none'' AS legacy_naive_column, 0 AS nonnull_values')
FROM information_schema.columns
WHERE table_schema='public' AND data_type='timestamp without time zone'
AND (table_name,column_name) IN (
  ('products','created_at'),('products','updated_at'),
  ('users','created_at'),('users','updated_at'),('users','last_login'),
  ('orders','created_at'),('orders','updated_at'),('orders','paid_at'),
  ('user_activities','created_at'),('user_badges','awarded_at'),
  ('audit_trails','timestamp'),('ai_memory','last_updated'),('notifications','created_at')
)
\gexec
COMMIT;
SQL
printf 'Archive: %s\n' "$archive"
printf 'Archive index is readable. A full restore was not performed.\n'
printf 'Read-only preflight: %s\n' "$archive.preflight.txt"
cat "$archive.preflight.txt"
printf 'Existing data and Docker volumes were not changed. Do not guess a historical timezone.\n'

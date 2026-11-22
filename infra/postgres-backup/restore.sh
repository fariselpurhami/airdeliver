#!/usr/bin/env bash
# Restore only into a newly created database. Never clean/overwrite a target.
set -Eeuo pipefail
if [ "$#" -ne 2 ]; then
  echo 'Usage: /restore.sh /backups/path.dump NEW_DATABASE_NAME' >&2
  exit 2
fi
archive=$1
target=$2
if [[ ! "$target" =~ ^[A-Za-z_][A-Za-z0-9_]{0,62}$ ]]; then
  echo 'Use a new database name of at most 63 ASCII identifier characters.' >&2
  exit 2
fi
if [ ! -r "$archive" ]; then
  echo 'The selected backup archive is not readable.' >&2
  exit 1
fi
source /env.sh
# Read the entire TOC before creating anything. This is not an authenticity check.
pg_restore --list "$archive" | wc -l
# createdb fails atomically if the target already exists, even if it is empty.
createdb --maintenance-db=postgres -- "$target"
pg_restore --exit-on-error --no-owner --dbname="$target" "$archive"
echo "Restore completed into new database: $target"
echo 'No existing database was overwritten. Verify rows before any cutover.'

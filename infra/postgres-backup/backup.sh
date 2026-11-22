#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
mkdir -p "${BACKUP_DIR:-/backups}"
# Scheduled and manual backups share the same lock and retention foundation.
exec flock --wait 300 "${BACKUP_DIR:-/backups}/.airdeliver-backup.lock" /upstream-backup.sh "$@"

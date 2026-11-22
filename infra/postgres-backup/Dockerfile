# Keep the existing scheduler/retention foundation, replace only its PG client.
FROM prodrigestivill/postgres-backup-local:18-debian-d257e5d@sha256:f70742ebe42b2277689b028d1fd15aa80f77cffa01da163cc9f85a6ff1866e7f AS foundation
FROM pgvector/pgvector:0.8.7-pg19-bookworm@sha256:89879f41d564f67b0c1462a491d16fcbc6de39ac10db17e7a4bba2138a5e0ba5

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates util-linux && rm -rf /var/lib/apt/lists/*
COPY --from=foundation /usr/local/bin/go-cron /usr/local/bin/go-cron
COPY --from=foundation /env.sh /init.sh /
COPY --from=foundation /backup.sh /upstream-backup.sh
COPY --from=foundation /hooks /hooks
COPY backup.sh /backup.sh
COPY restore.sh /restore.sh
COPY UPSTREAM_LICENSE /usr/share/doc/airdeliver-backup/UPSTREAM_LICENSE
RUN chmod 755 /backup.sh /restore.sh && mkdir -p /backups && pg_dump --version | grep ' 19.0' && command -v flock
ENV POSTGRES_DB="**None**" POSTGRES_DB_FILE="**None**" POSTGRES_HOST="**None**" POSTGRES_PORT=5432 \
    POSTGRES_USER="**None**" POSTGRES_USER_FILE="**None**" POSTGRES_PASSWORD="**None**" POSTGRES_PASSWORD_FILE="**None**" \
    POSTGRES_PASSFILE_STORE="**None**" POSTGRES_EXTRA_OPTS="-Fc -Z1" POSTGRES_CLUSTER="FALSE" \
    SCHEDULE="@daily" VALIDATE_ON_START="TRUE" BACKUP_ON_START="FALSE" BACKUP_DIR="/backups" BACKUP_SUFFIX=".dump" \
    BACKUP_LATEST_TYPE="symlink" BACKUP_KEEP_DAYS=7 BACKUP_KEEP_WEEKS=4 BACKUP_KEEP_MONTHS=6 BACKUP_KEEP_MINS=1440 \
    HEALTHCHECK_PORT=8080 WEBHOOK_URL="**None**" WEBHOOK_ERROR_URL="**None**" WEBHOOK_PRE_BACKUP_URL="**None**" \
    WEBHOOK_POST_BACKUP_URL="**None**" WEBHOOK_EXTRA_ARGS=""
VOLUME /backups
ENTRYPOINT []
CMD ["/init.sh"]
HEALTHCHECK --interval=5m --timeout=3s CMD curl -fsS "http://localhost:$HEALTHCHECK_PORT/" || exit 1

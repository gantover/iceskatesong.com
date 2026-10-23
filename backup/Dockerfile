# Same image as the postgres service so pg_dump and psql match the server's major version.
FROM postgres:18
COPY --from=rclone/rclone:1.75.2 /usr/local/bin/rclone /usr/local/bin/rclone
# Configured only through RCLONE_CONFIG_R2_* env vars; no config file.
ENV RCLONE_CONFIG=/dev/null
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
COPY backup.sh restore.sh /usr/local/bin/
# The postgres image stops with SIGINT, which this bash loop ignores.
STOPSIGNAL SIGTERM
# Nightly at 03:00 UTC. Sleeping to a clock time, not 24h, so a container restart doesn't move the schedule.
CMD ["bash", "-c", "while :; do sleep $(( ($(date -d 03:00 +%s) - $(date +%s) + 86400) % 86400 + 1 )); backup.sh || echo 'backup failed' >&2; done"]

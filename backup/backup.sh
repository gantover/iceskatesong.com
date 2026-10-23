#!/bin/bash
# One backup: pg_dump → gzip → R2, then drop dumps older than 30 days, then ping Healthchecks.
# Any failure exits before the ping, so Healthchecks alerts on a missed night.
set -euo pipefail
: "${R2_BUCKET:?}" "${HEALTHCHECKS_URL:?}"

name="iceskatesong-$(date -u +%Y-%m-%dT%H%M%SZ).sql.gz"
trap 'rm -f "/tmp/$name"' EXIT
# A local file first, so a dump that dies halfway never reaches R2 as a "latest" backup.
# No owner or grants, so it restores under whatever POSTGRES_USER the target host uses.
pg_dump -d "$DATABASE_URL" --no-owner --no-privileges | gzip > "/tmp/$name"
rclone copy "/tmp/$name" "r2:$R2_BUCKET/postgres/"
rclone delete --min-age 30d "r2:$R2_BUCKET/postgres/"
curl -fsS -m 10 --retry 3 -o /dev/null "$HEALTHCHECKS_URL"
echo "backed up $name"

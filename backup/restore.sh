#!/bin/bash
# Restore a dump from R2 into an empty database. Usage: restore.sh [dump name], default the newest.
set -euo pipefail
: "${R2_BUCKET:?}"

name=${1:-$(rclone lsf "r2:$R2_BUCKET/postgres/" | sort | tail -n 1)}
[ -n "$name" ] || { echo "no dumps in r2:$R2_BUCKET/postgres/" >&2; exit 1; }
# Plain SQL won't restore over existing tables; refuse rather than half-merge into live data.
tables=$(psql -d "$DATABASE_URL" -Atc "select count(*) from pg_tables where schemaname = 'public'")
[ "$tables" = 0 ] || {
    echo "the database has $tables tables: restore needs a fresh pgdata volume, before migrate runs" >&2
    exit 1
}
rclone cat "r2:$R2_BUCKET/postgres/$name" | gunzip | psql -d "$DATABASE_URL" -q -v ON_ERROR_STOP=1 --single-transaction > /dev/null
echo "restored $name"

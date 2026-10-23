#!/bin/sh
# Restore a backup from R2 into this checkout's Compose Postgres, which must be fresh (no pgdata volume yet).
# Usage: scripts/restore.sh [dump name], default the newest. Needs the R2_* values in .env.
set -eu
cd "$(dirname "$0")/.."
docker compose up -d --wait postgres
docker compose run --rm --no-deps backup restore.sh "$@"

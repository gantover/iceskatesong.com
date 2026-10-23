#!/bin/sh
# Run on the box: pull main and rebuild whatever changed.
set -eu
cd "$(dirname "$0")/.."
git pull --ff-only
docker compose up -d --build

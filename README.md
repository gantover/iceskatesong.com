# iceskatesong.com

What music each figure skater skated to, with the official video. See [PRD.md](PRD.md) and [GLOSSARY.md](GLOSSARY.md).

## Setting up a machine

Install these once per machine. Everything else (Node packages, Python and its packages, Postgres) comes from the lockfiles or Docker.

| Tool | Why | Arch / CachyOS |
|---|---|---|
| Docker + Compose | runs the whole stack | `docker docker-compose` |
| Docker Buildx | builds the ARM64 images for the box | `docker-buildx` |
| QEMU user emulation | lets Buildx run ARM64 build steps on an x86 machine | `qemu-user-static qemu-user-static-binfmt` |
| Node.js (any recent) | runs pnpm; pnpm then installs the pinned Node 24 from `web/package.json` | `nodejs npm` |
| pnpm 11+ | switches itself to the version pinned in `web/package.json` | `npm i -g pnpm` |
| uv | Python projects in `db/` and `import/`; fetches Python 3.14 itself | `uv` |
| GitHub CLI | issues live on GitHub | `github-cli`, then `gh auth login` |
| Tailscale | reaches the homeserver (`ssh rock5itx`) | `tailscale`, then log in |

Check: `cat /proc/sys/fs/binfmt_misc/qemu-aarch64` says `enabled`, and `docker buildx ls` lists `linux/arm64`.

For Claude Code, the project's `.mcp.json` runs the Playwright MCP through `npx` with Playwright's own Chromium (no Google Chrome needed). Once per machine, and again after bumping its version in `.mcp.json`, install the matching browser:

```sh
npx -y -p @playwright/mcp@0.0.83 playwright install chromium
```

## Running it

```sh
cp .env.example .env          # optional on a dev machine; required on the box
docker compose up --build     # postgres → migrate → web on http://localhost:8080, import polls for Imports

cd web && pnpm install
pnpm test                     # needs the Compose postgres up; makes and drops a throwaway database,
                              # and regenerates src/lib/server/db-types.ts from it: commit it with the migration

cd import && uv run pytest     # also needs the Compose postgres up
```

In a git worktree (no `.env`), pytest falls back to `.env.example`'s `DATABASE_URL`; `pnpm test` needs it in the environment: `DATABASE_URL=postgres://iceskatesong:iceskatesong@localhost:5432/iceskatesong pnpm test`.

The Admin panel is `/admin`: "Import now", the Import status and its problems, and a warning when the YouTube cache has rows older than 25 days. `IMPORT_CONTACT_EMAIL` must be set in `.env` for an Import to run; without `YOUTUBE_API_KEY` it skips the YouTube fetch. Every `/admin` request needs a Cloudflare Access JWT (`CF_ACCESS_TEAM_DOMAIN` and `CF_ACCESS_AUD` in `.env`), so the Compose `web` answers 403 on a dev machine. Locally, run `ADMIN_DEV_BYPASS=true pnpm dev` in `web/` and open `http://localhost:5173/admin`, or start an Import by hand:

```sh
docker compose exec postgres psql -U iceskatesong -c "insert into imports default values"
```

Check the ARM64 build: `docker buildx build --platform linux/arm64 web` (same for `db`, `import` and `backup`).

## On the box

`.env` sets `COMPOSE_PROFILES=prod`, which adds `backup` (nightly `pg_dump` to R2 at 03:00 UTC, 30-day retention, then a Healthchecks ping) and `cloudflared` (the Tunnel; its public hostname points at `http://web:3000`). Logs: `docker compose logs <service>`, rotated at 3 × 10 MB.

```sh
scripts/deploy.sh                              # git pull --ff-only && docker compose up -d --build
docker compose run --rm backup backup.sh       # one backup now
```

Restore (the setup drill on a laptop, or a move to a new host). Needs the `R2_*` values in `.env` and a Postgres with no `pgdata` volume yet, before `migrate` has run:

```sh
scripts/restore.sh                             # newest dump; or scripts/restore.sh iceskatesong-<date>.sql.gz
docker compose up -d                           # migrate then upgrades the restored schema to head
```

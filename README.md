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
docker compose up --build     # postgres → migrate → web on http://localhost:8080, import idles

cd web && pnpm install
pnpm test                     # needs the Compose postgres up; makes and drops a throwaway database
pnpm db:types                 # regenerate Kysely types after a migration

cd import && uv run pytest
```

Check the ARM64 build: `docker buildx build --platform linux/arm64 web` (same for `db` and `import`).

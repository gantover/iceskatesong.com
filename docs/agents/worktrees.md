# Parallel tickets in worktrees

- **Environment**: a worktree runs its tests on `.env.example` defaults (README, "Running it", has the `pnpm test` line). The main checkout's `.env` holds the box's secrets and stays in the main checkout.
- **`/implement`** is human-invoked only: paste its steps into a worktree agent's prompt.
- **Merging**: tickets touching `import/` (`fetch.py`, `main.py`) conflict with each other. Cherry-pick each onto main (history is linear), then run one `/code-review` from the old main tip.
- **Migrations**: parallel tickets each take the next number. At merge, renumber the later cherry-pick (`revision` and `down_revision`), then run `pnpm test` on main and commit the regenerated `db-types.ts`.

## Checks that caught real bugs (#36, #37)

- **Timing criteria**: the dev database is empty until the first production Import (#41). Measure in the worktree on a throwaway database seeded at corpus scale (~48k Programs, ~15k Pieces), `vacuum analyze` before timing (unflushed GIN pending lists skew plans), and report it as a seeded proxy. Include a query that matches thousands of rows, not only a selective one.
- **Restore tests compare whole tables.** Never filter out the rows the criterion is about.
- **Origin-precedence fixtures mix origins**: put a higher-origin claim on an unrelated Program too. A SQL fragment embedded in other queries (like `topClaim`) uses an alias no caller uses.
- **Wikipedia attribution follows `article_title` and `revision`**, never the claim's origin: a `corrections` claim can carry Wikipedia's text.

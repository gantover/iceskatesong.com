# Parallel tickets in worktrees

- **Environment**: a worktree runs its tests on `.env.example` defaults (README, "Running it", has the `pnpm test` line). The main checkout's `.env` holds the box's secrets and stays in the main checkout.
- **`/implement`** is human-invoked only: paste its steps into a worktree agent's prompt.
- **Merging**: tickets touching `import/` (`fetch.py`, `main.py`) conflict with each other. Cherry-pick each onto main (history is linear), then run one `/code-review` from the old main tip.

## Agent skills

### Issue tracker

Issues live in GitHub Issues on `gantover/iceskatesong.com` (via the `gh` CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Worktrees

Parallel tickets in git worktrees: environment, `/implement`, merging. See `docs/agents/worktrees.md`.

## Tool output

- Search specific paths and symbols before reading files; read relevant sections and reuse unchanged context.
- Cap routine tool output at about 2,000 tokens per call. Expand targeted output when correctness requires it.
- Prefer RTK for supported shell commands when available; call it explicitly if hooks are inactive. Otherwise use native quiet flags and bounded output.
- Keep successful checks to a result summary. For failures, retrieve the relevant errors and context while preserving exit status.
- Use unfiltered output when exact source, diffs or diagnostics matter; expand truncated results before drawing conclusions that depend on missing content.
- Give reviewers the task diff and necessary context; keep follow-up reviews focused on changed findings.

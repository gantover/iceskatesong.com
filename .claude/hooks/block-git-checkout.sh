#!/bin/bash
# Blocks `git checkout` (it can detach HEAD with no error) and `git switch --detach`.
# Branch creation (`checkout -b/-B/--orphan`) and plain `git switch <branch>` pass.
# shortcut: matches anywhere in the command, so a commit message quoting "git checkout x" is blocked too; reword it.

COMMAND=$(jq -r '.tool_input.command // empty')
GIT='(^|[^[:alnum:]_.-])git([[:space:]]+-[Cc][[:space:]]+[^[:space:]]+|[[:space:]]+--[[:alnum:]-]+(=[^[:space:]]+)?)*[[:space:]]+'

if echo "$COMMAND" | grep -qE "${GIT}checkout\b" && ! echo "$COMMAND" | grep -qE "${GIT}checkout[[:space:]]+(-b|-B|--orphan)\b" \
  || echo "$COMMAND" | grep -qE "${GIT}switch\b.*([[:space:]]--detach\b|[[:space:]]-d\b)"; then
  echo "BLOCKED: '$COMMAND'. Read another branch with \`git show <ref>:<path>\`, restore a file with \`git restore <path>\`, change branch with \`git switch <branch>\`." >&2
  exit 2
fi

exit 0

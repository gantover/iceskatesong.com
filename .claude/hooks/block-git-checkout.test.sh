#!/bin/bash
# Run: .claude/hooks/block-git-checkout.test.sh
hook="$(dirname "$0")/block-git-checkout.sh"; fail=0
t() { printf '{"tool_input":{"command":%s}}' "$(jq -Rn --arg c "$2" '$c')" | "$hook" 2>/dev/null; r=$?
  [ "$r" = "$1" ] || { echo "FAIL got $r want $1: $2"; fail=1; }; }
t 2 'git checkout origin/prototype/music-normaliser --'
t 2 '/usr/bin/git -C /tmp/wt checkout main'
t 2 'rtk git checkout -- PRD.md'
t 2 'git -c core.pager=cat checkout x'
t 2 'git switch --detach origin/x'
t 0 'git checkout -b feature'
t 0 'git show origin/prototype/x:PRD.md'
t 0 'git commit -m "CI: actions on Node 24 (checkout v7)"'
t 0 'git switch main'
t 0 'git switch -c new-branch'
[ $fail = 0 ] && echo ok; exit $fail

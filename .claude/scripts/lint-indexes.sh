#!/bin/bash
# Index sync — runs Claude headless with the /lint-indexes skill against
# the manual side of the Obsidian vault (~/obsidian-vaul/), keeping every
# folder's index.md in step with the actual on-disk listing. The Auto-Wiki
# subtree is skipped by the skill itself (it has its own ingest-and-weave
# loop). The skill's --cron flag tells it to treat this scheduled invocation
# as the owner's standing authorization, bypassing the interactive
# cross-vault confirmation it would otherwise require.
#
# Cron: 0 */6 * * * (every 6 hours, on the hour).

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
: "${HOME:=$(eval echo "~$(whoami)")}"

export PATH="$HOME/.bun/bin:$HOME/.local/bin:/opt/homebrew/bin:/home/linuxbrew/.linuxbrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

ENV_FILE="$REPO_ROOT/.claude/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    . "$ENV_FILE"
    set +a
fi
export GINARR_VAULT_ROOT="${GINARR_VAULT_ROOT:-$HOME/obsidian-vaul/Auto-Wiki}"

VAULT="${GINARR_MAIN_VAULT:-$HOME/obsidian-vaul}"
LOG="$REPO_ROOT/.claude/scripts/logs/lint-indexes.log"
mkdir -p "$(dirname "$LOG")"

echo "=== $(date -u) ===" >> "$LOG"
cd "$REPO_ROOT"
claude -p "/lint-indexes $VAULT --apply --cron" \
  --allowedTools 'Bash' 'Read' 'Write' 'Edit' 'Glob' \
  --permission-mode acceptEdits \
  >> "$LOG" 2>&1
echo "exit: $?" >> "$LOG"

#!/bin/bash
# Entity weaver — runs Claude headless with the /ingest-and-weave skill.
# Cron: 25 0 * * * (00:25 UTC, ten minutes after summarize-day. The skill
# is idempotent and self-aborts when the upstream summary is missing, so
# this independent cron is safe even on days when summarize-day failed.)

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

LOG="$REPO_ROOT/.claude/scripts/logs/ingest-and-weave.log"
mkdir -p "$(dirname "$LOG")"

echo "=== $(date -u) ===" >> "$LOG"
cd "$REPO_ROOT"
claude -p "/ingest-and-weave" \
  --allowedTools 'Bash' 'Read' 'Write' 'Edit' 'Glob' \
  --permission-mode acceptEdits \
  >> "$LOG" 2>&1
echo "exit: $?" >> "$LOG"

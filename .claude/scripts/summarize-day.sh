#!/bin/bash
# Daily summary roll-up — runs Claude headless with /summarize-day skill.
# Cron: 15 0 * * * (00:15 UTC, processes the previous UTC day plus any backlog).

# Self-locate so the script works from any clone path (Linux, macOS).
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# Cron on minimal configs may not set HOME — fall back to the passwd entry.
: "${HOME:=$(eval echo "~$(whoami)")}"

export PATH="$HOME/.bun/bin:$HOME/.local/bin:/opt/homebrew/bin:/home/linuxbrew/.linuxbrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

ENV_FILE="$REPO_ROOT/.claude/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    . "$ENV_FILE"
    set +a
fi
export GINARR_VAULT_ROOT="${GINARR_VAULT_ROOT:-$HOME/obsidian-vaul/Auto-Wiki}"

LOG="$REPO_ROOT/.claude/scripts/logs/summarize-day.log"
mkdir -p "$(dirname "$LOG")"

echo "=== $(date -u) ===" >> "$LOG"
cd "$REPO_ROOT"
claude -p "/summarize-day" \
  --allowedTools 'Bash' 'Read' 'Write' 'Glob' \
  --permission-mode acceptEdits \
  >> "$LOG" 2>&1
echo "exit: $?" >> "$LOG"

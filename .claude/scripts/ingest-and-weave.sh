#!/bin/bash
# Entity weaver — runs Claude headless with the /ingest-and-weave skill.
# Cron: 25 0 * * * (00:25 UTC, ten minutes after summarize-day. The skill
# is idempotent and self-aborts when the upstream summary is missing, so
# this independent cron is safe even on days when summarize-day failed.)

export HOME=/home/krokobot
export PATH="$HOME/.bun/bin:$HOME/.local/bin:/home/linuxbrew/.linuxbrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export GINARR_VAULT_ROOT="${GINARR_VAULT_ROOT:-$HOME/obsidian-vaul/Auto-Wiki}"

LOG="$HOME/Ginarr/.claude/scripts/logs/ingest-and-weave.log"
mkdir -p "$(dirname "$LOG")"

echo "=== $(date -u) ===" >> "$LOG"
cd "$HOME/Ginarr"
claude -p "/ingest-and-weave" \
  --allowedTools 'Bash' 'Read' 'Write' 'Edit' 'Glob' \
  --permission-mode acceptEdits \
  >> "$LOG" 2>&1
echo "exit: $?" >> "$LOG"

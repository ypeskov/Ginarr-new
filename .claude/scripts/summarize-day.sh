#!/bin/bash
# Daily summary roll-up — runs Claude headless with /summarize-day skill.
# Cron: 15 0 * * * (00:15 UTC, processes the previous UTC day plus any backlog).

export HOME=/home/krokobot
export PATH="$HOME/.bun/bin:$HOME/.local/bin:/home/linuxbrew/.linuxbrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export GINARR_VAULT_ROOT="${GINARR_VAULT_ROOT:-$HOME/obsidian-vaul/Auto-Wiki}"

LOG="$HOME/Ginarr/.claude/scripts/logs/summarize-day.log"
mkdir -p "$(dirname "$LOG")"

echo "=== $(date -u) ===" >> "$LOG"
cd "$HOME/Ginarr"
claude -p "/summarize-day" \
  --allowedTools 'Bash' 'Read' 'Write' 'Glob' \
  --permission-mode acceptEdits \
  >> "$LOG" 2>&1
echo "exit: $?" >> "$LOG"

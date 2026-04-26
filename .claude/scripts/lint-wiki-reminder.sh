#!/bin/bash
# Weekly nudge to run /lint-wiki manually. Does NOT run the skill itself —
# auto-running lint-wiki would either flood wiki/_health/ with redundant
# reports or require auto-resolution, neither of which is desired.
# Cron: 0 9 * * 0 (Sunday 09:00 UTC ~ midday Sofia).

export HOME=/home/krokobot
export PATH="$HOME/.bun/bin:$HOME/.local/bin:/home/linuxbrew/.linuxbrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export GINARR_VAULT_ROOT="${GINARR_VAULT_ROOT:-$HOME/obsidian-vaul/Auto-Wiki}"

LOG="$HOME/Ginarr/.claude/scripts/logs/lint-wiki-reminder.log"
mkdir -p "$(dirname "$LOG")"

echo "=== $(date -u) ===" >> "$LOG"
cd "$HOME/Ginarr"
claude -p "Send the owner a one-line Telegram reminder via the Telegram channel: 'Время прогнать /lint-wiki - еженедельная проверка вики'. Use the Telegram channel's reply tool to deliver to the configured chat. No other action. No reaction needed." \
  --allowedTools 'mcp__plugin_telegram_telegram__reply' \
  --permission-mode acceptEdits \
  >> "$LOG" 2>&1
echo "exit: $?" >> "$LOG"

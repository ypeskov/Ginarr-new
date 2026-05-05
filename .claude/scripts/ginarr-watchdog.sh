#!/bin/bash
# Watchdog — keeps the Ginarr claude tmux session alive and its Telegram plugin healthy.
# Identifies *its own* bun process by TELEGRAM_STATE_DIR in /proc/<pid>/environ, so it
# cannot be confused with OpenClaw's bun when both bots run in parallel.
# Cron: * * * * * (every minute)

export HOME=/home/krokobot
export PATH="$HOME/.bun/bin:$HOME/.local/bin:/home/linuxbrew/.linuxbrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

SESSION="ginarr"
STATE_DIR="$HOME/Ginarr/.claude/channels/telegram"
SCRIPT_DIR="$HOME/Ginarr/.claude/scripts"
LOG="$SCRIPT_DIR/logs/watchdog.log"
DIAG_LOG="$SCRIPT_DIR/logs/watchdog-diag.log"
MCP_STATE="$SCRIPT_DIR/logs/mcp-fail-state"
mkdir -p "$(dirname "$LOG")"

# 1. Ensure tmux session exists
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "$(date -u) — $SESSION dead, restarting" >> "$LOG"
    tmux new-session -d -s "$SESSION" "$SCRIPT_DIR/ginarr-bot.sh"
    echo "$(date -u) — $SESSION created" >> "$LOG"
    rm -f "$MCP_STATE"
    exit 0
fi

# 1b. Also nanny the obsidian-sync session. Ginarr is the primary consumer of
# the vault (Auto-Wiki) so sync lives here, not in any sibling project.
if ! tmux has-session -t obsidian-sync 2>/dev/null; then
    echo "$(date -u) — obsidian-sync dead, restarting" >> "$LOG"
    tmux new-session -d -s obsidian-sync "$SCRIPT_DIR/obsidian-sync.sh"
    echo "$(date -u) — obsidian-sync created" >> "$LOG"
fi

# 2. Find *our* bun process (the one whose env points at our STATE_DIR)
BUN_PID=""
for p in $(pgrep -f "bun server.ts" 2>/dev/null); do
    if [ -r "/proc/$p/environ" ] && \
       tr '\0' '\n' < "/proc/$p/environ" 2>/dev/null | grep -qx "TELEGRAM_STATE_DIR=$STATE_DIR"; then
        BUN_PID=$p
        break
    fi
done

BUN_ALIVE="no"
[ -n "$BUN_PID" ] && BUN_ALIVE="yes(pid=$BUN_PID)"

# 3. Check Telegram API reachability with our token
BOT_TOKEN=$(grep -E '^TELEGRAM_BOT_TOKEN=' "$STATE_DIR/.env" 2>/dev/null | cut -d= -f2-)
API_OK="unknown"
if [ -n "$BOT_TOKEN" ]; then
    if curl -s --max-time 5 "https://api.telegram.org/bot${BOT_TOKEN}/getMe" | grep -q '"ok":true'; then
        API_OK="yes"
    else
        API_OK="no"
    fi
fi

# 4. Check tmux footer for a visible MCP-failure indicator
FOOTER=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null | tail -3)
MCP_FAIL_VISIBLE="no"
if echo "$FOOTER" | grep -qE "[0-9]+ MCP server[s]? failed"; then
    MCP_FAIL_VISIBLE="yes"
fi

# Diagnostic snapshot (overwritten each run)
{
    echo "$(date -u) bun=$BUN_ALIVE api=$API_OK mcp_fail_visible=$MCP_FAIL_VISIBLE"
    echo "  footer: $(echo "$FOOTER" | tr '\n' '|' | cut -c1-300)"
} > "$DIAG_LOG"

# 5. Decision logic — accumulate failures, restart after 3 minutes
PLUGIN_DEAD="no"
REASON=""
if [ "$BUN_ALIVE" = "no" ]; then
    PLUGIN_DEAD="yes"
    REASON="bun process gone"
elif [ "$MCP_FAIL_VISIBLE" = "yes" ]; then
    PLUGIN_DEAD="yes"
    REASON="MCP fail visible in footer"
fi

if [ "$PLUGIN_DEAD" = "yes" ]; then
    if [ -f "$MCP_STATE" ]; then
        FAIL_COUNT=$(cat "$MCP_STATE")
        FAIL_COUNT=$((FAIL_COUNT + 1))
    else
        FAIL_COUNT=1
    fi
    echo "$FAIL_COUNT" > "$MCP_STATE"
    echo "$(date -u) — plugin dead ($REASON, $FAIL_COUNT/3)" >> "$LOG"

    if [ "$FAIL_COUNT" -ge 3 ]; then
        echo "$(date -u) — plugin dead for 3+ min, restarting $SESSION session" >> "$LOG"
        tmux kill-session -t "$SESSION" 2>/dev/null
        rm -f "$MCP_STATE"
    fi
else
    if [ -f "$MCP_STATE" ]; then
        echo "$(date -u) — plugin recovered, clearing fail state" >> "$LOG"
        rm -f "$MCP_STATE"
    fi
fi

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

# Cross-bot liveness channel (see docs/scripts/ginarr-watchdog.md "Shared heartbeat").
SHARED_SELF="$HOME/shared/ginarr"
SHARED_PEER="$HOME/shared/openclaw"
HEARTBEAT_FILE="$SHARED_SELF/last-seen.txt"
ALERT_MARKER="$SHARED_SELF/alerted-about-openclaw.txt"
PEER_NAME="openclaw"
OWNER_CHAT_ID="353065630"
mkdir -p "$SHARED_SELF"

write_heartbeat() {
    local tmux_alive="$1" obs_alive="$2" note="$3"
    {
        echo "ts_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo "tmux_session=$SESSION"
        echo "tmux_alive=$tmux_alive"
        echo "obsidian_sync_alive=$obs_alive"
        echo "note=$note"
    } > "$HEARTBEAT_FILE.tmp" && mv "$HEARTBEAT_FILE.tmp" "$HEARTBEAT_FILE"
}

# 1. Ensure tmux session exists
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "$(date -u) — $SESSION dead, restarting" >> "$LOG"
    tmux new-session -d -s "$SESSION" "$SCRIPT_DIR/ginarr-bot.sh"
    echo "$(date -u) — $SESSION created" >> "$LOG"
    rm -f "$MCP_STATE"
    OBS_ALIVE_FAST=0
    tmux has-session -t obsidian-sync 2>/dev/null && OBS_ALIVE_FAST=1
    write_heartbeat 0 "$OBS_ALIVE_FAST" "restarting_ginarr"
    exit 0
fi

# 1b. Also nanny the obsidian-sync session. Ginarr is the primary consumer of
# the vault (Auto-Wiki) so sync lives here, not in any sibling project.
OBS_ALIVE=1
if ! tmux has-session -t obsidian-sync 2>/dev/null; then
    echo "$(date -u) — obsidian-sync dead, restarting" >> "$LOG"
    tmux new-session -d -s obsidian-sync "$SCRIPT_DIR/obsidian-sync.sh"
    echo "$(date -u) — obsidian-sync created" >> "$LOG"
    OBS_ALIVE=0
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

# 5. Check remote-control bridge to claude.ai. The session JSON at
# ~/.claude/sessions/<pid>.json carries "bridgeSessionId":"session_..." while
# the bridge is connected, and "bridgeSessionId":null after it drops. The CLI
# does not auto-reconnect, so a null here means the web/mobile remote is dead.
CLAUDE_PID=""
for p in $(pgrep -x claude 2>/dev/null); do
    if [ -r "/proc/$p/environ" ] && \
       tr '\0' '\n' < "/proc/$p/environ" 2>/dev/null | grep -qx "TELEGRAM_STATE_DIR=$STATE_DIR"; then
        CLAUDE_PID=$p
        break
    fi
done

BRIDGE_STATE="unknown"
if [ -n "$CLAUDE_PID" ]; then
    SESSION_JSON="$HOME/.claude/sessions/${CLAUDE_PID}.json"
    if [ -r "$SESSION_JSON" ]; then
        if grep -q '"bridgeSessionId":"session_' "$SESSION_JSON"; then
            BRIDGE_STATE="up"
        elif grep -q '"bridgeSessionId":null' "$SESSION_JSON"; then
            BRIDGE_STATE="down"
        fi
    fi
fi

# Diagnostic snapshot (overwritten each run)
{
    echo "$(date -u) bun=$BUN_ALIVE api=$API_OK mcp_fail_visible=$MCP_FAIL_VISIBLE bridge=$BRIDGE_STATE claude_pid=${CLAUDE_PID:-none}"
    echo "  footer: $(echo "$FOOTER" | tr '\n' '|' | cut -c1-300)"
} > "$DIAG_LOG"

# 6. Decision logic — accumulate failures, restart after 3 minutes
PLUGIN_DEAD="no"
REASON=""
if [ "$BUN_ALIVE" = "no" ]; then
    PLUGIN_DEAD="yes"
    REASON="bun process gone"
elif [ "$MCP_FAIL_VISIBLE" = "yes" ]; then
    PLUGIN_DEAD="yes"
    REASON="MCP fail visible in footer"
elif [ "$BRIDGE_STATE" = "down" ]; then
    PLUGIN_DEAD="yes"
    REASON="remote-control bridge down"
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

# 7. Heartbeat — publish liveness for the peer bot to read.
NOTE=""
if pgrep -f "$SCRIPT_DIR/ingest-and-weave.sh" >/dev/null 2>&1; then
    NOTE="ingest_running"
fi
write_heartbeat 1 "$OBS_ALIVE" "$NOTE"

# 8. Peer-down check — alert owner via Telegram if OpenClaw has been silent
# for > 10 minutes. Dedup via $ALERT_MARKER (no repeat within 1 hour).
# Guard: if peer file never existed at all, do not alert — channel is still
# bootstrapping. Only alert on a previously-seen peer going silent.
PEER_FILE="$SHARED_PEER/last-seen.txt"
if [ -f "$PEER_FILE" ]; then
    PEER_TS=$(grep -E '^ts_utc=' "$PEER_FILE" | head -1 | cut -d= -f2-)
    if [ -n "$PEER_TS" ]; then
        PEER_EPOCH=$(date -d "$PEER_TS" +%s 2>/dev/null || echo 0)
        NOW_EPOCH=$(date -u +%s)
        AGE=$(( NOW_EPOCH - PEER_EPOCH ))
        if [ "$AGE" -gt 600 ]; then
            SEND=1
            if [ -f "$ALERT_MARKER" ]; then
                MARKER_EPOCH=$(stat -c %Y "$ALERT_MARKER" 2>/dev/null || echo 0)
                MARKER_AGE=$(( NOW_EPOCH - MARKER_EPOCH ))
                [ "$MARKER_AGE" -lt 3600 ] && SEND=0
            fi
            if [ "$SEND" = "1" ] && [ -n "$BOT_TOKEN" ]; then
                AGE_MIN=$(( AGE / 60 ))
                MSG="[ginarr] peer $PEER_NAME down for ${AGE_MIN}m. Last seen $PEER_TS."
                curl -s --max-time 5 \
                    -d "chat_id=$OWNER_CHAT_ID" \
                    --data-urlencode "text=$MSG" \
                    "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" > /dev/null
                touch "$ALERT_MARKER"
                echo "$(date -u) — alerted owner: $PEER_NAME down ${AGE_MIN}m" >> "$LOG"
            fi
        elif [ -f "$ALERT_MARKER" ]; then
            rm -f "$ALERT_MARKER"
            echo "$(date -u) — $PEER_NAME recovered, cleared alert marker" >> "$LOG"
        fi
    fi
fi

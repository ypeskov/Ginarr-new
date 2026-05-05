#!/bin/bash
# Obsidian vault sync daemon — runs `ob sync` in a loop
# Auto-restarted by ginarr-watchdog.sh; never invoked directly.

export HOME=/home/krokobot
# obsidian-headless (`ob`) needs Node >= 22 (nvm). Both bun and the nvm node 22
# dir come before /usr/bin so the cli's `#!/usr/bin/env node` shebang resolves
# to Node 22, not the system /usr/bin/node 20 (NODE_MODULE_VERSION mismatch on
# the native better-sqlite3 addon).
export PATH="$HOME/.bun/bin:$HOME/.nvm/versions/node/v22.22.0/bin:$HOME/.local/bin:/home/linuxbrew/.linuxbrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

VAULT_PATH="$HOME/obsidian-vaul"
SYNC_LOG="$HOME/Ginarr/.claude/scripts/logs/obsidian-sync-last.log"
mkdir -p "$(dirname "$SYNC_LOG")"

while true; do
    # `ob sync` has no connect-timeout — if a WebSocket SYN goes into a black hole,
    # the inner Promise hangs forever and the whole loop wedges (observed: 30+ hours
    # stuck on "Connecting..." after a network blip on 2026-05-04). `timeout --signal=KILL`
    # is the safety net: SIGTERM is caught by `ob` but doesn't actually exit, so we go
    # straight to KILL. 180 s is ~6× the normal iteration time (~30 s).
    timeout --signal=KILL 180 ob sync --path "$VAULT_PATH" > "$SYNC_LOG" 2>&1
    RC=$?
    SUMMARY=$(tail -3 "$SYNC_LOG" | tr '\n' ' | ')
    echo "[$(date -u)] sync exit=$RC | $SUMMARY"
    sleep 30
done

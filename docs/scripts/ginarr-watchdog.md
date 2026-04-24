# ginarr-watchdog.sh

Per-minute cron job that keeps the `ginarr` tmux session alive and the Telegram plugin healthy.

## Cron

```cron
* * * * * /home/krokobot/Ginarr/.claude/scripts/ginarr-watchdog.sh
```

## Checks each tick

1. **Session exists.** `tmux has-session -t ginarr` — if absent, recreate via `ginarr-bot.sh`.
2. **Plugin process alive.** Walks `pgrep -f "bun server.ts"` and keeps the one whose `/proc/<pid>/environ` contains `TELEGRAM_STATE_DIR=$STATE_DIR`. This isolates "our" bun from any sibling bots' bun on the same machine.
3. **Telegram API reachable.** `curl .../getMe` with the bot token. Recorded in the diagnostic log but does not drive restarts directly.
4. **Footer signal.** Captures the tmux pane tail and looks for `"N MCP server(s) failed"` — the visible marker that the plugin crashed.

## Restart policy

A failure (bun gone OR MCP-failure string in the footer) increments a counter in `logs/mcp-fail-state`. After **3 consecutive failures** (three cron ticks in a row), the watchdog kills the tmux session; the next tick recreates it. Recovery clears the counter.

## Logs

- `.claude/scripts/logs/watchdog.log` — human-readable history of decisions.
- `.claude/scripts/logs/watchdog-diag.log` — single-line diagnostic snapshot, overwritten every tick.

Both paths are gitignored.

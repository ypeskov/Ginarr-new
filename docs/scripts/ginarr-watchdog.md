# ginarr-watchdog.sh

Per-minute cron job that keeps the `ginarr` and `obsidian-sync` tmux sessions alive and the Telegram plugin healthy.

## Cron

```cron
* * * * * /home/krokobot/Ginarr/.claude/scripts/ginarr-watchdog.sh
```

## Checks each tick

1. **`ginarr` session exists.** `tmux has-session -t ginarr` — if absent, recreate via `ginarr-bot.sh` and exit early (next tick will check the rest).
2. **`obsidian-sync` session exists.** `tmux has-session -t obsidian-sync` — if absent, recreate via [`obsidian-sync.sh`](obsidian-sync.md). Sync lives here because Ginarr is the primary consumer of the vault.
3. **Plugin process alive.** Walks `pgrep -f "bun server.ts"` and keeps the one whose `/proc/<pid>/environ` contains `TELEGRAM_STATE_DIR=$STATE_DIR`. This isolates "our" bun from any sibling bots' bun on the same machine.
4. **Telegram API reachable.** `curl .../getMe` with the bot token. Recorded in the diagnostic log but does not drive restarts directly.
5. **Footer signal.** Captures the tmux pane tail and looks for `"N MCP server(s) failed"` — the visible marker that the plugin crashed.
6. **Remote-control bridge.** Identifies "our" `claude` PID by the same `TELEGRAM_STATE_DIR` env trick, then reads `~/.claude/sessions/<pid>.json` and looks at `bridgeSessionId`. A `"session_..."` value means the bridge to claude.ai is up; `null` means it dropped and the CLI did not reconnect — web and mobile remote are dead until restart.

## Restart policy

A failure (bun gone OR MCP-failure string in the footer OR remote-control bridge down) increments a counter in `logs/mcp-fail-state`. After **3 consecutive failures** (three cron ticks in a row), the watchdog kills the `ginarr` tmux session; the next tick recreates it via `ginarr-bot.sh`, and `claude --continue` resumes the same conversation with a fresh bridge. Recovery clears the counter. The `obsidian-sync` session has no plugin-health logic — it's just respawned if the tmux session is gone.

## Shared heartbeat (cross-bot liveness)

Each tick the watchdog also publishes Ginarr's liveness to `~/shared/ginarr/last-seen.txt` so the sibling bot (OpenClaw / Kroko James) can detect a silent peer and alert the owner. Format is plain `key=value` lines, written atomically via `*.tmp` + `mv`:

```
ts_utc=2026-05-12T06:03:24Z
tmux_session=ginarr
tmux_alive=1
obsidian_sync_alive=1
note=
```

The `note=` field is a controlled enum so the peer can react contextually. Currently emitted values:

- *(empty)* — normal operation.
- `ingest_running` — `ingest-and-weave.sh` is running; vault writes may race a peer's read.
- `restarting_ginarr` — `ginarr` tmux session was just respawned this tick; the next tick will reflect the recovered state.

Reserved for future emission (declared in the cross-bot contract but not yet detected): `consolidation_run`, `obsidian_sync_lag=N`.

### Peer-down alert

After publishing its own heartbeat, the watchdog reads `~/shared/openclaw/last-seen.txt`. If the peer's `ts_utc` is older than **10 minutes**, it sends one Telegram DM to the owner via Ginarr's own bot token:

```
[ginarr] peer openclaw down for Xm. Last seen <ts>.
```

A marker file at `~/shared/ginarr/alerted-about-openclaw.txt` suppresses repeats within 1 hour. The marker is cleared the moment the peer's heartbeat freshens. If the peer file has **never existed**, no alert is sent — the channel is still bootstrapping and a "never seen" state is not the same as a "previously alive, now silent" state.

The owner's chat_id is hardcoded as the single entry from `.claude/channels/telegram/access.json`'s `allowFrom` list — the bot only ever talks to its one owner.

## Logs

- `.claude/scripts/logs/watchdog.log` — human-readable history of decisions (now also records peer-down alerts and recoveries).
- `.claude/scripts/logs/watchdog-diag.log` — single-line diagnostic snapshot, overwritten every tick.

Both paths are gitignored. `~/shared/` lives outside the repo and is not version-controlled.

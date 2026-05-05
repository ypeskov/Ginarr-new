# obsidian-sync.sh

Daemon that keeps `$GINARR_VAULT_ROOT` in sync with Obsidian's hosted Sync service via `obsidian-headless`. Runs as a long-lived `while true` loop inside the `obsidian-sync` tmux session, supervised by [ginarr-watchdog.sh](ginarr-watchdog.md).

## Why it lives in this repo

Ginarr's Auto-Wiki is the primary consumer of the vault — daily summaries, entity pages, capture flow all depend on the vault being kept up-to-date across devices. Krokobot (the OpenClaw-side bot) does not write to the vault. From 2026-04-24 to 2026-05-05 the script lived in `~/OpenClaw/.claude/scripts/`; this was historical inertia, not architecture, and was corrected in commit `bfa3ccf`'s follow-up.

## How it runs

Not invoked directly. The watchdog launches it via:

```bash
tmux new-session -d -s obsidian-sync ~/Ginarr/.claude/scripts/obsidian-sync.sh
```

Loop body:

```bash
while true; do
    timeout --signal=KILL 180 ob sync --path "$VAULT_PATH" > "$SYNC_LOG" 2>&1
    RC=$?
    SUMMARY=$(tail -3 "$SYNC_LOG" | tr '\n' ' | ')
    echo "[$(date -u)] sync exit=$RC | $SUMMARY"
    sleep 30
done
```

Healthy iterations finish in ~30 s. The `timeout --signal=KILL 180` is a safety net against `obsidian-headless`'s missing connect-timeout — see [configuration.md § Hang failure mode](../configuration.md#hang-failure-mode-now-bounded-by-wrapper-side-timeout) for the full root cause and recovery procedure.

## PATH note

The script prepends `$HOME/.bun/bin:$HOME/.nvm/versions/node/v22.22.0/bin` to `PATH`. The `ob` cli's shebang is `#!/usr/bin/env node`, so without this the system `/usr/bin/node` (20.x) gets picked up and `better-sqlite3` fails with `NODE_MODULE_VERSION` mismatch.

## Logs

- `~/Ginarr/.claude/scripts/logs/obsidian-sync-last.log` — output of the **current** iteration, overwritten on each cycle. Useful for "is it stuck right now?" diagnostics.
- The wrapper's own per-tick exit-code line (`[<date>] sync exit=N | <summary>`) goes to the tmux pane scrollback — `tmux capture-pane -t obsidian-sync -pS -200` to see history.

Both are gitignored.

## See also

- [ginarr-watchdog.md](ginarr-watchdog.md) — supervisor.
- [../configuration.md § Obsidian Sync](../configuration.md#obsidian-sync-current-deployment) — full deployment notes including the three-knob `unsupported` file-types checklist.

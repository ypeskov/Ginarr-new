# ginarr-bot.sh

Entrypoint for the Ginarr Claude Code process. Launched into a tmux session named `ginarr`.

## Behaviour

1. Sets `HOME`, `PATH`, and `TELEGRAM_STATE_DIR` (`…/Ginarr/.claude/channels/telegram` — project-local, so Ginarr can coexist with other bots that have their own state dir and bot token).
2. Sources `.claude/.env` with `set -a`, so any variables defined there (notably `GINARR_VAULT_ROOT`) are exported and inherited by the child Claude Code process and its hooks.
3. `cd` into the project directory.
4. Execs Claude Code with `--continue --channels plugin:telegram@claude-plugins-official --remote-control`.

## Why `.env` sourcing lives here

All scripts invoked from the bot (write-path hooks in particular) need `GINARR_VAULT_ROOT`. Loading `.env` once at process start centralises the config; no wrapper or hook has to read the file itself.

## Invocation

Not run by the user directly. Normally invoked by `ginarr-watchdog.sh`:

```bash
tmux new-session -d -s ginarr "$SCRIPT_DIR/ginarr-bot.sh"
```

For a manual restart without waiting for the watchdog (from any terminal):

```bash
tmux kill-session -t ginarr 2>/dev/null
tmux new-session -d -s ginarr ~/Ginarr/.claude/scripts/ginarr-bot.sh
```

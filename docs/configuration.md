# Configuration

Environment variables and config files that drive the bot's runtime behaviour.

## `.claude/.env` — bot environment

Sourced by `.claude/scripts/ginarr-bot.sh` at startup with `set -a`, so every variable defined here is exported and inherited by the Claude Code process and every hook it spawns.

**Gitignored.** A committed template lives at [`.claude/.env.example`](../.claude/.env.example); to bootstrap a new machine, copy it to `.claude/.env` and edit.

### Variables

| Name                | Purpose                                                                       | Required |
|---------------------|-------------------------------------------------------------------------------|----------|
| `GINARR_VAULT_ROOT` | Absolute path to the chat-memory vault (data side: `logs/` + `notes/`).       | Yes      |

If `GINARR_VAULT_ROOT` is unset, `log_event.py` prints a message to stderr and exits 0 — the bot runs, but no events are captured.

## `.claude/channels/telegram/.env` — Telegram plugin config

Managed by the Telegram channel plugin, **not** by this repo. Holds `TELEGRAM_BOT_TOKEN` and similar plugin state. Set via the `/telegram:configure` skill (invoked once from a terminal Claude session, not from the bot itself).

`ginarr-watchdog.sh` reads the token from this file directly to call `getMe` as a liveness probe.

## Bootstrap on a new machine

1. Clone this repo.
2. `cp .claude/.env.example .claude/.env` and set `GINARR_VAULT_ROOT` to your vault path.
3. Make sure the vault exists and contains `logs/` and `notes/` (see [architecture.md](architecture.md)).
4. Run `/telegram:configure` in a terminal Claude session to pair the bot token.
5. Install the watchdog cron line (see [scripts/ginarr-watchdog.md](scripts/ginarr-watchdog.md)).

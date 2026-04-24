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

## Obsidian Sync (current deployment)

The vault at `$GINARR_VAULT_ROOT` is kept in sync with Obsidian's hosted service via the official `ob` CLI (`/home/linuxbrew/.linuxbrew/bin/ob`, v0.0.8). The daemon is **not owned by this repo** — it lives in a sibling project:

- Script: `~/OpenClaw/.claude/scripts/obsidian-sync.sh` (a 30-second `while true` loop running `ob sync`).
- Log: `~/OpenClaw/.claude/scripts/logs/obsidian-sync-last.log` — current tick's output, overwritten each cycle.

On a fresh deployment without OpenClaw there is no sync at all; the vault stays local until something is wired up.

### "Logs/notes don't appear in Obsidian" — three knobs

All three must align. Missing any one makes `logs/**/*.jsonl` invisible on the Mac/iOS client:

1. **Server-side file-types** must include `unsupported`. JSONL doesn't match `image|audio|video|pdf`, so the default config won't upload it. Fix and verify on the Linux host:
   ```
   ob sync-config --path ~/obsidian-vaul \
       --file-types image,audio,video,pdf,unsupported
   ob sync-status --path ~/obsidian-vaul
   ```
2. **Client-side Sync selection.** On the Mac: `Settings → Core plugins → Sync → Selected file types → Unsupported` ON. Sync's file-type filter is per-device.
3. **File-explorer visibility.** On the Mac: `Settings → Files and links → Detect all file extensions` ON. Obsidian otherwise hides non-native extensions in the sidebar even when they exist on disk.

### Useful `ob` subcommands

- `ob sync-status --path <vault>` — current config + sync mode.
- `ob sync-list-local` / `ob sync-list-remote` — enumerate vaults.
- `ob sync-config --help` — full option list (conflict strategy, excluded folders, config categories, device name, sync mode).

## Bootstrap on a new machine

1. Clone this repo.
2. `cp .claude/.env.example .claude/.env` and set `GINARR_VAULT_ROOT` to your vault path.
3. Make sure the vault exists and contains `logs/` and `notes/` (see [architecture.md](architecture.md)).
4. Run `/telegram:configure` in a terminal Claude session to pair the bot token.
5. Install the watchdog cron line (see [scripts/ginarr-watchdog.md](scripts/ginarr-watchdog.md)).

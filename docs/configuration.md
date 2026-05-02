# Configuration

Environment variables and config files that drive the bot's runtime behaviour.

## `.claude/.env` — bot environment

Sourced by `.claude/scripts/ginarr-bot.sh` at startup with `set -a`, so every variable defined here is exported and inherited by the Claude Code process and every hook it spawns.

**Gitignored.** A committed template lives at [`.claude/.env.example`](../.claude/.env.example); to bootstrap a new machine, copy it to `.claude/.env` and edit.

### Variables

| Name                | Purpose                                                                       | Required |
|---------------------|-------------------------------------------------------------------------------|----------|
| `GINARR_VAULT_ROOT` | Absolute path to the Auto-Wiki vault (data side: `logs/` + `wiki/`).       | Yes      |

If `GINARR_VAULT_ROOT` is unset, `log_event.py` prints a message to stderr and exits 0 — the bot runs, but no events are captured.

## `.claude/channels/telegram/.env` — Telegram plugin config

Managed by the Telegram channel plugin, **not** by this repo. Holds `TELEGRAM_BOT_TOKEN` and similar plugin state. Set via the `/telegram:configure` skill (invoked once from a terminal Claude session, not from the bot itself).

`ginarr-watchdog.sh` reads the token from this file directly to call `getMe` as a liveness probe.

## Obsidian Sync (current deployment)

The vault at `$GINARR_VAULT_ROOT` is kept in sync with Obsidian's hosted service via **`obsidian-headless`** (github.com/obsidianmd/obsidian-headless), the official Obsidian-made headless client that ships an `ob` binary. The daemon is **not owned by this repo** — it lives in a sibling project:

- Script: `~/OpenClaw/.claude/scripts/obsidian-sync.sh` (a 30-second `while true` loop running `ob sync`).
- Log: `~/OpenClaw/.claude/scripts/logs/obsidian-sync-last.log` — current tick's output, overwritten each cycle.
- Tmux session: `obsidian-sync` (separate from `ginarr` / `claude` so daemon kills don't take Claude down).
- Auto-restart: `~/OpenClaw/.claude/scripts/claude-watchdog.sh` (cron every minute) ensures the tmux session exists; recreates it if dead. Survives reboots since cron starts before the watchdog re-checks.

### Install

`obsidian-headless` is distributed via npm (not Homebrew, despite a historical install at `/home/linuxbrew/.linuxbrew/bin/ob`). The native module `better-sqlite3` requires **Node ≥ 22** (`NODE_MODULE_VERSION 127`).

```bash
# install via nvm's node 22+ so native modules compile against the right ABI
export PATH="$HOME/.nvm/versions/node/v22.22.0/bin:$PATH"
npm install -g obsidian-headless
```

The binary lands at `~/.nvm/versions/node/v22.22.0/bin/ob`. Auth state survives reinstall (`~/.config/obsidian-headless/`), so re-login is not required if reinstalling on the same machine.

The daemon script `obsidian-sync.sh` prepends `$HOME/.bun/bin:$HOME/.nvm/versions/node/v22.22.0/bin` to `PATH` so the `ob` cli's `#!/usr/bin/env node` shebang resolves to Node 22, not the system `/usr/bin/node` (which is 20.x and triggers `NODE_MODULE_VERSION` mismatch on the native sqlite addon).

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
3. Make sure the vault exists and contains `logs/` and `wiki/` (see [architecture.md](architecture.md)).
4. Run `/telegram:configure` in a terminal Claude session to pair the bot token.
5. Install the cron lines (see the per-script docs for the exact one-liner):
   - Watchdog — every minute, keeps the bot alive: [scripts/ginarr-watchdog.md](scripts/ginarr-watchdog.md).
   - Daily summaries — 00:15 UTC, builds the read-path index: [scripts/summarize-day.md](scripts/summarize-day.md).
   - Entity weaver — 00:25 UTC, weaves entities from each new daily summary into `wiki/entities/`: [scripts/ingest-and-weave.md](scripts/ingest-and-weave.md).
   - Wiki-lint reminder — Sundays 09:00 UTC, sends a Telegram nudge to run `/lint-wiki` manually: [scripts/lint-wiki-reminder.md](scripts/lint-wiki-reminder.md).
   - Index sync — every 6 hours, regenerates auto-managed sections in every `index.md` across the manual vault: [scripts/lint-indexes.md](scripts/lint-indexes.md).

## Cron lines installed by this repo

All cron entries live in the **owner's user crontab** (`crontab -e`), not in `/etc/cron.d/`. Inspect with `crontab -l`:

| When            | Script                                                                       | Purpose                                                       |
|-----------------|------------------------------------------------------------------------------|---------------------------------------------------------------|
| `* * * * *`     | `~/Ginarr/.claude/scripts/ginarr-watchdog.sh`                                | Keep the `ginarr` tmux session and the Telegram plugin alive. |
| `15 0 * * *`    | `~/Ginarr/.claude/scripts/summarize-day.sh`                                  | Daily roll-up of `logs/<date>.jsonl` into `logs/summaries/`.  |
| `25 0 * * *`    | `~/Ginarr/.claude/scripts/ingest-and-weave.sh`                               | Weave entities from the new daily summary into `wiki/entities/`. |
| `0 9 * * 0`     | `~/Ginarr/.claude/scripts/lint-wiki-reminder.sh`                             | Weekly Telegram nudge: time to run `/lint-wiki` manually.     |
| `0 */6 * * *`   | `~/Ginarr/.claude/scripts/lint-indexes.sh`                                   | Sync auto-managed sections in every `index.md` across the manual vault. |

OpenClaw and any other sibling repos may add their own entries (e.g. weather, news, calendar digests); those are not owned by this repo.

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

The vault at `$GINARR_VAULT_ROOT` is kept in sync with Obsidian's hosted service via **`obsidian-headless`** (github.com/obsidianmd/obsidian-headless), the official Obsidian-made headless client that ships an `ob` binary. The daemon lives in this repo because Ginarr's Auto-Wiki is the primary consumer of the vault:

- Script: [`~/Ginarr/.claude/scripts/obsidian-sync.sh`](scripts/obsidian-sync.md) — `while true; do timeout --signal=KILL 180 ob sync; sleep 30; done`.
- Log: `~/Ginarr/.claude/scripts/logs/obsidian-sync-last.log` — current tick's output, overwritten each cycle.
- Tmux session: `obsidian-sync` (separate from `ginarr` so daemon kills don't take the bot down).
- Auto-restart: [`ginarr-watchdog.sh`](scripts/ginarr-watchdog.md) (cron every minute) ensures the tmux session exists; recreates it if dead. Survives reboots since cron starts before the watchdog re-checks.

### Install

`obsidian-headless` is distributed via npm (not Homebrew, despite a historical install at `/home/linuxbrew/.linuxbrew/bin/ob`). The native module `better-sqlite3` requires **Node ≥ 22** (`NODE_MODULE_VERSION 127`).

```bash
# install via nvm's node 22+ so native modules compile against the right ABI
export PATH="$HOME/.nvm/versions/node/v22.22.0/bin:$PATH"
npm install -g obsidian-headless
```

The binary lands at `~/.nvm/versions/node/v22.22.0/bin/ob`. Auth state survives reinstall (`~/.config/obsidian-headless/`), so re-login is not required if reinstalling on the same machine.

The daemon script `obsidian-sync.sh` prepends `$HOME/.bun/bin:$HOME/.nvm/versions/node/v22.22.0/bin` to `PATH` so the `ob` cli's `#!/usr/bin/env node` shebang resolves to Node 22, not the system `/usr/bin/node` (which is 20.x and triggers `NODE_MODULE_VERSION` mismatch on the native sqlite addon).

On a fresh deployment, install `obsidian-headless` first and run `ob login` once to seed the auth token; from there the watchdog handles everything.

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

### Hang failure mode (now bounded by wrapper-side timeout)

**Root cause.** `obsidian-headless` has heartbeat logic (20 s ping interval, 120 s silence → disconnect) but it is installed inside the WebSocket `onopen` callback — it only guards a connection that successfully opened. The initial `connect()` call returns a `new Promise` with **no timeout**. If the WebSocket's TCP SYN gets lost (network blip, dropped RST, NAT state-table eviction), neither `onopen` nor `onclose` fires, the Promise never settles, and `ob sync` blocks on `await e.connect(...)` forever. The wrapper's `while true; do ob sync; sleep 30; done` then blocks on that single hung call — the next iteration never starts, the watchdog only checks tmux session existence, and the daemon stays "alive" while doing nothing. Observed once: 2026-05-04 13:51 UTC → 2026-05-05 19:14 UTC, ~30 hours stuck on `Connecting...` after a network event that left no trace in journalctl.

**Mitigation (in place since 2026-05-05).** `obsidian-sync.sh` wraps each iteration:

```bash
timeout --signal=KILL 180 ob sync --path "$VAULT_PATH" > "$SYNC_LOG" 2>&1
```

Healthy iterations finish in ~30 s, so 180 s is a ~6× margin. If the connect wedges, SIGKILL fires after 3 minutes, the wrapper logs `exit=137`, then `sleep 30` and a fresh iteration runs. The class "stuck for hours" is no longer possible. SIGKILL, not SIGTERM — `ob` catches SIGTERM and prints `Received signal to shut down... Disconnected from server`, but the Node process doesn't actually exit (async handles never finalise).

**Detect.**

```bash
stat -c '%y' ~/Ginarr/.claude/scripts/logs/obsidian-sync-last.log    # should be within ~30 s
tmux capture-pane -t obsidian-sync -pS -200 | grep '^\['               # iteration exit-code timeline
```

Healthy timeline is `sync exit=0` once per ~30 s. A `sync exit=137` is the timeout firing — annoying but bounded.

**Manual recovery (if it ever wedges inside the 3-minute window).**

```bash
kill -9 "$(pgrep -f 'bin/ob sync')"
```

## Bootstrap on a new machine

The repo is path-portable: every script self-locates its own `REPO_ROOT` via `$(dirname "$0")`, and `.claude/settings.json` hooks expand `$CLAUDE_PROJECT_DIR` (set by Claude Code). You can clone anywhere; nothing assumes `~/Ginarr/`. In the per-script docs `<repo>` is a placeholder for the absolute path to your local clone — substitute it when copy-pasting cron lines into your crontab.

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
| `* * * * *`     | `~/Ginarr/.claude/scripts/ginarr-watchdog.sh`                                | Keep the `ginarr` and `obsidian-sync` tmux sessions alive; check Telegram plugin health. |
| `15 0 * * *`    | `~/Ginarr/.claude/scripts/summarize-day.sh`                                  | Daily roll-up of `logs/<date>.jsonl` into `logs/summaries/`.  |
| `25 0 * * *`    | `~/Ginarr/.claude/scripts/ingest-and-weave.sh`                               | Weave entities from the new daily summary into `wiki/entities/`. |
| `0 9 * * 0`     | `~/Ginarr/.claude/scripts/lint-wiki-reminder.sh`                             | Weekly Telegram nudge: time to run `/lint-wiki` manually.     |
| `0 */6 * * *`   | `~/Ginarr/.claude/scripts/lint-indexes.sh`                                   | Sync auto-managed sections in every `index.md` across the manual vault. |

OpenClaw and any other sibling repos may add their own entries (e.g. weather, news, calendar digests); those are not owned by this repo.

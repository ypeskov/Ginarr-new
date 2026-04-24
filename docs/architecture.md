# Architecture

Ginarr is a single-owner, always-on Telegram assistant. Claude Code is the agent runtime; a portable chat-memory vault on the filesystem is the long-term memory.

## Processes

- **`ginarr` tmux session** — the live Claude Code process, launched by `.claude/scripts/ginarr-bot.sh`. Runs with `--continue` so the conversation survives restarts.
- **Telegram plugin** — loaded via `--channels plugin:telegram@claude-plugins-official`. Receives messages from the owner and hands them to Claude Code as prompts.
- **Watchdog** — `.claude/scripts/ginarr-watchdog.sh` is invoked every minute by cron. Verifies the tmux session, the bun plugin subprocess, and the Telegram API; restarts the session after 3 consecutive failures.

## Data / behavior split

The bot repo and the memory vault are **separate** directories with independent lifecycles.

| Path                              | Purpose                                                  | Lifecycle                                                  |
|-----------------------------------|----------------------------------------------------------|------------------------------------------------------------|
| `~/Ginarr/` (this repo)           | Behavior: scripts, hooks, skills, configuration.         | Replaceable. Can migrate to Junie or OpenCode by rewiring. |
| `~/obsidian-vaul/chat-memory/`    | Data: logs, notes. Portable Markdown + JSONL.            | Must survive years and runtime migrations.                 |

`GINARR_VAULT_ROOT` in `.claude/.env` (gitignored) points the bot at its vault. `ginarr-bot.sh` sources this file before exec'ing Claude, so the variable is inherited by all hook processes.

Rationale for the split: data is format-portable, behavior is runtime-specific; keeping them apart avoids accidentally coupling a multi-year memory store to a single agent runtime. See SPEC.v3 §"Vendor neutrality".

## Write-path

Every conversational turn flows through Claude Code hooks into the vault as one JSONL event.

1. Owner sends a Telegram message → plugin delivers it as a prompt to the Claude session.
2. Claude Code fires `UserPromptSubmit` → `log_event.py --event user` writes `{role:"user", content:"…"}` to `$GINARR_VAULT_ROOT/logs/YYYY/MM/YYYY-MM-DD.jsonl`.
3. Assistant composes reply (possibly using tools).
4. Claude Code fires `Stop` at end of turn → `log_event.py --event assistant` writes the turn's outgoing assistant text.
5. Session lifecycle events (`SessionStart`, `SessionEnd`) produce `{role:"system", content:"bot_started"|"bot_stopped"}`.

All content is passed through `redactor.py` (Layer 2 regex + Layer 3 owner denylist) before persistence.

See [hooks.md](hooks.md) for the extraction details and [scripts/log_event.md](scripts/log_event.md) for the implementation.

## What is NOT here yet

- **Consolidation / search / archive tools** — only `redactor.py` has been built from SPEC.v3 §"Portable tools".
- **Skills** — only `create-skill` is installed (copied from OpenClaw for scaffolding). The six project-specific skills (`capture`, `recall`, `review`, `consolidate`, `redact`, `nolog`) are not yet built.
- **Attachment markers** (`[image: …]`, `[file: …]`, `[audio: …]`) — the write-path currently logs prompt text as-is; Telegram-specific attachment handling comes later.

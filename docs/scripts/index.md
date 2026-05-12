# Scripts

Everything in `.claude/scripts/`. These are the behavioural building blocks of the bot.

## Files

- [ginarr-bot.md](ginarr-bot.md) — tmux-run launcher for the Claude Code process.
- [ginarr-watchdog.md](ginarr-watchdog.md) — per-minute cron health check and self-healer; also nannies `obsidian-sync` and publishes a shared heartbeat for the sibling bot (`~/shared/ginarr/last-seen.txt`).
- [obsidian-sync.md](obsidian-sync.md) — long-lived `ob sync` loop that keeps the vault in sync with Obsidian's hosted service.
- [statusline.md](statusline.md) — status line renderer: `[Ginarr] · ctx:Nk/1M (P%) · $X.XX`.
- [redactor.md](redactor.md) — secret-pattern scrubber (Layer 2 regex + Layer 3 owner denylist).
- [log_event.md](log_event.md) — write-path hook: appends one JSONL event per conversational turn.
- [pre_tool_denylist.md](pre_tool_denylist.md) — Layer 1 `PreToolUse` hook: denies tool calls targeting denylisted paths.
- [summarize-day.md](summarize-day.md) — cron launcher for the `summarize-day` skill (00:15 UTC daily roll-up).
- [ingest-and-weave.md](ingest-and-weave.md) — cron launcher for the `ingest-and-weave` skill (00:25 UTC, chained after summarize-day).
- [lint-wiki-reminder.md](lint-wiki-reminder.md) — weekly Telegram reminder to run `/lint-wiki` manually (Sundays 09:00 UTC). Does NOT run the skill itself.
- [lint-indexes.md](lint-indexes.md) — cron launcher for the `lint-indexes` skill against the manual side of the Obsidian vault (every 6 hours).

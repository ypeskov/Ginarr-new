# Scripts

Everything in `.claude/scripts/`. These are the behavioural building blocks of the bot.

## Files

- [ginarr-bot.md](ginarr-bot.md) — tmux-run launcher for the Claude Code process.
- [ginarr-watchdog.md](ginarr-watchdog.md) — per-minute cron health check and self-healer.
- [statusline.md](statusline.md) — status line renderer: `[Ginarr] · ctx:Nk/1M (P%) · $X.XX`.
- [redactor.md](redactor.md) — secret-pattern scrubber (Layer 2 regex + Layer 3 owner denylist).
- [log_event.md](log_event.md) — write-path hook: appends one JSONL event per conversational turn.
- [pre_tool_denylist.md](pre_tool_denylist.md) — Layer 1 `PreToolUse` hook: denies tool calls targeting denylisted paths.
- [summarize-day.md](summarize-day.md) — cron launcher for the `summarize-day` skill (00:15 UTC daily roll-up).

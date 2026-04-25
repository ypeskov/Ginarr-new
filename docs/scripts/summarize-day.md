# `summarize-day.sh` — cron launcher for the daily summary skill

Thin wrapper that fires Claude Code in headless mode against the `summarize-day` skill once per night.

## Source

- Script: [`.claude/scripts/summarize-day.sh`](../../.claude/scripts/summarize-day.sh).
- Skill it invokes: [`/summarize-day`](../skills/summarize-day.md).
- Cron line: `15 0 * * * /home/krokobot/Ginarr/.claude/scripts/summarize-day.sh`.

## Installing the cron entry

The cron line lives in the **owner's user crontab** (not `/etc/cron.d/`), the same place the watchdog and the OpenClaw digest scripts are wired. Install once per machine:

```bash
chmod +x /home/krokobot/Ginarr/.claude/scripts/summarize-day.sh

# Append the line if it isn't already there
( crontab -l 2>/dev/null | grep -F summarize-day.sh ) || \
  ( crontab -l 2>/dev/null; echo '15 0 * * * /home/krokobot/Ginarr/.claude/scripts/summarize-day.sh' ) | crontab -

# Verify
crontab -l | grep summarize-day
```

To remove it: `crontab -e` and delete the line. To inspect what cron actually ran last night: `tail -50 .claude/scripts/logs/summarize-day.log`.

## What it does

1. Sets `HOME`, `PATH`, and `GINARR_VAULT_ROOT` (default `~/obsidian-vaul/chat-memory/`).
2. `cd ~/Ginarr` so Claude picks up this repo's `.claude/` skills directory.
3. Runs `claude -p "/summarize-day"` with a tight allowlist (`Bash`, `Read`, `Write`, `Glob`) and `--permission-mode acceptEdits`.
4. Appends stdout / stderr to `.claude/scripts/logs/summarize-day.log` along with the exit code.

The script does not pass `--continue` — each cron run is a fresh headless session. State across nights lives entirely in the vault (existing summary files determine which days are still missing).

## Failure modes worth checking

| Symptom in `summarize-day.log`                                | Likely cause                                                       |
|---------------------------------------------------------------|--------------------------------------------------------------------|
| `vault not found`                                             | `$GINARR_VAULT_ROOT` doesn't exist or the Mac unmounted it.        |
| Many runs in a row print `up to date` then suddenly process N days | Cron was paused (server reboot, watchdog disabled). Backfill kicked in.   |
| Non-zero exit, partial summary written                         | Claude headless ran out of context on a huge day. Re-run by hand.  |

## Manual run

```
bash /home/krokobot/Ginarr/.claude/scripts/summarize-day.sh
tail -50 /home/krokobot/Ginarr/.claude/scripts/logs/summarize-day.log
```

The launcher is idempotent — re-running the same night is a no-op once the summary exists. To force a re-summary of one day, ask the assistant directly with the date, not via the cron launcher.

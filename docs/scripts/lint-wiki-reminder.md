# `lint-wiki-reminder.sh` — weekly nudge to run `/lint-wiki`

Sends one Telegram reminder per week. Does NOT run the `lint-wiki` skill itself.

## Source

- Script: [`.claude/scripts/lint-wiki-reminder.sh`](../../.claude/scripts/lint-wiki-reminder.sh).
- Skill it nudges (run separately, by hand): [`/lint-wiki`](../skills/lint-wiki.md).
- Cron line: `0 9 * * 0 /home/krokobot/Ginarr/.claude/scripts/lint-wiki-reminder.sh`.

## Why a reminder, not an auto-run

The `lint-wiki` skill produces an action list — orphans, contradictions, missing cross-references — for the owner to resolve. Auto-running would either:

- Flood `wiki/_health/` with redundant reports, or
- Require auto-resolution (write back to entity pages), which defeats the audit purpose.

So the cron only nudges; the owner runs the skill when convenient.

## Installing the cron entry

The cron line lives in the **owner's user crontab** (not `/etc/cron.d/`). Install once per machine:

```bash
chmod +x /home/krokobot/Ginarr/.claude/scripts/lint-wiki-reminder.sh

# Append the line if it isn't already there
( crontab -l 2>/dev/null | grep -F lint-wiki-reminder.sh ) || \
  ( crontab -l 2>/dev/null; echo '0 9 * * 0 /home/krokobot/Ginarr/.claude/scripts/lint-wiki-reminder.sh' ) | crontab -

# Verify
crontab -l | grep lint-wiki-reminder
```

To remove: `crontab -e` and delete the line.

## What it does

1. Sets `HOME`, `PATH`, `GINARR_VAULT_ROOT`.
2. `cd ~/Ginarr` so Claude picks up this repo's `.claude/` skills directory.
3. Runs `claude -p "<reminder prompt>"` with the Telegram reply tool allowlisted, telling the headless instance to send one short message: «Время прогнать /lint-wiki - еженедельная проверка вики».
4. Appends stdout / stderr to `.claude/scripts/logs/lint-wiki-reminder.log` along with the exit code.

The wrapper does not pass `--continue` — each run is a fresh headless session. State doesn't matter; the message is one-shot.

## Failure modes

| Symptom in `lint-wiki-reminder.log`                | Likely cause                                                              |
|----------------------------------------------------|---------------------------------------------------------------------------|
| `Telegram channel not configured`                   | `/telegram:configure` has not been run on this host. Run it once.         |
| Reminder sent to the wrong chat                     | Channel access list points at multiple chats. Check `/telegram:access`.   |
| Non-zero exit, no message delivered                 | Headless Claude failed to identify the chat. Inspect the log for details. |

## Manual run

```
bash /home/krokobot/Ginarr/.claude/scripts/lint-wiki-reminder.sh
tail -50 /home/krokobot/Ginarr/.claude/scripts/logs/lint-wiki-reminder.log
```

The script is safe to re-run — it just sends one more reminder.

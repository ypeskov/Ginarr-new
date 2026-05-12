# `ingest-and-weave.sh` — cron launcher for the entity weaver

Thin wrapper that fires Claude Code in headless mode against the `ingest-and-weave` skill once per night, ten minutes after `summarize-day` finishes.

## Source

- Script: [`.claude/scripts/ingest-and-weave.sh`](../../.claude/scripts/ingest-and-weave.sh).
- Skill it invokes: [`/ingest-and-weave`](../skills/ingest-and-weave.md).
- Cron line: `25 0 * * * <repo>/.claude/scripts/ingest-and-weave.sh`.

## Installing the cron entry

The cron line lives in the **owner's user crontab** (not `/etc/cron.d/`), the same place the watchdog and `summarize-day` are wired. Install once per machine:

```bash
chmod +x <repo>/.claude/scripts/ingest-and-weave.sh

# Append the line if it isn't already there
( crontab -l 2>/dev/null | grep -F ingest-and-weave.sh ) || \
  ( crontab -l 2>/dev/null; echo '25 0 * * * <repo>/.claude/scripts/ingest-and-weave.sh' ) | crontab -

# Verify
crontab -l | grep ingest-and-weave
```

To remove it: `crontab -e` and delete the line. To inspect what cron actually ran last night: `tail -50 .claude/scripts/logs/ingest-and-weave.log`.

## What it does

1. Sets `HOME`, `PATH`, and `GINARR_VAULT_ROOT` (default `~/obsidian-vaul/Auto-Wiki/`).
2. `cd ~/Ginarr` so Claude picks up this repo's `.claude/` skills directory.
3. Runs `claude -p "/ingest-and-weave"` with a tight allowlist (`Bash`, `Read`, `Write`, `Edit`, `Glob`) and `--permission-mode acceptEdits`.
4. Appends stdout / stderr to `.claude/scripts/logs/ingest-and-weave.log` along with the exit code.

The script does not pass `--continue` — each cron run is a fresh headless session. State across nights lives entirely in the vault (existing entity pages and per-fact `[[<date>]]` anchors determine which facts are still missing).

## Failure modes worth checking

| Symptom in `ingest-and-weave.log`                               | Likely cause                                                           |
|-----------------------------------------------------------------|------------------------------------------------------------------------|
| `summary not found for <date>`                                  | `summarize-day` failed or hadn't finished by 00:25 UTC. Re-run by hand. |
| Many runs in a row exit cleanly with no entity changes          | Either no summaries were built, or every fact in the new summaries was already on its entity page (idempotency working). |
| Non-zero exit, partial entity files written                     | Claude headless ran out of context on a huge backlog. Re-run with a narrower date range by hand. |

## Manual run

```
bash <repo>/.claude/scripts/ingest-and-weave.sh
tail -50 <repo>/.claude/scripts/logs/ingest-and-weave.log
```

The launcher is idempotent — re-running the same night is a no-op once entities have been woven for that day. To force a re-weave of a specific day, ask the assistant directly with the date (e.g. `/ingest-and-weave 2026-04-26`) — the cron launcher does not pass arguments.

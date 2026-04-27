# `lint-indexes.sh` — scheduled index sync

Cron wrapper that runs Claude headless with the `/lint-indexes` skill against the **manual side** of the Obsidian vault — `~/obsidian-vaul/` minus the `Auto-Wiki/` subtree. Keeps every folder's `index.md` in sync with the actual on-disk listing without manual intervention.

## Source

- Script: [`.claude/scripts/lint-indexes.sh`](../../.claude/scripts/lint-indexes.sh).
- Skill: [`lint-indexes`](../skills/lint-indexes.md).

## Cron line

```
0 */6 * * * /home/krokobot/Ginarr/.claude/scripts/lint-indexes.sh
```

Fires every 6 hours on the hour: 00:00, 06:00, 12:00, 18:00 UTC. The 00:00 firing is independent of `summarize-day` (00:15) and `ingest-and-weave` (00:25) — different files, no contention.

## What it does

1. Sets `HOME`, `PATH`, and `GINARR_VAULT_ROOT` (Auto-Wiki path — used by the skill to recognize what to skip).
2. Invokes `claude -p "/lint-indexes ~/obsidian-vaul --apply --cron"` with `--permission-mode acceptEdits`.
3. The skill walks the vault, regenerates auto-managed `## Files` / `## Subdirectories` sections in every `index.md`, leaves all other sections untouched, and skips the `Auto-Wiki/` subtree (managed separately by `ingest-and-weave`).
4. Appends a timestamped block to the log.

## Why `--cron`

`/lint-indexes` writing outside `$GINARR_VAULT_ROOT` (i.e. into the manual vault) normally requires explicit owner confirmation in the conversation — a guard against the skill clobbering personal notes by surprise. `--cron` tells the skill that the crontab entry IS the standing authorization for this root, so the interactive pause is skipped. Only this wrapper script passes `--cron`; the skill never infers it from natural language.

## Logs

- File: `~/Ginarr/.claude/scripts/logs/lint-indexes.log`.
- Each run starts with `=== <UTC timestamp> ===` and ends with `exit: <code>`.
- Rotation: none. Tail with `tail -n 200 ~/Ginarr/.claude/scripts/logs/lint-indexes.log` if anything looks off.

## Operational notes

- **Idempotent.** A run with no on-disk changes since the previous one writes nothing — every directory's auto sections compare equal to the freshly computed ones, no diff, no edit.
- **Renames look like delete + add.** No rename detection; a renamed file shows up as the old entry removed and the new entry added (with a description regenerated from the new file's first H1).
- **Custom-grouped files are not duplicated.** If a file is mentioned in some non-auto section (e.g. `## Сводные документы`), the linter sees it as already covered and won't re-add it to `## Files` / `## Файлы`.
- **The Auto-Wiki subtree is skipped.** That tree is owned by `ingest-and-weave`. If you want to lint Auto-Wiki itself, run `/lint-indexes` manually with its root as the explicit argument.
- **Failure mode.** If the `claude` CLI is unavailable or the vault path doesn't exist, the wrapper logs the error and exits non-zero. There is no retry — the next 6-hour tick will pick up where this one left off.

## Removing or changing the schedule

```
crontab -e
```

The line is the only one referencing `lint-indexes.sh`. Delete it to disable scheduled sync; the skill remains usable manually via `/lint-indexes`. To change the cadence, edit the cron expression — every-6-hours is a default tradeoff and not load-bearing.

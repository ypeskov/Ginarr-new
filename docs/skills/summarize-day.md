# `summarize-day` — daily log roll-ups

Builds a homemade per-day index over the raw chat-memory JSONL. One Markdown file per UTC date; ~1KB; topics, people, decisions, paths. `recall` greps these first to narrow which day to drill into. The raw `logs/YYYY/MM/YYYY-MM-DD.jsonl` files stay untouched and authoritative.

## Source

- Skill: [`.claude/skills/summarize-day/SKILL.md`](../../.claude/skills/summarize-day/SKILL.md) — authoritative behaviour.
- Cron launcher: [`.claude/scripts/summarize-day.sh`](../../.claude/scripts/summarize-day.sh).
- Cron log: `.claude/scripts/logs/summarize-day.log` (gitignored — under `logs/`).

## Where summaries live

```
$GINARR_VAULT_ROOT/
├── logs/
│   ├── 2026/04/
│   │   ├── 2026-04-24.jsonl    # raw, authoritative
│   │   └── 2026-04-25.jsonl
│   └── summaries/
│       └── 2026/04/
│           ├── 2026-04-24.md   # ~1KB summary, grep-target
│           └── 2026-04-25.md
```

The `summaries/` subtree is parallel to the per-month folders, not nested inside them. That way `grep -ril` over only `summaries/` ignores the heavy raw logs entirely.

## Schedule

- **Cron**: `15 0 * * * /home/krokobot/Ginarr/.claude/scripts/summarize-day.sh`. Fires at 00:15 UTC. Processes everything strictly before today's UTC date — i.e. the just-finished UTC day plus any backlog from days the cron missed (server down, vault unmounted, etc.).
- **Idempotent**: never overwrites an existing summary. Re-running the cron job is safe; it's a no-op once the day is summarised.
- **Today (UTC) is never summarised** — the day's JSONL is still being written. `recall` knows this and falls through to `logs/<date>.jsonl` directly when the question is about today.

## Manual operations

| Want                           | How                                                                  |
|--------------------------------|----------------------------------------------------------------------|
| Run it once now                | `bash /home/krokobot/Ginarr/.claude/scripts/summarize-day.sh`        |
| Backfill missing days          | Same — the skill detects gaps and fills them oldest-first            |
| Re-summarise one day           | Ask the assistant explicitly: "пересобери summary за `<YYYY-MM-DD>`" |
| Inspect what cron did          | `tail -50 /home/krokobot/Ginarr/.claude/scripts/logs/summarize-day.log` |
| Inspect a generated file       | `Read $GINARR_VAULT_ROOT/logs/summaries/YYYY/MM/<date>.md`           |

## Format contract

Each summary file is YAML frontmatter + 3-4 short sections. Bullets are dry, declarative, and contain greppable nouns (names, paths, technologies, project codes, decisions). Adjectives and adverbs are stripped. See the format block in the skill for the exact shape.

The contract matters because `recall` depends on it: vague paraphrases break the index. If you find a summary that's too prose-y, tell the assistant to regenerate that day with stricter rules.

## Interaction with `recall`

`recall`'s scope-order has the summaries as the new step 2:

1. `notes/` — curated facts.
2. `logs/summaries/` — daily index, grep here next.
3. `logs/<date>.jsonl` — drill into a specific day only.
4. `_pending.md` — unconfirmed items, on demand.

If a summary's bullet already answers the question, `recall` quotes the bullet and cites the summary file path — no need to open the JSONL. The raw log is only opened when a summary points to a day but doesn't carry enough detail.

## Known gaps

- **Day boundary is UTC, not Sofia.** A long Sofia-evening conversation that crosses UTC midnight gets split across two summary files. Acceptable for now; if it becomes annoying we can switch to Sofia-day boundaries by adjusting the cron and the file-naming.
- **Cost.** One headless Claude Code invocation per missing day. Backfill of N days = N invocations. At 00:15 UTC steady state this is one invocation per night.
- **No re-index on edit.** If the redactor or the user later edits a JSONL post hoc (e.g. via `/redact`), the corresponding summary is not regenerated. Re-summarising that specific day is a manual step.

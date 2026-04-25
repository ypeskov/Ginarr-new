---
name: summarize-day
description: >
  Generate brief, dry, grep-friendly daily summaries of the chat-memory log.
  Use when the user asks to summarise a day's activity, when running headless
  via cron at 00:15 UTC to roll up the previous UTC day, or when the user
  notices missing summary files and asks to backfill. Reads
  `$GINARR_VAULT_ROOT/logs/YYYY/MM/YYYY-MM-DD.jsonl`, writes
  `$GINARR_VAULT_ROOT/logs/summaries/YYYY/MM/YYYY-MM-DD.md`. Never overwrites
  an existing summary unless explicitly asked.
metadata:
  project: Ginarr
  version: "1.0"
allowed-tools: Bash, Read, Write, Glob
---

# summarize-day

A homemade per-day index over the raw JSONL conversation logs. Each summary is a sub-1KB Markdown file with topics, people, and decisions for one UTC date. `recall` greps these first to narrow down which day(s) to drill into.

## Boundaries

- **Read scope**: `$GINARR_VAULT_ROOT/logs/YYYY/MM/YYYY-MM-DD.jsonl` only. Vault root defaults to `~/obsidian-vaul/chat-memory/`.
- **Write scope**: `$GINARR_VAULT_ROOT/logs/summaries/YYYY/MM/YYYY-MM-DD.md` only. Never write under `logs/YYYY/MM/` directly.
- **Day boundary**: UTC. Cron runs at 00:15 UTC, processes everything strictly before today's UTC date.
- **Idempotent**: never overwrite an existing summary. Backfill = generate missing days only.
- **Today**: never summarise today's UTC date. The day is still being written to.

## Workflow

### 1. Resolve environment

```bash
VAULT="${GINARR_VAULT_ROOT:-$HOME/obsidian-vaul/chat-memory}"
TODAY_UTC=$(date -u +%F)
NOW_UTC=$(date -u +%FT%TZ)   # use this exact value as `generated_at` for every summary written this run
```

### 2. Find missing days

Globs to run in parallel:

- `$VAULT/logs/*/*/*.jsonl` — all raw daily logs.
- `$VAULT/logs/summaries/*/*/*.md` — all existing summaries.

For each `<date>.jsonl`, check whether the matching `summaries/<YYYY>/<MM>/<date>.md` exists. Skip `<date> == TODAY_UTC`. The remainder is the backlog, oldest first.

If the backlog is empty: print `up to date` and exit 0.

### 3. For each missing day, in chronological order

a. **Read the JSONL.** Lines are `{ts, role, content[, channel, ...]}`. Roles seen: `user`, `assistant`, `system`. Reserved `system` content identifiers (snake_case): `bot_started`, `bot_stopped`, `log_paused`, `log_resumed`, `hook_error`, `consolidation_run`. Skip them — they are operational noise unless something abnormal happened (e.g. `hook_error`).

b. **Filter to signal.** Drop assistant turns that are pure tool plumbing (long blobs of file contents, command output transcripts). Keep:
   - User messages.
   - Assistant text that contains decisions, conclusions, or direct answers.
   - System events that mark anomalies.

c. **Compose the summary.** Write to a tmp path, then move into place. Format below. The `generated_at` field must be the **actual** UTC timestamp at the moment of writing — capture it once with `date -u +%FT%TZ` (or equivalent) at the start of the run, never hard-code the nominal cron time and never write a future timestamp.

d. **Report**: print one line to stdout — `wrote logs/summaries/<YYYY>/<MM>/<date>.md (<N> bullets)`.

### 4. Done

Print a final tally line — `processed N day(s)`. Exit 0.

## Summary file format

Strict. Stays under ~50 lines, ~1KB. Goal: a future `grep -ril "<keyword>"` matches the right day with no false positives from noise.

```markdown
---
date: 2026-04-25
generated_at: 2026-04-26T00:15:32Z
source_log: logs/2026/04/2026-04-25.jsonl
event_count: 117
---

# 2026-04-25

## Topics
- short bullets, one line each, with concrete nouns and project names
- bullets must contain greppable keywords, not vague paraphrases
- 3 to 8 bullets — if a day has more, group them

## People
Comma-separated list of named people who came up. Empty line if none.

## Decisions
- one bullet per concrete decision the owner made or confirmed today
- include filenames, version numbers, dollar amounts where relevant
- empty section allowed; omit the heading if truly nothing

## Files and paths
- absolute or repo-relative paths the owner edited or asked about
- one bullet per path
- omit the section if none
```

### Style rules for the bullets

- Plain declarative sentences. No emojis. No hedging.
- **Language matching is per-bullet, mandatory.** Each bullet is written in the **same language the topic was actually discussed in** in the JSONL — Russian, Ukrainian, or English. Do NOT translate to English by default. Do NOT default to a single language for the whole file. The owner converses in any of these three within a single day; uniform-English summaries break grep because his future query will use his original wording.
  - Conversation in Russian → bullet in Russian.
  - Conversation in Ukrainian → bullet in Ukrainian.
  - Conversation in English → bullet in English.
  - Mixed within one topic → pick the language the substantive content was in (the language of the decisions, names, key terms), not the assistant's reply language.
  - **Section headings (`## Topics`, `## People`, `## Decisions`, `## Files and paths`) stay in English** — they are structural markers, not content.
  - **Files and paths section is always English** — paths and filenames don't translate.
  - Proper nouns keep their original script (Cyrillic names stay Cyrillic, never transliterated).
- Every bullet must answer "what would I `grep` for to find this day later?". Names, paths, technologies, project codes, decisions — these go in. Adjectives and adverbs don't. Use the **owner's exact terminology** where possible (if he called it «крокобот», write «крокобот», not "the krokobot bot").
- Never quote multi-line passages from the log. The log is the source; the summary is the index.

## Backfill semantics

Missing day = JSONL exists, summary does not, date is strictly before today's UTC date. Generate it. Order is chronological.

If a day's JSONL is suspiciously small (< 1KB or `event_count < 5`): write a one-line summary anyway with a `## Topics\n- (low activity)` line. Still gives `recall` a hit and prevents repeated backfill attempts.

If `$GINARR_VAULT_ROOT` does not exist: print `vault not found` and exit 1.

## Invocation

- **Cron** (headless): `15 0 * * *  /home/krokobot/Ginarr/.claude/scripts/summarize-day.sh`. Runs daily at 00:15 UTC.
- **Manual backfill**: `claude -p "/summarize-day"` from the repo root, or invoke the slash command from inside an interactive session.
- **Re-summarise a specific day** (overwrite): the user must say so explicitly with the date, e.g. "пересобери summary за 2026-04-23". Do not overwrite without that explicit ask.

## Don't

- Don't summarise today (UTC). The day is incomplete.
- Don't read or grep the user's private auto-memory under `~/.claude/projects/`. That is out of scope for this skill.
- Don't include personal-secret content (tokens, passwords, addresses). The redactor at write time should already have stripped them, but the bullets must not re-promote anything that does slip through.
- Don't quote raw user messages verbatim. Paraphrase to a one-line topic.
- Don't write a summary that is longer than the source. If a day has 5 lines of log, the summary has 1-2 bullets.

## See also

- `recall` skill — consumes these summaries as the new first read layer.
- `docs/skills/summarize-day.md` — operator doc.
- `docs/architecture.md` — overall data layout.

---
name: recall
description: >
  Answer retrospective questions about the owner or past conversations
  by searching the chat-memory vault before replying. Consult whenever
  the user asks what they said earlier, when something was decided,
  what their plans or preferences were, or asks you to remember a past
  fact. Do not trigger on operational questions (how code works, what
  is in a file, run tests) — those are not retrospective.
metadata:
  project: Ginarr
  version: "1.0"
---

# recall

Read-side memory skill. Complements `capture` (write-side). When the owner asks a retrospective question, search `$GINARR_VAULT_ROOT/notes/` first; if needed, fall back to `$GINARR_VAULT_ROOT/logs/YYYY/MM/*.jsonl` within a bounded date window. Answer **from what you found**, citing the source. If nothing was found, say so — do not invent.

## Scope order (authoritative)

1. **`notes/` first.** These are curated facts — one topic per file, owner-visible. If a note covers the question, quote or summarise it and stop. Do not "double-check" in the logs: notes are the authority, logs are the raw material they were derived from.
2. **`logs/` second, only if notes don't cover it.** Always bound the grep by a date window — unbounded grep across years of JSONL is wasteful and picks up noise.
3. **`_pending.md` on demand.** If the question implies something the owner was recently thinking about but may not have confirmed, also consult `$GINARR_VAULT_ROOT/notes/_pending.md`. Flag that the match is unconfirmed in the reply.
4. **Nothing found.** Say it plainly — do not fabricate. Optionally suggest that `capture` will pick it up next time if the owner wants to start tracking the topic.

## Date windows and local time

The owner's default timezone is **Europe/Sofia** (UTC+2 in winter, UTC+3 in DST summer). The session prompt shows today's date in UTC.

When the question includes a relative phrase, convert it to a UTC window in-head using `Europe/Sofia` and today's date:

| Phrase | Example window (today = 2026-04-24, DST → UTC+3) |
|---|---|
| "вчера днём" / "yesterday afternoon" | `2026-04-23T09:00:00Z..2026-04-23T15:00:00Z` |
| "на прошлой неделе" | `2026-04-13T00:00:00Z..2026-04-20T00:00:00Z` (Mon..Mon, local) |
| "час назад" | `now - 1h` |
| "в марте" | `2026-03-01T00:00:00Z..2026-04-01T00:00:00Z` |

If unsure about an offset or DST boundary, cross-check with `TZ=Europe/Sofia date -d "yesterday 14:00" -u +%FT%TZ` — Bash, read-only. If the owner is travelling and names a different TZ inline ("today 14:00 Bangkok time"), use the stated TZ for that query.

If no period is given and notes don't resolve the question, either:

- Default to the **last 7 days** and say so in the reply ("в логах за последнюю неделю…"), or
- Ask "с какого момента смотреть?" before grepping.

## Workflow

1. **Parse the question.** Extract (a) topic / keyword(s), (b) date scope if any.
2. **Grep notes.** `grep -rli "<keyword>" "$GINARR_VAULT_ROOT/notes/"`. Run variants in parallel: morphological roots (Russian `собак` catches `собаки`/`собаку`), singular/plural, EN↔RU aliases.
3. **Match in notes?** → `Read` each hit. If the answer is there, reply and cite the note path (`— из notes/user/dog_rex.md`). Stop.
4. **No match, or note too thin?** → Build the UTC date window (above). Grep the matching log files: `grep -h "<keyword>" "$GINARR_VAULT_ROOT/logs/YYYY/MM/YYYY-MM-DD.jsonl"`. Each line is a JSONL event — parse `ts`, `role`, `content`. Quote the relevant span with its UTC timestamp. For multi-day windows, loop over the daily files inside the range.
5. **Cite sources.** Every factual claim in the reply names its origin — note path or log timestamp. No unsourced assertions.
6. **Nothing found.** State it plainly. Do not guess.

## Keyword search discipline

- Prefer **substring grep** (`grep -i`) over regex — keyword is usually a name, noun, or phrase.
- Try morphological variants: `dog`/`dogs`, `собак` (as a root) to catch declensions.
- Do not auto-translate silently — run both the owner's phrasing and an obvious alias if you suspect one (`Sofia` / `София`).
- Parallelise independent greps in one turn to keep latency low.

## Citing log events

JSONL line format:

```
{"ts": "2026-04-23T11:02:14.123Z", "role": "user", "content": "..."}
```

Cite as `logs/YYYY/MM/YYYY-MM-DD.jsonl#ts=<ts>` — same pointer shape the `capture` skill uses in note `source:` frontmatter, so a future promotion of the log event into a note keeps the chain intact.

## Write boundary

`recall` **never writes**. It reads `notes/` and `logs/`, and that is all. If during recall you notice something the owner said that *should* have been captured but was not (no matching note), flag it in the reply — `capture` may pick it up on the next trigger, but `recall` itself does not create or amend notes.

## Reply shape (Telegram)

- Short, direct answer **first**.
- Source citation on a new line:
  - Note: `— из notes/user/dog_rex.md`.
  - Log: `"..." — 2026-04-23T11:02Z`.
  - Pending (unconfirmed): `— из notes/_pending.md, ещё не подтверждено`.
- If nothing found, one line, in the language of the question: "В vault ничего по этой теме нет." / "Nothing in the vault on that."
- No prefaces ("Я посмотрел в notes и логи…") — cite after answering, not before.

## Ginarr vault ≠ your private memory

`$GINARR_VAULT_ROOT/notes/` is the **owner-facing** vault — the source of truth for facts about the owner, mirrored to their Obsidian client. Your private auto-memory under `~/.claude/projects/.../memory/` is a separate, Claude-only notebook.

- Retrospective question about the owner or past sessions → Ginarr vault.
- Meta-question about Claude's own conventions / tool quirks → private memory.

Do not cross-contaminate. When in doubt, a question about the human goes to the Ginarr vault.

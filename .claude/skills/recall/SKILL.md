---
name: recall
description: >
  Answer retrospective questions about the owner or past conversations
  by searching the Auto-Wiki vault before replying. Consult whenever
  the user asks what they said earlier, when something was decided,
  what their plans or preferences were, or asks you to remember a past
  fact. Do not trigger on operational questions (how code works, what
  is in a file, run tests) — those are not retrospective.
metadata:
  project: Ginarr
  version: "1.1"
---

# recall

Read-side memory skill. Complements `capture` and `ingest-and-weave` (the two write-side skills). When the owner asks a retrospective question, search `$GINARR_VAULT_ROOT/wiki/entities/` first; if that doesn't resolve it, grep the per-day summaries in `$GINARR_VAULT_ROOT/logs/summaries/`; only then drill into the raw JSONL in `$GINARR_VAULT_ROOT/logs/YYYY/MM/*.jsonl`, and only on the days the summaries point to. Answer **from what you found**, citing the source. If nothing was found, say so — do not invent.

## Scope order (authoritative)

1. **`wiki/entities/` first.** Entity pages are curated facts — one page per person / project / place / technology / organization, organised into topic folders (`dating/`, `work/`, `tech/`, `health/`, `finance/`, `immigration/`, `owner/`, `family/`). Always **search recursively** (`grep -rli` walks subfolders by default; `find` calls must include the entire `wiki/entities/` tree). `_owner.md` lives at the entities root (no topic folder) and is the consolidated owner-meta page (profile, biography, health, values, communication preferences). If an entity page covers the question, quote or summarise it and stop. Do not "double-check" in the logs: entities are the authority, logs are raw material.
2. **`logs/summaries/` second.** Per-day Markdown summaries built by `summarize-day`. Each is a sub-1KB index for one UTC date with topics, people, decisions. `grep -ril "<keyword>" "$GINARR_VAULT_ROOT/logs/summaries/"` is fast even across years and tells you which day(s) to drill into. If a summary's bullet already answers the question, quote that bullet and cite the summary file — no need to open the JSONL.
3. **`logs/` JSONL third, only on the days the summaries flagged.** When a summary points to a day but doesn't quote enough detail, open just that one `logs/YYYY/MM/<date>.jsonl` and grep within it. Do not blanket-grep all logs. If summaries returned nothing for the keyword and entities don't cover it, expand the JSONL grep to a bounded date window (see below) — but treat that as a fallback, not the default.
4. **`_pending.md` on demand.** If the question implies something the owner was recently thinking about but may not have confirmed, also consult `$GINARR_VAULT_ROOT/wiki/_pending.md`. Flag that the match is unconfirmed in the reply.
5. **`wiki/archive/` only when the question is explicitly historical.** Migration originals (pre-2026-04-26 type-folders) live there. Don't grep this layer by default; consult only if the user asks for the original / pre-migration version of a fact.
6. **Today (UTC)** has no summary yet — `summarize-day` only processes complete days. If the question is clearly about today, skip step 2 and grep today's JSONL directly.
7. **Nothing found.** Say it plainly — do not fabricate. Optionally suggest that `capture` will pick it up next time if the owner wants to start tracking the topic.

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
2. **Grep entity pages.** `grep -rli "<keyword>" "$GINARR_VAULT_ROOT/wiki/entities/"` (recursive, walks all topic folders). Run variants in parallel: morphological roots (Russian `собак` catches `собаки`/`собаку`), singular/plural, EN↔RU aliases. Also scan `aliases:` frontmatter — entities can match through alternate renderings: `grep -rh "^aliases:" "$GINARR_VAULT_ROOT/wiki/entities/"`.
3. **Match in entities?** → `Read` each hit. If the answer is there, reply and cite the entity path including its topic folder (`— из wiki/entities/_owner.md` for root pages, `— из wiki/entities/<topic>/<slug>.md` for topic-folder pages). Stop.
4. **No match, or note too thin?** → Grep summaries: `grep -ril "<keyword>" "$GINARR_VAULT_ROOT/logs/summaries/"` (parallel for variants). Each hit is a `YYYY-MM-DD.md` for one UTC day. If the bullet inside answers the question on its own, quote it and cite `logs/summaries/YYYY/MM/<date>.md`. Stop.
5. **Summary points to a day but lacks detail?** → Open just that one `logs/YYYY/MM/<date>.jsonl` and grep inside it: `grep -h "<keyword>" "$GINARR_VAULT_ROOT/logs/YYYY/MM/<date>.jsonl"`. Each line is a JSONL event — parse `ts`, `role`, `content`. Quote the relevant span with its UTC timestamp.
6. **Summaries returned nothing AND notes are thin?** → Fall back to a bounded JSONL grep over the date window (see below). Use this only when summaries genuinely missed; do not pre-empt step 4 with it.
7. **Today (UTC).** No summary exists. If the question is about today, skip the summary step and grep today's JSONL directly.
8. **Cite sources.** Every factual claim in the reply names its origin — note path, summary path, or log timestamp. No unsourced assertions.
9. **Nothing found.** State it plainly. Do not guess.

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

`recall` **never writes**. It reads `wiki/` and `logs/`, and that is all. If during recall you notice something the owner said that *should* have been captured but was not (no matching note), flag it in the reply — `capture` may pick it up on the next trigger, but `recall` itself does not create or amend notes.

## Reply shape (Telegram)

- Short, direct answer **first**.
- Source citation on a new line:
  - Note: `— из wiki/entities/_owner.md` or `— из wiki/entities/<topic>/<slug>.md`.
  - Log: `"..." — 2026-04-23T11:02Z`.
  - Pending (unconfirmed): `— из wiki/_pending.md, ещё не подтверждено`.
- If nothing found, one line, in the language of the question: "В vault ничего по этой теме нет." / "Nothing in the vault on that."
- No prefaces ("Я посмотрел в notes и логи…") — cite after answering, not before.

## Topic-scoped recall

When the question is naturally bounded to a topic (e.g. "что я говорил про работу в марте", "напомни про текущий dating-фокус"), narrow the entity grep to the relevant topic folder first:

```bash
grep -rli "<keyword>" "$GINARR_VAULT_ROOT/wiki/entities/dating/"
```

For cross-topic membership, also grep the `topics:` frontmatter to find entities that participate in the topic as a secondary tag (e.g. Boo dating app has `topics: [dating, tech]` — included by both `dating` and `tech` queries):

```bash
grep -rl "^topics:.*dating" "$GINARR_VAULT_ROOT/wiki/entities/"
```

The `/load-topic <name>` skill handles topic-scoped context loading at session-start scale; `recall` handles single-question lookups.

## Ginarr vault ≠ your private memory

`$GINARR_VAULT_ROOT/wiki/` is the **owner-facing** vault — the source of truth for facts about the owner, mirrored to their Obsidian client. Your private auto-memory under `~/.claude/projects/.../memory/` is a separate, Claude-only notebook.

- Retrospective question about the owner or past sessions → Ginarr vault.
- Meta-question about Claude's own conventions / tool quirks → private memory.

Do not cross-contaminate. When in doubt, a question about the human goes to the Ginarr vault.

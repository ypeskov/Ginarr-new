# `recall` — read-side memory skill

The skill Claude consults before answering retrospective questions about the owner or past conversations. Pairs with the two write-side skills `capture` (owner-action driven) and `ingest-and-weave` (cron-driven).

## Source

- Skill: [`.claude/skills/recall/SKILL.md`](../../.claude/skills/recall/SKILL.md) — authoritative behaviour (LLM-facing).
- Data read: `$GINARR_VAULT_ROOT/wiki/entities/` (curated entity pages — `_owner.md` at the root, plus one per person/project/place/technology/organization/event under topic folders `dating/`, `work/`, `tech/`, `health/`, `finance/`, `immigration/`, `owner/`, `family/`), then `$GINARR_VAULT_ROOT/logs/summaries/` and `logs/YYYY/MM/<date>.jsonl`, plus `wiki/_pending.md` for unconfirmed candidates. Never written. All entity reads are recursive — entities can live in any topic folder. Legacy SPEC.v3 type-folders (`wiki/{user,feedback,projects,reference,decisions}/`) were collapsed into entities/ on 2026-04-26 and archived under `wiki/archive/migration-2026-04-26/`; that path is checked only when the user explicitly asks for the original / pre-migration version of a fact.

## When it fires

Retrospective questions from the owner — "what did I say about X", "when did we decide Y", "remember Z", "what were my plans for W". Not operational questions (code, tests, files); those are handled inline without the skill.

## Scope order

1. `wiki/entities/` — if an entity page covers the question, answer from it and stop. Entities are the authority; logs are raw material.
2. `logs/summaries/` — daily roll-ups built by `summarize-day`. Grep here second.
3. `logs/YYYY/MM/<date>.jsonl` — raw event log, only on the days the summaries flagged.
4. `wiki/_pending.md` on demand, when the question hints at something recent but not yet confirmed. Matches flagged unconfirmed.
5. `wiki/archive/migration-2026-04-26/` only when the user explicitly asks for the pre-migration / original version of a fact. Not a default scope.
6. Nothing found → say so plainly; do not fabricate.

## Local time handling

Owner default TZ: **Europe/Sofia** (UTC+2 winter, UTC+3 DST summer). The skill converts phrases like "yesterday afternoon" / "вчера днём" / "в марте" into UTC windows in-head, using today's UTC date and the Europe/Sofia offset (DST-aware). Cross-check with `TZ=Europe/Sofia date -u …` when a DST boundary is ambiguous.

Travel override: the owner can name another TZ inline ("today 14:00 Bangkok time") — the skill uses the stated TZ for that query instead of the default.

If no period is given and entities don't resolve the question, the skill either defaults to the last 7 days (and says so in the reply) or asks the owner before grepping.

## Reply discipline

- Direct answer first, source citation after.
- Entity citation: `— из wiki/entities/<topic>/<slug>.md` (e.g. `— из wiki/entities/_owner.md` for owner-meta facts at root, `— из wiki/entities/dating/eli_badoo.md` for topic-folder pages).
- Log citation: `"..." — 2026-04-23T11:02Z` (UTC).
- Pending citation: `— из wiki/_pending.md, ещё не подтверждено`.
- Nothing found: one line, no preface, in the language of the question.
- Never fabricate an answer when the vault is silent.

## Write boundary

`recall` reads; it never writes. If a missing capture is noticed during recall (the owner asks about a fact that was told but never landed in `wiki/entities/`), the reply flags it. `capture` picks it up on the next natural trigger; `recall` itself does not amend the vault.

## Relationship to the other memory skills

- `capture` writes — owner-action driven, routes to `wiki/entities/<topic>/<slug>.md` (or `_owner.md` for owner-meta).
- `ingest-and-weave` writes — cron-driven, reads daily summaries, weaves entities. Never writes to `_owner.md`.
- `recall` reads — finds those entity pages when the owner asks retrospective questions.
- `review` walks `_pending.md` candidates with confirm / drop / edit.

## Relationship to Claude's private auto-memory

Retrospective questions about the owner → Auto-Wiki vault. Meta-questions about Claude's own conventions → private `~/.claude/projects/.../memory/`. Do not cross-contaminate.

## Testing

LLM-driven; no self-test harness. Walk with representative prompts and verify the reply cites a real source:

| Input                                            | Expected                                                                                                                            |
|--------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| "как зовут мою собаку?"                          | Grep `wiki/entities/`; check `_owner.md` § Family or a `dog_*.md` entity page; reply with cite, e.g. `— из wiki/entities/_owner.md`. |
| "что я вчера вечером говорил про марафон?"        | Grep `logs/summaries/` then `logs/YYYY/MM/YYYY-MM-DD.jsonl` within the UTC window for yesterday evening (Europe/Sofia).             |
| "что у меня в vault про нейронки?"                | Grep recursively across `wiki/entities/` (all topic folders), list matching files with one-line summaries and their topic-folder paths. |
| "что у меня сейчас по dating-фронту?"             | Narrow grep to `wiki/entities/dating/` and to entities with `topics:` containing `dating`; summarise each active prospect.          |
| "когда у меня следующая встреча?"                 | Nothing found → "В vault ничего по этой теме нет." No fabrication.                                                                  |
| "кажется я недавно думал про смену БД?"           | `_pending.md` has a matching block → quote it, flag as unconfirmed.                                                                 |

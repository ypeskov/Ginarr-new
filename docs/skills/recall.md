# `recall` — read-side memory skill

The skill Claude consults before answering retrospective questions about the owner or past conversations. Second of the three SPEC.v3 memory skills (`capture` / `recall` / `review`).

## Source

- Skill: [`.claude/skills/recall/SKILL.md`](../../.claude/skills/recall/SKILL.md) — authoritative behaviour (LLM-facing).
- Data read: `$GINARR_VAULT_ROOT/notes/` (curated facts) then `$GINARR_VAULT_ROOT/logs/` (raw transcript) and `notes/_pending.md` (unconfirmed candidates). Never written.

## When it fires

Retrospective questions from the owner — "what did I say about X", "when did we decide Y", "remember Z", "what were my plans for W". Not operational questions (code, tests, files); those are handled inline without the skill.

## Scope order

Authoritative per SPEC.v3:

1. `notes/` — if a curated note covers the question, answer from it and stop. Notes are the authority; logs are raw material they were derived from.
2. `logs/` only if notes do not cover it. Always within a bounded date window.
3. `_pending.md` on demand, when the question hints at something recent but not yet confirmed. Matches from there are flagged unconfirmed.
4. Nothing found → say so plainly; do not fabricate.

## Local time handling

Owner default TZ: **Europe/Sofia** (UTC+2 winter, UTC+3 DST summer). The skill converts phrases like "yesterday afternoon" / "вчера днём" / "в марте" into UTC windows in-head, using today's UTC date and the Europe/Sofia offset (DST-aware). Cross-check with `TZ=Europe/Sofia date -u …` when a DST boundary is ambiguous.

Travel override: the owner can name another TZ inline ("today 14:00 Bangkok time") — the skill uses the stated TZ for that query instead of the default.

If no period is given and notes don't resolve the question, the skill either defaults to the last 7 days (and says so in the reply) or asks the owner before grepping.

## Reply discipline

- Direct answer first, source citation after.
- Note citation: `— из notes/user/dog_rex.md`.
- Log citation: `"..." — 2026-04-23T11:02Z` (UTC).
- Pending citation: `— из notes/_pending.md, ещё не подтверждено`.
- Nothing found: one line, no preface, in the language of the question.
- Never fabricate an answer when the vault is silent.

## Write boundary

`recall` reads; it never writes. If a missing capture is noticed during recall (the owner asks about a fact that was told but never landed in `notes/`), the reply flags it. `capture` picks it up on the next natural trigger; `recall` itself does not amend the vault.

## Relationship to the other memory skills

- `capture` writes — triages owner statements into notes.
- `recall` reads — finds those notes when the owner asks retrospective questions.
- `review` (Phase 3.3) walks `_pending.md` candidates with confirm / drop / edit.

## Relationship to Claude's private auto-memory

Retrospective questions about the owner → Ginarr vault. Meta-questions about Claude's own conventions → private `~/.claude/projects/.../memory/`. Do not cross-contaminate.

## Testing

LLM-driven; no self-test harness. Walk with representative prompts and verify the reply cites a real source:

| Input | Expected |
|---|---|
| "как зовут мою собаку?" | Grep `notes/user/`; match `dog_rex.md`; reply `Рекс — из notes/user/dog_rex.md`. |
| "что я вчера вечером говорил про марафон?" | Grep `logs/YYYY/MM/YYYY-MM-DD.jsonl` within the UTC window for yesterday evening (Europe/Sofia). Quote matching events with timestamps. |
| "что у меня в vault про нейронки?" | Grep across `notes/`, list matching files with one-line summaries. |
| "когда у меня следующая встреча?" | Nothing found → "В vault ничего по этой теме нет." No fabrication. |
| "кажется я недавно думал про смену БД?" | `_pending.md` has a matching block → quote it, flag as unconfirmed. |

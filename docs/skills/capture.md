# `capture` — write-side memory skill

The skill that decides whether a user statement is worth persisting to the Auto-Wiki vault, and if so to which entity page. The owner-action-driven writer of `wiki/entities/` (paired with `ingest-and-weave`, the cron-driven writer reading daily summaries).

## Source

- Skill: [`.claude/skills/capture/SKILL.md`](../../.claude/skills/capture/SKILL.md) — authoritative behaviour.
- Data store: `$GINARR_VAULT_ROOT/wiki/entities/` — owner-facing Obsidian vault, see [`architecture.md`](../architecture.md).

## When it fires

The `description` field in the skill's frontmatter tells Claude Code when to load it: a user turn that states a fact about themselves, expresses a preference, gives feedback on how to work with them, makes a decision, or explicitly asks to remember. Purely operational turns (debugging, code tasks, one-off requests) do not trigger it.

## Four paths

Triage by confidence:

| Path                 | Trigger                                                                        | Storage                                                                                  |
|----------------------|--------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| **Auto-save**        | High confidence (explicit remember, direct feedback, factual self-claim, confirmed decision) | Append to `wiki/entities/<slug>.md`. New page if no match.                               |
| **Unconfirmed save** | Medium (indirect preference, one-off choice, inferred fact)                    | Same routing, fact bullet tagged `(unconfirmed)`.                                        |
| **`_pending.md`**    | Low / ambiguous (speculation, thinking out loud)                               | Single block appended to `wiki/_pending.md` for later `/review`.                         |
| **Ask immediately**  | Contradicts existing fact, involves external stakeholders, or borders on sensitive data | No write until the owner answers.                                                        |

## Routing

| Statement is about              | Routes to                                       |
|---------------------------------|-------------------------------------------------|
| Owner himself (profile, biography, health, values, communication preferences) | `wiki/entities/_owner.md` (sectioned: Profile, Family, Health, Values, Communication preferences, …) |
| Specific named person / project / place / technology / organization / event | `wiki/entities/<slug>.md` (one entity per page) |
| Owner's relationship with another entity (e.g. "Mikhail returns from leave") | The other entity's page, with `[[_owner]]` mention inline |

Underscore-prefixed slug `_owner.md` is intentional — sort-priority hack so it appears at the top of the file explorer. The skill rule that excludes `_pending.md` / `_tools/` / `_attachments/` does not apply to `_owner.md`.

## Telegram side

- **High-confidence save** → 💾 reaction on the user's original message. No text reply. Fallback chain: 💾 → 🧠 → 👌.
- **Medium-confidence save** → 💾 reaction plus one short reply naming the entity path. No paraphrase of content.
- **Low-confidence (pending)** → silent.
- **Always-ask** → text question inline; action taken after owner's answer.

The reaction-only path for high-confidence saves is deliberate: it shows *that* something was captured without re-leaking the content into the visible reply (which would itself end up in the log).

## Threshold notification

When a low-confidence block lands in `_pending.md` and the queue reaches 5 candidates, `capture` sends one proactive Telegram message: `Накопилось N кандидатов в /review — разберёшь?`. Latch file `$GINARR_VAULT_ROOT/wiki/.pending_notified` prevents repeat pings; cleared by `review-pending` when the queue drops below 5. Terminal-only turns (no `<channel>` tag) are silent.

## Dedup

One entity = one page. Before every write the skill greps `$GINARR_VAULT_ROOT/wiki/entities/` (including `aliases:` frontmatter) for the entity's name and any rendering, and reads matches. New facts append; contradictions trigger the conflict protocol (both claims kept with date anchors, `## Conflicts` section flags the disagreement, owner asked).

## Migration history

Until 2026-04-26 the skill wrote into per-type folders (`wiki/{user,feedback,projects,reference,decisions}/`). On that date (auto-wiki roadmap step 3.4) the layout collapsed into the entity-page model and the originals moved to `wiki/archive/migration-2026-04-26/`. The skill version bumped to `2.0`; previous behaviour and the SPEC.v3 type-folders are no longer the write target.

## Relationship to `recall`, `review`, and `ingest-and-weave`

- `capture` writes — owner-action-driven.
- `ingest-and-weave` writes — cron-driven, reads daily summaries. Never writes to `_owner.md`.
- `recall` reads `wiki/entities/` first, then `logs/summaries/`, then `logs/<date>.jsonl`.
- `review` walks `_pending.md` candidates with the owner.

## Relationship to Claude's private auto-memory

Auto-Wiki vault is the **owner-facing** store — visible in Obsidian, synced across devices. Claude's per-session auto-memory under `~/.claude/projects/.../memory/` is a private notebook that stays with Claude across sessions but is never shown to the user. Facts about the human go to the Auto-Wiki vault; meta-conventions about how Claude should operate stay private.

## Testing

`capture` is LLM-driven — there is no self-test harness. Walk it with representative prompts and verify the resulting vault state manually:

| Input                                                       | Expected                                                                                   |
|-------------------------------------------------------------|--------------------------------------------------------------------------------------------|
| "Remember my dog's name is Rex."                            | Append to `wiki/entities/_owner.md` § Family (or new entity `dog_rex.md`), 💾 reaction.    |
| "I think I might prefer darker colours in the UI."          | Append `(unconfirmed)` to `_owner.md` § Communication preferences, 💾 + short reply.       |
| "Maybe we should switch databases someday."                 | Block appended to `wiki/_pending.md`, no entity write, no reply.                           |
| "Don't summarise at the end of every response."             | Append to `_owner.md` § Communication preferences, 💾 reaction.                            |
| "My dog's name is actually Max, not Rex."                   | Conflict detected on prior fact. Both claims kept with date anchors, owner asked.          |
| "Mikhail returns from leave next week, I'm preparing the case." | Append fact to `wiki/entities/ringcentral.md`, mention `[[_owner]]` inline.            |

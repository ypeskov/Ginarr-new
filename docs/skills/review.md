# `/review` — walk the pending queue

The slash command + skill the owner uses to process `wiki/_pending.md` candidates. Third of the three memory skills (`capture` / `recall` / `review`).

## Source

- Slash command: [`.claude/commands/review.md`](../../.claude/commands/review.md) — user-facing trigger.
- Skill: [`.claude/skills/review-pending/SKILL.md`](../../.claude/skills/review-pending/SKILL.md) — workflow, dedup rules, Telegram feedback.
- Data: `$GINARR_VAULT_ROOT/wiki/_pending.md` (read + rewrite), `$GINARR_VAULT_ROOT/wiki/entities/` (new or appended pages on save).

**Skill naming:** the filesystem directory is `review-pending` (not `review`) to avoid colliding with a built-in `review` skill for PR reviews. The user-facing slash command is still `/review`.

## When it fires

The owner explicitly invokes `/review` to drain the pending queue. The `capture` skill feeds that queue with low-confidence candidates — statements that sounded memorable but not confirmed enough to land as real notes automatically.

## Actions

| Command | Alias (RU) | Effect |
|---|---|---|
| `/review` | — | Show the top block + proposed entity + action prompt |
| `/review save` | `сохрани` / `да` | Promote the top block to `wiki/entities/<slug>.md` (append to existing page or create new), remove from queue, show next |
| `/review drop` | `удали` / `нет` | Remove the top block without writing a note, show next |
| `/review skip` | `пропусти` / `потом` | Rotate the top block to the end of the queue, show next |
| `/review edit` | `правь` | Enter edit sub-flow (change entity / section / body) before saving |

After a candidate is shown, bare action words in the owner's next reply are also accepted — the skill's trigger description picks them up contextually.

## Queue mechanics

`_pending.md` is a plain-Markdown queue. Blocks emitted by the post-migration `capture` skill use the entity-page shape:

```
# Pending review
…template header…

## <short title>
- ts: <UTC ISO>
- source: logs/YYYY/MM/YYYY-MM-DD.jsonl#ts=...
- proposed entity: <slug or _owner>
- proposed section: <e.g. Health, Communication preferences, Facts>

<body>
```

- Blocks are delimited by `## ` at column 0.
- The template header is preserved on every rewrite.
- The queue is FIFO by default; `skip` rotates to tail.

Legacy blocks written before 2026-04-26 may still carry the old `proposed type:` / `proposed path: wiki/<dir>/<name>.md` shape. The skill accepts both shapes and asks for a target section when the legacy form omits it. Once the queue is drained the legacy path is dead.

## Save → entity promotion

Promoting a block appends a fact bullet to `wiki/entities/<slug>.md` under the proposed section, with a date anchor (`[[YYYY-MM-DD]]`) linking back to the daily summary. If the entity page does not exist yet, it is created with the standard entity frontmatter (`name`, `aliases`, `type`, `created`, `updated`, `related`). Dedup runs first: if the same fact already lives on the page, the save is a no-op. Contradictions trigger the conflict protocol from the `capture` skill (keep both claims dated, add a `## Conflicts` entry, ask the owner).

## Edit sub-flow

Freeform natural-language edits: entity change, section change, body rewrite, or combinations. Preview → confirm → save. Cancel leaves the pending block untouched.

## Telegram feedback

See the skill doc for the full table. Short version: 💾 reaction on save actions, 👌 on drop/skip, no reaction on the candidate prompt itself.

## Threshold-latch maintenance

`capture` pings the owner once when the queue crosses 5 candidates upward, using `$GINARR_VAULT_ROOT/wiki/.pending_notified` as a latch. Every time `/review` removes a block (save or drop), the skill checks the remaining count and deletes the latch if it is below 5, so the next accumulation triggers a fresh ping. Skip does not change the count, so it leaves the latch alone.

## Relationship to the other memory skills

- `capture` writes the queue.
- `recall` reads `wiki/` and `logs/`, may also peek at `_pending.md` for unconfirmed hints.
- `review` (this skill) drains the queue at the owner's request.

## Not yet implemented

- **Inline keyboard UI** — Telegram supports button-based prompts; the current setup keeps text-only actions for portability across non-Telegram channels.

## Testing

LLM-driven; no self-test harness. Walk manually:

| Input | Expected |
|---|---|
| `/review` on an empty queue | `В очереди ничего нет.` (or English match) |
| `/review` with one block | Body + proposed entity + action prompt |
| `/review save` | Fact appended (or new page created) at `wiki/entities/<slug>.md`, block removed, next candidate shown (or empty-queue line) |
| `/review drop` | Block removed, no entity write |
| `/review skip` | Block moved to tail of `_pending.md`, next candidate shown |
| `/review edit` → change entity → save | Fact appended to the new entity's page, block removed |
| `save` with the same fact already on the entity page | Dedup triggered: no-op or conflict protocol |

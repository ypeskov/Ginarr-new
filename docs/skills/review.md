# `/review` — walk the pending queue

The slash command + skill the owner uses to process `wiki/_pending.md` candidates. Third of the three SPEC.v3 memory skills (`capture` / `recall` / `review`).

## Source

- Slash command: [`.claude/commands/review.md`](../../.claude/commands/review.md) — user-facing trigger.
- Skill: [`.claude/skills/review-pending/SKILL.md`](../../.claude/skills/review-pending/SKILL.md) — workflow, dedup rules, Telegram feedback.
- Data: `$GINARR_VAULT_ROOT/wiki/_pending.md` (read + rewrite), `$GINARR_VAULT_ROOT/wiki/<type>/` (new files on save).

**Skill naming:** the filesystem directory is `review-pending` (not `review`) to avoid colliding with a built-in `review` skill for PR reviews. The user-facing slash command is still `/review`.

## When it fires

The owner explicitly invokes `/review` to drain the pending queue. The `capture` skill feeds that queue with low-confidence candidates — statements that sounded memorable but not confirmed enough to land as real notes automatically.

## Actions

| Command | Alias (RU) | Effect |
|---|---|---|
| `/review` | — | Show the top block + path + action prompt |
| `/review save` | `сохрани` / `да` | Promote the top block to `wiki/<type>/<name>.md` with `status: confirmed`, remove from queue, show next |
| `/review drop` | `удали` / `нет` | Remove the top block without writing a note, show next |
| `/review skip` | `пропусти` / `потом` | Rotate the top block to the end of the queue, show next |
| `/review edit` | `правь` | Enter edit sub-flow (change type / path / body) before saving |

After a candidate is shown, bare action words in the owner's next reply are also accepted — the skill's trigger description picks them up contextually.

## Queue mechanics

`_pending.md` is a plain-Markdown queue:

```
# Pending review
…template header…

## <short title>
- ts: <UTC ISO>
- source: logs/YYYY/MM/YYYY-MM-DD.jsonl#ts=...
- proposed type: user | feedback | project | reference | decision
- proposed path: wiki/<subdir>/<snake_case>.md

<body>
```

- Blocks are delimited by `## ` at column 0.
- The template header is preserved on every rewrite.
- The queue is FIFO by default; `skip` rotates to tail.

## Save → note promotion

Promoting a block produces a file in `wiki/<type>/<name>.md` with full frontmatter (`type`, `name`, `description`, `created`, `updated`, `status: confirmed`, `source`). Dedup runs first: if the name/topic already has a note, the skill offers to merge. Contradictions trigger the conflict protocol from the `capture` skill (keep both claims dated, `status: unconfirmed`, ask the owner).

## Edit sub-flow

Freeform natural-language edits: type change, path change, body rewrite, or combinations. Preview → confirm → save. Cancel leaves the pending block untouched.

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
| `/review` with one block | Body + proposed path + action prompt |
| `/review save` | File created at `wiki/<type>/<name>.md`, block removed, next candidate shown (or empty-queue line) |
| `/review drop` | Block removed, no file created |
| `/review skip` | Block moved to tail of `_pending.md`, next candidate shown |
| `/review edit` → change type → save | File created at the new type's directory, block removed |
| `save` with an existing note on the same topic | Dedup triggered: merge or conflict protocol |

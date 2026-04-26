---
name: review-pending
description: >
  Walk the owner through wiki/_pending.md candidates one at a time:
  present the top block, accept save / drop / skip / edit, and apply
  the action to the vault. Consult whenever the user invokes /review,
  or replies "save"/"drop"/"skip"/"edit" (or the Russian equivalents
  "сохрани"/"удали"/"пропусти"/"правь") after this assistant just
  presented a review candidate. Do not trigger outside a review
  context.
metadata:
  project: Ginarr
  version: "2.0"
---

# review-pending

Single-owner queue processor for `$GINARR_VAULT_ROOT/wiki/_pending.md`. Low-confidence captures from the `capture` skill land there as blocks. This skill lets the owner process them one-by-one — promote to a real entity-page fact, drop, skip, or edit — via the `/review` slash command (the primary trigger) or bare action words after a candidate has been presented.

Aligned with the entity-page model (post-2026-04-26 migration). Promotion appends a fact bullet to `$GINARR_VAULT_ROOT/wiki/entities/<slug>.md` under the proposed section, never to a type-folder.

## File layout

`_pending.md` = a Markdown template header (`# Pending review` + instructions) followed by zero or more candidate blocks separated by blank lines. Each block:

```
## <short title>
- ts: <UTC ISO>
- source: logs/YYYY/MM/YYYY-MM-DD.jsonl#ts=...
- proposed entity: <slug or _owner>
- proposed section: <e.g. Health, Communication preferences, Facts>

<body / quote>
```

Blocks are delimited by `## ` at column 0. The template header is everything before the first `## ` heading — **preserve it on every rewrite.**

## Flow

1. **Read `_pending.md`.** Parse into `header` (text before first `## ` line) + `blocks[]` (each starting with `## `). If the file is missing, treat as empty queue.
2. **Empty queue?** → one line, no reaction: `В очереди ничего нет.` / `Queue is empty.` (match language). Stop.
3. **Top block?** → Present in the reply:
   - Candidate body (truncate to ~500 chars, append `…` and `(полный блок в _pending.md)` if longer).
   - `Предложенный entity: wiki/entities/<slug>.md § <section>` (or English equivalent).
   - Inline prompt: `/review save | drop | skip | edit` (or: "ответь save/drop/skip/edit").
4. **On next action** (either `/review <action>` or a bare action word in a Telegram reply after the prompt):
   - `save` / `сохрани` / `да` → promote (below), remove the block, then present the next candidate.
   - `drop` / `удали` / `нет` → remove the block, present the next.
   - `skip` / `пропусти` / `потом` → rotate the block to the tail, present the next.
   - `edit` / `правь` → enter edit sub-flow.
   - Anything else → re-prompt once with the same candidate.

## Promote to an entity-page fact

When the owner says save on a top block:

1. **Extract fields.** From the block:
   - `slug` = from `- proposed entity:` (e.g. `_owner`, `bg_residency`, `natalya`).
   - `section` = from `- proposed section:` (e.g. `Health`, `Communication preferences`, `Facts`).
   - `title` = the `##` heading (used for context in dedup, not stored).
   - `source` = from `- source:` line.
   - `body` = everything after the bullet list, trimmed. This is the candidate fact text.
   - `date_anchor` = the date portion of the `- source:` line (`YYYY-MM-DD`). Falls back to today's UTC date if the source line is missing.
2. **Resolve the entity page.** Path is `$GINARR_VAULT_ROOT/wiki/entities/<slug>.md`.
   - If the file exists → Read it.
   - If not, also scan every existing entity's `aliases:` frontmatter (`grep -l "aliases:" wiki/entities/`) for a match — the same person can appear under multiple renderings. If an alias matches, switch the target to that slug.
   - Still no match → create the page using the entity-page format (below).
3. **Dedup.** Search the target page for an existing fact bullet that matches the candidate body (case-insensitive substring on the body text). If a match is found:
   - **Identical fact** → no-op write. Drop the pending block, reply `Skipped: already on wiki/entities/<slug>.md`.
   - **Contradictory fact** → Conflict protocol (below). Do **not** remove the pending block until the conflict is resolved.
4. **Append the fact.** One-line declarative bullet anchored by `[[<date>]]`:
   ```
   - [[YYYY-MM-DD]] <body, condensed to one line>
   ```
   Insert under the section line (`## <section>`). If the section does not yet exist, create it at the bottom of the page (above any existing `## Conflicts` section).
5. **Bump frontmatter.** Update `updated:` to today's UTC date.
6. **Remove the block from `_pending.md`.** Read → rewrite as `header + "\n\n" + join(remaining_blocks, "\n\n")` → Write. Never overwrite the header.
7. **Feedback:**
   - Telegram: 💾 reaction on the owner's `save` message (fallback 🧠 → 👌), then one short reply `Saved to wiki/entities/<slug>.md § <section>`.
   - Terminal (no `<channel>` tag): same short line, no reaction.

### Entity-page format for new pages

When the proposed entity has no existing page, create the file using the same format as `capture` and `ingest-and-weave`:

```markdown
---
name: <canonical name, in original script>
aliases: [<alt name>, <transliteration>, <nickname>]
type: <person|project|place|technology|organization|event>
created: <today UTC date>
updated: <today UTC date>
related: []
---

# <name>

<one-line description, derived from the candidate body if obvious>

## <section>

- [[<date>]] <body, one line>
```

For `_owner.md` specifically the layout is sectioned (Profile, Family, Health, Values, Communication preferences, …) rather than a flat `## Facts`; do not create `_owner.md` from this skill — it is owner-action-only and should already exist. If it does not, ask the owner before creating it.

## Edit sub-flow

1. Show the current fields (title, proposed entity, proposed section, body).
2. Ask `Что меняем?` / `What should change?` — accept freeform natural-language edits:
   - "entity → ringcentral" — change the target entity slug.
   - "section → Health" — change the target section.
   - "переформулируй body: …" — rewrite the body text (the line that becomes the fact bullet).
   - Combinations are fine.
3. Apply to an in-memory copy. Show the updated fields as a preview and ask for confirmation (`применить? да/нет`).
4. **Confirm** → run the normal save flow with the edited fields (resolve → dedup → append → remove block → feedback).
5. **Cancel** → leave the pending block unchanged, move to the next candidate.

Edits never persist into `_pending.md`. Either they land in `wiki/entities/` (on confirm) or they are discarded (on cancel).

## Skip semantics

Skip = rotate to tail. The block is not lost — it moves behind the others in `_pending.md`. `/review` always operates on the top of the queue, so a skipped block gets a second look after everything behind it has cycled through.

Implementation: Read → move `blocks[0]` to the end of `blocks[]` → rewrite `header + "\n\n" + join(blocks, "\n\n")`.

## Dedup inside the queue

Before saving, scan the remaining pending blocks for a matching topic (same `proposed entity` + same `proposed section` + similar body). If found, surface both and ask the owner which to keep. Do not silently merge queue blocks — that is the owner's call.

## Conflict protocol

Aligned with the `capture` skill's protocol:

1. **Do not overwrite the existing fact.** Both claims stay in their section with their original date anchors.
2. Append the new fact bullet alongside the old one (both retained), then add a `## Conflicts` section entry on the entity page:
   ```
   - [[<old-date>]] <claim A> ↔ [[<new-date>]] <claim B> — unresolved
   ```
3. Reply to the owner: "Конфликт на [[<slug>]] § <section>: старая версия — A ([[<date1>]]), новая — B ([[<date2>]]). Какая верна?"
4. **Do not remove the pending block until the conflict is resolved.** The block stays at the top of the queue so the next `/review` invocation surfaces it again. When the owner resolves it, delete the losing fact, trim the matching `## Conflicts` line, then remove the pending block.

## Threshold-latch maintenance

`capture` sets a latch file `$GINARR_VAULT_ROOT/wiki/.pending_notified` when the queue crosses 5 candidates upward, so the owner is pinged once per crossing. Review is responsible for clearing the latch on the downward crossing:

- After any block removal (save, drop), count the remaining `## ` headings in `_pending.md`. If the count is **below 5** and `.pending_notified` exists → delete the latch. The next time the queue climbs back past 5, `capture` will re-notify.
- Skip (rotate to tail) does not change the count — no latch action needed.
- Edit that ends in save is just a save with an extra step; the same latch-clear rule applies.
- Conflict (block stays at the top, no removal) does not change the count — no latch action needed.

## Write boundary

`review-pending` writes the vault — both `wiki/entities/<slug>.md` (new or appended) and `wiki/_pending.md` (block removal, rotation). Unlike `recall`, it is not read-only. All writes happen at the explicit direction of the owner; never auto-merge on ambiguity.

## Telegram reply shape

| Action | Reaction (best-effort) | Text reply |
|---|---|---|
| Candidate prompt | — | body + proposed entity § section + action prompt |
| Save | 💾 (→ 🧠 → 👌) | `Saved to wiki/entities/<slug>.md § <section>` |
| Save (already present) | 👌 | `Skipped: already on wiki/entities/<slug>.md` |
| Drop | 👌 | — |
| Skip | 👌 | — |
| Edit (preview) | — | updated fields + confirm prompt |
| Edit (applied) | 💾 | `Saved to wiki/entities/<slug>.md § <section>` |
| Conflict | — | both claims + question, block left in queue |
| Empty queue | — | one line |

Reactions attach to the owner's message carrying the action (their `/review save` reply). If Telegram rejects the emoji, fall back per the chain above.

## Backwards-compat for legacy pending blocks

A `_pending.md` written before 2026-04-26 may still carry the old `proposed type:` / `proposed path: wiki/<dir>/<name>.md` shape. When parsing, accept either field set:

- New shape: `proposed entity:` + `proposed section:`. Use as-is.
- Legacy shape: `proposed type:` + `proposed path: wiki/<dir>/<name>.md`. Map `<name>` to the entity slug, ask the owner which section to use (default `Facts`). Do not silently assume — legacy blocks predate the entity model and the section is genuinely ambiguous.

Mixed-shape blocks should be rare; once the queue is drained the legacy path is dead.

## Not in this MVP

- **Inline keyboard UI.** Telegram supports inline buttons; MVP stays with text actions for simplicity and portability across non-Telegram channels.

## Auto-Wiki vault ≠ your private memory

`_pending.md` lives in the **owner-facing** vault. The reviewer operates there — not in Claude's private auto-memory (`~/.claude/projects/.../memory/`). Never consult or write the private store during review; the two are kept deliberately separate.

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
  version: "1.0"
---

# review-pending

Single-owner queue processor for `$GINARR_VAULT_ROOT/wiki/_pending.md`. Low-confidence captures from the `capture` skill land there as blocks. This skill lets the owner process them one-by-one — promote to a real note, drop, skip, or edit — via the `/review` slash command (the primary trigger) or bare action words after a candidate has been presented.

## File layout

`_pending.md` = a Markdown template header (`# Pending review` + instructions) followed by zero or more candidate blocks separated by blank lines. Each block:

```
## <short title>
- ts: <UTC ISO>
- source: logs/YYYY/MM/YYYY-MM-DD.jsonl#ts=...
- proposed type: user | feedback | project | reference | decision
- proposed path: wiki/<subdir>/<snake_case>.md

<body / quote>
```

Blocks are delimited by `## ` at column 0. The template header is everything before the first `## ` heading — **preserve it on every rewrite.**

## Flow

1. **Read `_pending.md`.** Parse into `header` (text before first `## ` line) + `blocks[]` (each starting with `## `). If the file is missing, treat as empty queue.
2. **Empty queue?** → one line, no reaction: `В очереди ничего нет.` / `Queue is empty.` (match language). Stop.
3. **Top block?** → Present in the reply:
   - Candidate body (truncate to ~500 chars, append `…` and `(полный блок в _pending.md)` if longer).
   - `Предложенный путь: wiki/<dir>/<name>.md` (or English equivalent).
   - Inline prompt: `/review save | drop | skip | edit` (or: "ответь save/drop/skip/edit").
4. **On next action** (either `/review <action>` or a bare action word in a Telegram reply after the prompt):
   - `save` / `сохрани` / `да` → promote (below), remove the block, then present the next candidate.
   - `drop` / `удали` / `нет` → remove the block, present the next.
   - `skip` / `пропусти` / `потом` → rotate the block to the tail, present the next.
   - `edit` / `правь` → enter edit sub-flow.
   - Anything else → re-prompt once with the same candidate.

## Promote to real note

When the owner says save on a top block:

1. **Extract fields.** From the block:
   - `name` = basename of the proposed path without `.md`.
   - `description` = the `##` title line.
   - `type` = from `- proposed type:` line.
   - `directory` = derived from the `- proposed path:` line (`wiki/<dir>/…`).
   - `source` = from `- source:` line.
   - `body` = everything after the bullet list, trimmed.
2. **Dedup.** `grep -rli "<name-core-word>" "$GINARR_VAULT_ROOT/wiki/"`. If a file in the same `type`'s directory covers the topic:
   - Read it. If compatible → merge (append a section to the body, bump `updated:`, keep `status` as is).
   - If contradictory → Conflict protocol (from the `capture` skill): keep both claims with dates, set `status: unconfirmed`, ask the owner before finalising. Do not remove the pending block until the conflict is resolved.
3. **No match.** `mkdir -p "$GINARR_VAULT_ROOT/wiki/<dir>/"`, then Write:
   ```yaml
   ---
   type: <type>
   name: <name>
   description: <title>
   created: <today UTC date>
   updated: <today UTC date>
   status: confirmed
   source: <source from the pending block>
   ---
   ```
   Body = the block body, verbatim.
4. **Remove the block from `_pending.md`.** Read → rewrite as `header + "\n\n" + join(remaining_blocks, "\n\n")` → Write. Never overwrite the header.
5. **Feedback:**
   - Telegram: 💾 reaction on the owner's `save` message (fallback 🧠 → 👌), then one short reply `Saved: wiki/<dir>/<file>.md`.
   - Terminal (no `<channel>` tag): same short line, no reaction.

## Edit sub-flow

1. Show the current fields (title, proposed type, proposed path, body).
2. Ask `Что меняем?` / `What should change?` — accept freeform natural-language edits:
   - "type → feedback" — change the frontmatter type (and therefore directory).
   - "путь → wiki/user/foo.md" — change the target filename.
   - "переформулируй body: …" — rewrite the body text.
   - Combinations are fine.
3. Apply to an in-memory copy. Show the updated fields as a preview and ask for confirmation (`применить? да/нет`).
4. **Confirm** → run the normal save flow with the edited fields (dedup, write note, remove block, feedback).
5. **Cancel** → leave the pending block unchanged, move to the next candidate.

Edits never persist into `_pending.md`. Either they land in `wiki/` (on confirm) or they are discarded (on cancel).

## Skip semantics

Skip = rotate to tail. The block is not lost — it moves behind the others in `_pending.md`. `/review` always operates on the top of the queue, so a skipped block gets a second look after everything behind it has cycled through.

Implementation: Read → move `blocks[0]` to the end of `blocks[]` → rewrite `header + "\n\n" + join(blocks, "\n\n")`.

## Dedup inside the queue

Before saving, scan the remaining pending blocks for a matching topic (same name core, same proposed type). If found, surface both and ask the owner which to keep. Do not silently merge queue blocks — that is the owner's call.

## Threshold-latch maintenance

`capture` sets a latch file `$GINARR_VAULT_ROOT/wiki/.pending_notified` when the queue crosses 5 candidates upward, so the owner is pinged once per crossing. Review is responsible for clearing the latch on the downward crossing:

- After any block removal (save, drop), count the remaining `## ` headings in `_pending.md`. If the count is **below 5** and `.pending_notified` exists → delete the latch. The next time the queue climbs back past 5, `capture` will re-notify.
- Skip (rotate to tail) does not change the count — no latch action needed.
- Edit that ends in save is just a save with an extra step; the same latch-clear rule applies.

## Write boundary

`review-pending` writes the vault — both `wiki/<type>/<file>.md` (new or merged) and `wiki/_pending.md` (block removal, rotation). Unlike `recall`, it is not read-only. All writes happen at the explicit direction of the owner; never auto-merge on ambiguity.

## Telegram reply shape

| Action | Reaction (best-effort) | Text reply |
|---|---|---|
| Candidate prompt | — | body + proposed path + action prompt |
| Save | 💾 (→ 🧠 → 👌) | `Saved: wiki/<dir>/<file>.md` |
| Drop | 👌 | — |
| Skip | 👌 | — |
| Edit (preview) | — | updated fields + confirm prompt |
| Edit (applied) | 💾 | `Saved: wiki/<dir>/<file>.md` |
| Conflict | — | both claims + question |
| Empty queue | — | one line |

Reactions attach to the owner's message carrying the action (their `/review save` reply). If Telegram rejects the emoji, fall back per the chain above.

## Not in this MVP

- **Threshold notification** (≥5 pending → proactive ping to the owner). Roadmap 3.3 sub-phase.
- **Inline keyboard UI.** Telegram supports inline buttons; MVP stays with text actions for simplicity and portability across non-Telegram channels.

## Ginarr vault ≠ your private memory

`_pending.md` lives in the **owner-facing** vault. The reviewer operates there — not in Claude's private auto-memory (`~/.claude/projects/.../memory/`). Never consult or write the private store during review; the two are kept deliberately separate.

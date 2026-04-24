---
name: capture
description: >
  Decide whether a user statement is worth persisting to the chat-memory
  vault and, if so, to which note type and file. Consult whenever the
  user states a fact about themselves, expresses a preference, gives
  feedback on how to work with them, makes a decision, or explicitly asks
  to remember. Do not trigger on purely operational questions, debugging
  sessions, code tasks, or one-off task requests — those are not memory.
metadata:
  project: Ginarr
  version: "1.0"
---

# capture

Triage each memorable statement into one of four paths: **auto-save**, **unconfirmed save**, **`_pending.md`**, or **ask-immediately**. Operate on the shared vault at `$GINARR_VAULT_ROOT/notes/` — this is the owner-facing store they see in Obsidian. It is **separate from your private per-session auto-memory**; do not confuse the two.

## Confidence triage (SPEC.v3)

| Confidence | Cue examples | Path |
|---|---|---|
| **High** | "remember X", "запомни Y", explicit feedback ("don't do Y"), factual claim about the owner, confirmed decision | **Auto-save silently.** `status: confirmed`. |
| **Medium** | Indirect preference, one-off choice, inferred fact | **Auto-save with `status: unconfirmed`.** Confirm lazily when the topic comes up again. |
| **Low / ambiguous** | Speculation, thinking out loud, idle reflection | **Append block to `notes/_pending.md`.** Do *not* create a file under `notes/<type>/`. Reviewed later via `/review`. |

## Always ask immediately (overrides triage)

Stop and ask the owner before writing when:

- The new claim **contradicts an existing note** (see Conflict protocol).
- The fact involves **external stakeholders** (other people, deadlines, commitments you might act on).
- The content **borders on sensitive data** (finances, health, credentials).

## Never save

- Ephemeral task / session state (what's running now, what you just did).
- Information trivially derivable from an existing note (dedup, not duplicate).
- Low-confidence hunches → those go to `_pending.md`, not a typed file.

## Note types → directories

| `type` in frontmatter | Directory | What goes there |
|---|---|---|
| `user` | `notes/user/` | Facts about the owner. ("speaks Russian and English", "has a dog named Rex") |
| `feedback` | `notes/feedback/` | Rules for how to work with the owner. ("don't summarize at the end", "plan docs stay in Russian") |
| `project` | `notes/projects/` | Ongoing initiatives with a lifecycle. ("marathon training — target Oct 2026") |
| `reference` | `notes/reference/` | Pointers to external systems / people / places. ("bugs tracked in Linear INGEST", "ob sync daemon lives in ~/OpenClaw") |
| `decision` | `notes/decisions/` | Point-in-time choices with rationale. ("chose Postgres over MySQL — need range types") |

Note the directory-name asymmetry: `projects/` / `decisions/` (plural dirs), `project` / `decision` in frontmatter (singular). SPEC convention.

## Workflow

1. **Classify.** Pick a confidence bucket and (if not low) a `type`.
2. **Always-ask overrides?** → Ask the owner inline; wait for their answer before acting.
3. **Never-save?** → Stop.
4. **Low-confidence?** → Append a block to `$GINARR_VAULT_ROOT/notes/_pending.md` (format below). Stop.
5. **High/medium:** derive a `snake_case` filename capturing the topic — **not** the event. Good: `dog_rex.md`, `language_preferences.md`, `marathon_training.md`. Bad: `2026-04-24_chat_about_dog.md`.
6. **Dedup — search before write.** Grep the whole `notes/` tree for the topic keyword (name, tag, subject). Use Bash: `grep -rli "<keyword>" "$GINARR_VAULT_ROOT/notes/"` plus variants.
7. **Existing match?** → Read it. Judge: compatible (merge into the body, update `updated:` date) vs. contradictory → Conflict protocol.
8. **No match?** → `mkdir -p "$GINARR_VAULT_ROOT/notes/<dir>/"` and Write a new file with full frontmatter (template below).
9. **Telegram feedback** (see below). Never echo the stored value in the reply.

## Frontmatter template

```yaml
---
type: user | feedback | project | reference | decision
name: dog_rex
description: user's dog — a border collie, 4 years old
created: 2026-04-24
updated: 2026-04-24
tags: [pet]                                    # optional
source: logs/2026/04/2026-04-24.jsonl#ts=2026-04-24T14:32:01Z..2026-04-24T14:32:01Z  # optional
status: confirmed                              # optional; default confirmed. Use unconfirmed for medium-confidence.
# supersedes: user/previous_note.md            # optional
---
```

- **Dates are UTC** (YYYY-MM-DD, no time component).
- `source` ranges are inclusive on both ends — for a single user message, `X..Y` with `X == Y == the message's ts` is fine. Read the `ts="…"` attribute from the `<channel>` tag in the triggering prompt when available; fall back to the current UTC ISO.
- For `feedback` and `project` notes, the body follows a fixed shape:
  ```
  Primary rule / fact / decision in one sentence.

  **Why:** the reason (past incident, constraint, stated preference).

  **How to apply:** when and where this guidance kicks in.
  ```
  For `user`, `reference`, `decision` — free-form prose, keep it terse.

## `_pending.md` block format

`$GINARR_VAULT_ROOT/notes/_pending.md` already contains the template at its top. Each low-confidence candidate is appended as a block separated by a blank line:

```
## <short title>
- ts: <UTC ISO>
- source: logs/YYYY/MM/YYYY-MM-DD.jsonl#ts=...
- proposed type: user | feedback | project | reference | decision
- proposed path: notes/<subdir>/<snake_case>.md

<body / quote>
```

Append via Read → rewrite with the new block appended → Write. Do not overwrite earlier candidates.

### Threshold notification (≥5 pending)

After any low-confidence append to `_pending.md`, count the `## ` headings in the file. Call that `N`.

- `N >= 5` **and** `$GINARR_VAULT_ROOT/notes/.pending_notified` does **not** exist → send one short Telegram message to the owner: `Накопилось N кандидатов в /review — разберёшь?` (match the owner's recent language; default to Russian). Then create `.pending_notified` so the ping does not repeat at every subsequent capture while the queue stays above the threshold.
- `N < 5` **and** `.pending_notified` exists → delete it. The flag is a latch — set once on the upward crossing of the threshold, cleared on the downward crossing.
- No Telegram context on the current turn (no `<channel>` tag) → skip the notification. Do not write to stdout; proactive pings only make sense against a chat.

Do not notify about individual high/medium-confidence saves — those surface via the 💾 reaction at save time. This notification is strictly for the `_pending.md` queue pressure.

## Conflict protocol

When updating an existing note and a new claim contradicts an existing claim:

1. **Do not overwrite.** Keep both claims in the body, each prefixed with the date it was recorded.
2. Set `status: unconfirmed` in frontmatter.
3. Ask the owner at the next natural break ("I have two conflicting notes about X — the old one says A, the new one says B. Which is right?").
4. When the owner resolves it, delete the losing claim and drop `unconfirmed`.

## Telegram feedback

The `<channel>` tag on the user prompt carries `chat_id` and `message_id`. Use them for the tools below.

- **High-confidence save** (`status: confirmed`) → call `mcp__plugin_telegram_telegram__react` with emoji **💾** on the originating message. No text reply about the save itself. If Telegram rejects the emoji, fall back to 🧠 then 👌.
- **Medium-confidence save** (`status: unconfirmed`) → react 💾 **and** send one short reply: `Saved as unconfirmed: notes/<type>/<file>.md` (path only; do not paraphrase the content).
- **Low-confidence (pending)** → no reaction, no reply. The `/review` flow surfaces it later.
- **Always-ask** → send a direct text question; wait for the answer; then apply the resulting path as above.

Never echo the saved value in the visible reply — the message itself would land in the log and defeat the point for sensitive captures.

## Filename discipline

- **One topic = one file.** Primary dedup mechanism.
- `snake_case.md` **is mandatory**, not stylistic. Without it, `dog_rex.md` vs. `dog-rex.md` would both exist and dedup would miss. Never use hyphens, spaces, or camelCase.
- Topic > event. Filename keys the *subject*, not when it was captured.

## Ginarr vault ≠ your private memory

`$GINARR_VAULT_ROOT/notes/` is the **owner-facing** vault, mirrored to their Obsidian client. Your private auto-memory under `~/.claude/projects/.../memory/` is a separate, Claude-only notebook. For memorable *owner-visible* facts, capture into the Ginarr vault. For meta-behaviour about how *you* should operate (skill conventions, tool quirks), stay in private memory. When in doubt, a fact about the human goes to the Ginarr vault.

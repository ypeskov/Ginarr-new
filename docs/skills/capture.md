# `capture` — write-side memory skill

The skill that decides whether a user statement is worth persisting to the chat-memory vault, and if so to which note type and file. First of the three SPEC.v3 memory skills (`capture` / `recall` / `review`).

## Source

- Skill: [`.claude/skills/capture/SKILL.md`](../../.claude/skills/capture/SKILL.md) — authoritative behaviour (LLM-facing).
- Data store: `$GINARR_VAULT_ROOT/notes/` — owner-facing Obsidian vault, see [`architecture.md`](../architecture.md).

## When it fires

The `description` field in the skill's frontmatter tells Claude Code when to load it. In short: a user turn that states a fact about themselves, expresses a preference, gives feedback on how to work with them, makes a decision, or explicitly asks to remember. Purely operational turns (debugging, code tasks, one-off requests) do not trigger it.

## Four paths

Triage by confidence, per SPEC.v3 §"Capture rules":

| Path | Trigger | Storage |
|---|---|---|
| **Auto-save** | High confidence (explicit remember, direct feedback, factual self-claim, confirmed decision) | `notes/<type>/<snake_case>.md` with `status: confirmed` |
| **Unconfirmed save** | Medium (indirect preference, one-off choice, inferred fact) | Same path, `status: unconfirmed` — reconfirmed lazily on next use |
| **`_pending.md`** | Low / ambiguous (speculation, thinking out loud) | Single block appended to `notes/_pending.md` |
| **Ask immediately** | Contradicts existing note, involves external stakeholders, or borders on sensitive data | No write until the owner answers |

## Note types and directory layout

| `type:` frontmatter | Directory | Example |
|---|---|---|
| `user` | `notes/user/` | Facts about the owner |
| `feedback` | `notes/feedback/` | How to work with the owner |
| `project` | `notes/projects/` | Ongoing initiatives |
| `reference` | `notes/reference/` | Pointers to external systems / people / places |
| `decision` | `notes/decisions/` | Point-in-time choices with rationale |

Directory-name asymmetry (`projects/decisions/` plural, `project/decision` singular in frontmatter) is SPEC convention. `reference/` was added here — the SPEC.v3 layout listed `reference` as a frontmatter type but omitted the matching directory; this is now `notes/reference/` and will be formalised in SPEC v4.

## Telegram side

- **High-confidence save** → 💾 reaction on the user's original message (via `mcp__plugin_telegram_telegram__react`). No text reply. Fallback chain: 💾 → 🧠 → 👌.
- **Medium-confidence save** → 💾 reaction plus one short reply naming the file path. No paraphrase of the content.
- **Low-confidence (pending)** → silent.
- **Always-ask** → text question inline; action taken after owner's answer.

The reaction-only path for high-confidence saves is deliberate: it shows *that* something was captured without pushing a notification to the owner's phone and without re-leaking the content into the visible reply (which would itself end up in the log).

## Threshold notification

When a low-confidence block lands in `_pending.md` and the queue reaches 5 candidates, `capture` sends one proactive Telegram message: `Накопилось N кандидатов в /review — разберёшь?`. To avoid spamming every subsequent capture, the skill touches `$GINARR_VAULT_ROOT/notes/.pending_notified` as a latch; it fires again only after the queue has dropped back below 5 (cleared by `review-pending` on save/drop) and risen back above. Terminal-only turns (no `<channel>` tag) are silent — there is no chat to ping.

## Dedup

One topic = one file. Before every write the skill greps `$GINARR_VAULT_ROOT/notes/` for topic keywords and reads any matches. Duplicates become updates; contradictions trigger the conflict protocol (keep both claims with dates, `status: unconfirmed`, ask the owner).

## Relationship to `recall` and `review`

- `capture` writes.
- `recall` (next phase) reads `notes/` first, `logs/` second, before answering retrospective questions.
- `review` (Phase 3.3) walks `_pending.md` candidates with the owner.

## Relationship to Claude's private auto-memory

Ginarr's vault is the **owner-facing** store — visible in Obsidian, synced to all their devices. Claude's per-session auto-memory under `~/.claude/projects/.../memory/` is a private notebook that stays with Claude across sessions but is never shown to the user. Facts about the human go to the Ginarr vault; meta-conventions about how Claude should operate stay private. The skill makes this split explicit in its own body.

## Testing

`capture` is LLM-driven — there is no self-test harness. Walk it with representative prompts and verify the resulting vault state manually:

| Input | Expected |
|---|---|
| "Remember my dog's name is Rex." | New `notes/user/dog_rex.md`, `status: confirmed`, 💾 reaction. |
| "I think I might prefer darker colours in the UI." | New `notes/user/ui_colour_preference.md`, `status: unconfirmed`, 💾 + short reply. |
| "Maybe we should switch databases someday." | Block appended to `notes/_pending.md`, no file created, no reply. |
| "Don't summarise at the end of every response." | New `notes/feedback/response_style.md`, `status: confirmed`. Follows the `Primary rule / Why / How to apply` body shape. |
| "My dog's name is actually Max, not Rex." | Conflict detected in `notes/user/dog_rex.md`. Both claims kept with dates, `status: unconfirmed`, owner asked. |

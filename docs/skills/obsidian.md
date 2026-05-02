# `obsidian` — full vault access

Read, search, create, and edit notes anywhere in the owner's Obsidian vault at `~/obsidian-vaul/`. Distinct from the Ginarr memory layer, which targets only the `Auto-Wiki/` sub-vault.

## Source

- Skill: [`.claude/skills/obsidian/SKILL.md`](../../.claude/skills/obsidian/SKILL.md) — authoritative behaviour.
- Origin: copied from `~/OpenClaw/.claude/skills/obsidian/` (2026-04-24).
- Paired with: [`obsidian-structure`](obsidian-structure.md) — folder taxonomy and routing rules.

## Dependencies

- Claude Code standard tools (`Read`, `Edit`, `Write`, `Glob`, `Grep`).
- `ob sync --path ~/obsidian-vaul` — optional, to force-push changes to other devices after a write. The `ob` daemon lives in the OpenClaw repo; see `memory/reference_obsidian_sync.md` for the three knobs that need aligning.

## Scope and boundary vs. Ginarr memory

| Skill | Scope | Write path |
|---|---|---|
| `obsidian` | **Entire** vault — work, BG life, investments, résumé, personal | User decides folder (aided by `obsidian-structure`). |
| `capture` / `recall` | Only `Auto-Wiki/` sub-vault — long-term conversational memory | Automatic routing into `wiki/entities/<topic>/<slug>.md` (one page per entity, organised under topic folders `dating/`, `work/`, `tech/`, `health/`, `finance/`, `immigration/`, `owner/`, `family/`). |

Rule of thumb: facts about the owner that the assistant would want to recall in future chats → `capture`. Operational notes, shopping lists, recipes, work docs → `obsidian`.

## Rules enforced by the skill

- Never delete without explicit confirmation.
- Do not leak personal info into group Telegram chats. DMs only.
- Match existing note language (mostly Russian).
- Use `[[Note Name]]` for internal links.
- Run `ob sync` after writes.

## Known gaps

- The hard-coded folder list inside SKILL.md drifts from `obsidian-structure` (12 folders vs 16). Owner has flagged this; a unified taxonomy source is a future cleanup.

# `cross-link` — wikilink suggestion for the main vault

Suggests `[[wikilink]]` insertions in the owner's main Obsidian vault, pointing to existing entity pages under `Auto-Wiki/wiki/entities/` or to other main-vault files. Read-only by default; writes only on `--apply` AND after explicit owner confirmation in the conversation. Never creates a new page.

## Source

- Skill: [`.claude/skills/cross-link/SKILL.md`](../../.claude/skills/cross-link/SKILL.md) — authoritative behaviour.

## When to invoke

- Manual: `/cross-link [<path>]` or "пройдись cross-link по `<dir>`".
- After adding several new entity pages — main-vault notes that mention those entities need refreshing.
- After a slug rename — broken wikilinks need attention (this skill detects new mentions, does not rename existing ones).

## Args

| Trigger                       | Effect                                                                                  |
|-------------------------------|-----------------------------------------------------------------------------------------|
| `/cross-link`                 | Dry-run on `~/obsidian-vaul/` (excluding `Auto-Wiki/` and the standard exclusion list). |
| `/cross-link <path>`          | Dry-run on the given file or directory.                                                  |
| `/cross-link <path> --apply`  | Apply mode. **Even with `--apply`, the skill must show the dry-run diff and wait for explicit owner confirmation in the conversation before writing.** |

## What it touches

- Read: target markdown files in the main vault, plus the entity catalogue under `Auto-Wiki/wiki/entities/`.
- Write: the target files only — adds `[[<slug>|<text>]]` around plain-text mentions of known entity names. Nothing else, never any other file.

## What it skips

- `Auto-Wiki/` itself (entity pages already cross-link via `capture` / `ingest-and-weave`).
- `.git/`, `.obsidian/`, `node_modules/`, `__pycache__/`, `.venv/`, `dist/`, `build/`.
- `_pending.md`, `_tools/`, `_attachments/`, `attachments/` subtrees.
- The owner's own entity (`_owner.md`) is excluded from the matcher list — auto-linking «Юра» / «Yuriy» everywhere is noise, not signal.
- Matches inside code fences, inline code, frontmatter, or already-existing markdown / wiki links.
- Matchers shorter than 4 characters (too many false positives).
- Repeat occurrences of the same matcher in one file (Obsidian convention: link the first occurrence only).

## Where to look when something's off

| Symptom                                                | Likely cause                                                                                |
|--------------------------------------------------------|---------------------------------------------------------------------------------------------|
| Wrong link inserted (entity has the same name as a generic word) | Add a more-specific alias to the entity's `aliases:`, drop the generic one.       |
| Missed an obvious mention                              | The catalogue entry's `name` / `aliases:` did not include that rendering. Add it.            |
| `--apply` did nothing                                  | The skill waits for explicit conversational confirmation even when the flag is passed.       |
| Same file re-suggested links every run                 | Owner accepted some, declined others; declined matches stay flagged. Add per-page suppression manually if it matters. |

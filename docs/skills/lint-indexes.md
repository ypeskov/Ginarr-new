# `lint-indexes` — per-folder index maintainer

Walks a directory tree and ensures every folder has an `index.md` listing its files and subdirectories. Read-only by default; writes only on `--apply`. Never rewrites existing content — the audit trail stays clean.

## Source

- Skill: [`.claude/skills/lint-indexes/SKILL.md`](../../.claude/skills/lint-indexes/SKILL.md) — authoritative behaviour.

## When to invoke

- Manually: `/lint-indexes` (defaults to `$GINARR_VAULT_ROOT`, dry-run).
- After bulk imports of new notes when you want navigation refreshed.
- Before sharing a directory tree with a reader who needs an index to navigate by.

## Modes

| Trigger                             | Effect                                                                                                                   |
|-------------------------------------|--------------------------------------------------------------------------------------------------------------------------|
| `/lint-indexes`                     | Dry-run on `$GINARR_VAULT_ROOT`. Prints the proposed plan; no writes.                                                    |
| `/lint-indexes --apply`             | Apply on `$GINARR_VAULT_ROOT`. Creates missing `index.md`, appends missing entries.                                      |
| `/lint-indexes <path>`              | Dry-run on the given path.                                                                                               |
| `/lint-indexes <path> --apply`      | Apply on the given path. Outside `$GINARR_VAULT_ROOT` the skill must show the dry-run plan and wait for owner confirmation before writing. |

## What it touches

Only `index.md` files. Never any other file. In an existing `index.md`, only appends to a `## Recent additions` section at the end — never rewrites or reorders existing bullets.

## What it skips

`.git/`, `.obsidian/`, `node_modules/`, `__pycache__/`, `.venv/`, `dist/`, `build/`, `_pending.md`, `_tools/`, any `_attachments/` or `attachments/` subtree. Underscore-prefixed names otherwise are NOT excluded — they are commonly used as a sort-order hack (e.g. `_Dashboard/`, `__TODO.md`).

## Where to look when something's off

| Symptom                                | Likely cause                                                                  |
|----------------------------------------|-------------------------------------------------------------------------------|
| Proposed plan is way too big           | Root is broader than intended — narrow it: `/lint-indexes wiki/`.             |
| An entry was missed                    | Either it's under an excluded path, or the skill failed to detect it.         |
| Apply ran but `index.md` looks unchanged | Entries were already linked under different anchor text; check the existing index manually. |
| Owner-private file appeared in an index | Bug — the file should have been `_pending.md`, under `_tools/`, or under an `attachments/` / `_attachments/` subtree. |

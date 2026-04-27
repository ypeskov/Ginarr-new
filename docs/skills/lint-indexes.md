# `lint-indexes` — per-folder index maintainer

Walks a directory tree and rebuilds every folder's `index.md` from scratch as a pure navigation file: heading + list of files (with one-line descriptions from each file's first H1) + list of subdirectories (with descriptions from their `index.md`'s first H1). The whole `index.md` is regenerated each run; nothing inside it is preserved.

`index.md` is treated as fully linter-owned. Convention notes, cross-links, naming tables, intro paragraphs do **not** belong there — they get clobbered on the next run. Keep that material in separate `.md` files in the same folder; the linter will list it under `## Files` like any other entry.

## Source

- Skill: [`.claude/skills/lint-indexes/SKILL.md`](../../.claude/skills/lint-indexes/SKILL.md) — authoritative behaviour.
- Cron wrapper: [`.claude/scripts/lint-indexes.sh`](../scripts/lint-indexes.md) — every 6 hours, applies to `~/obsidian-vaul/`.

## When to invoke

- Manually: `/lint-indexes` (defaults to `$GINARR_VAULT_ROOT`, dry-run).
- After bulk imports of new notes when you want navigation refreshed.
- Scheduled (every 6 hours) — handled by the cron wrapper, no manual step needed.

## Modes

| Trigger                                        | Effect                                                                                                                   |
|------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------|
| `/lint-indexes`                                | Dry-run on `$GINARR_VAULT_ROOT`. Prints the proposed plan; no writes.                                                    |
| `/lint-indexes --apply`                        | Apply on `$GINARR_VAULT_ROOT`. Creates / overwrites every `index.md`.                                                    |
| `/lint-indexes <path>`                         | Dry-run on the given path.                                                                                               |
| `/lint-indexes <path> --apply`                 | Apply on the given path. Outside `$GINARR_VAULT_ROOT` the skill must show the dry-run plan and wait for owner confirmation before writing. |
| `/lint-indexes <path> --apply --cron`          | Non-interactive scheduled run. Used only by `.claude/scripts/lint-indexes.sh`. The crontab entry IS the standing authorization, so the interactive pause is skipped. |

## What it writes

Each `index.md` regenerates to exactly this shape:

```markdown
# <directory basename>

## Files

- [<file>](<file>) — <first H1, or empty>

## Subdirectories

- [<sub>/](<sub>/index.md)
```

Section names are always English (`## Files`, `## Subdirectories`) — matches the de facto convention across this vault. Empty sections are dropped. Entries are sorted alphabetically.

File entries carry a description pulled from the file's own first H1 (within its first 30 lines). If the file has no `# ` H1, the description is omitted — never fabricated. Subdirectory entries get **no** description: their `index.md` H1 is regenerated to the basename, which would be tautological, and there is no stable owner-editable surface for a custom description. Click into the subdir to see what it holds.

## What it skips

`.git/`, `.obsidian/`, `node_modules/`, `__pycache__/`, `.venv/`, `dist/`, `build/`, `_pending.md`, `_tools/`, any `_attachments/` or `attachments/` subtree. Underscore-prefixed names otherwise are NOT excluded — they are commonly used as a sort-order hack (e.g. `_Dashboard/`, `__TODO.md`).

When the walk root is outside `$GINARR_VAULT_ROOT`, the `Auto-Wiki/` subtree is also skipped — Auto-Wiki manages itself via `ingest-and-weave`. Direct invocation on Auto-Wiki (or anywhere under it) still descends normally.

## Where to look when something's off

| Symptom                                       | Likely cause                                                                                                |
|-----------------------------------------------|-------------------------------------------------------------------------------------------------------------|
| Proposed plan is way too big                  | Root is broader than intended — narrow it: `/lint-indexes wiki/`.                                           |
| A renamed file shows as removed + added       | Expected — the linter has no rename detection. Description for the new entry comes from its first H1.      |
| Custom prose disappeared from `index.md`      | Expected — `index.md` is fully linter-owned. Move the prose to a separate `.md` file in the same folder.   |
| An entry was force-removed                    | The file no longer exists on disk. Check `git log` or trash.                                                |
| Owner-private file appeared in an index       | Bug — the file should have been `_pending.md`, under `_tools/`, or under an `attachments/` / `_attachments/` subtree. |
| Cron wrapper applies without confirmation     | Expected — `--cron` mode treats the crontab entry as the owner's standing authorization for that root.     |

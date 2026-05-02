# `lint-indexes` — per-folder index maintainer

Walks a directory tree and keeps every folder's `index.md` in sync with the on-disk listing: heading + list of files (each with a one-line description) + list of subdirectories (each with a one-line description). The **listing skeleton** (which entries exist, what order) is rewritten from disk on every run; **descriptions are owner-curated and preserved across runs** — once a description is in `index.md`, the linter never overwrites it. New entries (just-added files / subdirs) get a description derived automatically the first time they appear.

Prose intros, convention notes, cross-link tables do **not** belong in `index.md` — only the heading + the two listing sections. Keep prose in a separate file in the same folder (convention: `_about.md`); the linter will list it under `## Files` like any other file.

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
| `/lint-indexes --apply`                        | Apply on `$GINARR_VAULT_ROOT`. Rewrites listings; descriptions for existing entries preserved verbatim.                  |
| `/lint-indexes <path>`                         | Dry-run on the given path.                                                                                               |
| `/lint-indexes <path> --apply`                 | Apply on the given path. Outside `$GINARR_VAULT_ROOT` the skill must show the dry-run plan and wait for owner confirmation before writing. |
| `/lint-indexes <path> --apply --cron`          | Non-interactive scheduled run. Used only by `.claude/scripts/lint-indexes.sh`. The crontab entry IS the standing authorization, so the interactive pause is skipped. |

## What it writes

Each `index.md` is rewritten to exactly this shape:

```markdown
# <directory basename>

## Files

- [<file>](<file>) — <description>

## Subdirectories

- [<sub>/](<sub>/index.md) — <description>
```

Section names are always English (`## Files`, `## Subdirectories`). Empty sections are dropped. Entries are sorted alphabetically (case-insensitive, locale-aware — `en_US.UTF-8` collation).

## How descriptions are derived

The linter parses the previous `index.md` and captures the existing description for every bullet line. On rewrite, those descriptions are carried forward verbatim — owner edits to descriptions survive any number of runs.

For **new** entries (in disk listing but not in the previous `index.md`), the linter derives a description automatically:

- **Files:** first `# ` H1 in the first 30 lines (skipped if tautological with the filename) → YAML frontmatter `description:` field → LLM-generated 1-line summary of the file content (≤80 chars). Frontmatter `title:` is ignored when it duplicates the filename.
- **Subdirs:** if `<sub>/_about.md` exists, its `# H1` (skipped if tautological with the directory name) → its first prose paragraph → first non-list paragraph from `<sub>/index.md` → LLM summary of the subdir's listing.

LLM derivation runs only on cache-miss (new entries). A cron pass over a stable vault produces zero LLM calls; the initial seed of an H1-less vault burns one call per file, then quiesces.

If derivation produces nothing meaningful (binary, empty, content-free), the entry renders without a description (just `- [name](<name>)`) — never fabricated.

## What it skips

`.git/`, `.obsidian/`, `node_modules/`, `__pycache__/`, `.venv/`, `dist/`, `build/`, `_pending.md`, `_tools/`, any `_attachments/` or `attachments/` subtree. Underscore-prefixed names otherwise are NOT excluded — they are commonly used as a sort-order hack (e.g. `_Dashboard/`, `__TODO.md`).

When the walk root is outside `$GINARR_VAULT_ROOT`, the `Auto-Wiki/` subtree is also skipped — Auto-Wiki manages itself via `ingest-and-weave`. Direct invocation on Auto-Wiki (or anywhere under it) still descends normally.

## Where to look when something's off

| Symptom                                       | Likely cause                                                                                                |
|-----------------------------------------------|-------------------------------------------------------------------------------------------------------------|
| Proposed plan is way too big                  | Root is broader than intended — narrow it: `/lint-indexes wiki/`.                                           |
| A renamed file shows as removed + added       | Expected — the linter has no rename detection. Description for the new entry is freshly derived.            |
| Custom prose disappeared from `index.md`      | Expected — only the heading + the two listing sections are kept. Move prose to a sibling `_about.md`.       |
| Description got rewritten on a cron pass      | Bug — descriptions are supposed to be preserved verbatim. Capture the diff and check if the bullet line was malformed (parser only matches `^- \[name\](target)( — desc)?`). |
| An entry was force-removed                    | The file no longer exists on disk. Check `git log` or trash.                                                |
| Owner-private file appeared in an index       | Bug — the file should have been `_pending.md`, under `_tools/`, or under an `attachments/` / `_attachments/` subtree. |
| Cron wrapper applies without confirmation     | Expected — `--cron` mode treats the crontab entry as the owner's standing authorization for that root.     |

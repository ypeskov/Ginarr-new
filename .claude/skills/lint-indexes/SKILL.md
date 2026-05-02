---
name: lint-indexes
description: >
  Walk a directory tree and keep every folder's `index.md` in sync with
  the on-disk listing: heading + list of files (each with a one-line
  description) + list of subdirectories (each with a one-line
  description). Listings are regenerated from disk every run; descriptions
  are PRESERVED across runs once written, so the owner can curate them by
  hand and the linter won't clobber them. New entries get a description
  derived from `# H1` → frontmatter `description:` → an LLM-generated
  one-line summary of the file (or, for subdirs, the folder's `_about.md`
  / first-paragraph fallback / LLM summary).
  Use when the user asks to "lint indexes", "обнови индексы", "пройдись
  по сейфу", or to fix `index.md` across a specific path. Default mode
  is dry-run; pass `--apply` to actually write. Outside the Auto-Wiki
  vault, dry-run is mandatory and `--apply` requires explicit owner
  confirmation in the conversation, except in `--cron` mode (which is
  the standing authorization installed via crontab).
metadata:
  project: Ginarr
  version: "3.0"
allowed-tools: Bash, Read, Write, Edit
---

# lint-indexes

Per-folder index maintainer. Walks any directory tree and keeps every folder's `index.md` in sync with the on-disk listing — every entry gets both a clickable Obsidian-style link **and** a one-line description, so an LLM (or a human) can decide whether a file or subfolder is worth opening without reading it.

The listing skeleton (which files / subdirs exist, what order they go in) is rewritten from disk on every run. **Descriptions are owner-curated and preserved across runs** — once a description is in `index.md`, the linter never overwrites it. New entries (just-added files, just-added subdirs) get a description derived automatically the first time they appear (see "Description derivation" below).

This is the navigation half of the Karpathy-style auto-wiki: the wiki content layer (entity pages) is built by `ingest-and-weave`; this skill just makes sure every folder is browsable from its parent via clickable links with useful summaries.

## Boundaries

- **Read scope**: every regular file under the root, to extract H1 / frontmatter / first-paragraph content for description derivation when needed.
- **Write scope**: only `index.md` files. Never any other file. Each `index.md` is rewritten from the directory's contents, **but descriptions for entries that already had one are preserved verbatim**.
- **Default mode**: dry-run. Prints a per-directory summary of what would change. Writes happen only when `--apply` is passed AND (when the root is outside the Auto-Wiki vault) the owner has explicitly confirmed (or `--cron` is set).
- **Idempotent**: a second run after `--apply` produces no further changes — listing is unchanged, descriptions are preserved, no diff.

## Inputs

- **`<root>`** (positional, optional) — directory to walk. Defaults to `$GINARR_VAULT_ROOT`.
- **`--apply`** (flag, optional) — actually write `index.md` files. Without it, dry-run.
- **`--cron`** (flag, optional) — non-interactive scheduled run. Implies "owner pre-authorized this root via crontab", so the cross-vault safety check (which otherwise pauses for conversation confirmation outside `$GINARR_VAULT_ROOT`) is skipped. Always combined with `--apply`. Used by `.claude/scripts/lint-indexes.sh`.

The owner can also pass intent in plain language: "lint indexes in `wiki/`", "обнови индексы в Auto-Wiki", "dry-run по основному сейфу". Parse the root and the apply flag from natural language when no explicit args are given. `--cron` is never inferred from natural language — it must be explicit, and only the cron wrapper passes it.

## `index.md` shape

Each `index.md` is rewritten to exactly this shape:

```markdown
# <directory basename>

## Files

- [<file.md>](<file.md>) — <description>
- [<file.ext>](<file.ext>) — <description>

## Subdirectories

- [<sub>/](<sub>/index.md) — <description>
```

Section names are always English: `## Files` and `## Subdirectories`. Existing indexes in this vault standardized on English long ago; the linter does not switch language and does not localize. If a directory has only files, omit `## Subdirectories`. If only subdirs, omit `## Files`. If empty, write just the `# <basename>` heading.

Entries are sorted alphabetically (case-insensitive, locale-aware — `en_US.UTF-8` collation, `locale.strxfrm`) within each section. Stable order keeps diffs across runs readable.

Filenames or subdirectory names containing spaces or special characters use angle-bracket Markdown link syntax: `[Имя с пробелами.md](<Имя с пробелами.md>) — описание`.

Every entry should have a description. The dash separator is `— ` (em-dash, space) for code-readability of parsing; if a description is genuinely unavailable (binary file, brand-new entry where derivation failed), render the entry as `- [name](<name>)` with no trailing dash.

## Description derivation

The linter must compute the **listing** (which entries exist, what order) on every run, but it must **not** clobber owner-curated descriptions. Logic per entry:

1. **Listing first.** Build the fresh listing from on-disk children. For each entry that already exists in the previous `index.md`, capture its existing description (everything after the first `— ` on that bullet line, trimmed). Carry that description forward verbatim into the new `index.md`.

2. **For new entries** (in disk listing but not in previous `index.md`), derive a description automatically in this priority order:

   **Files:**
   1. **First-line `# ` H1** — read first 30 lines of the target file, find first line matching `^# `, strip the marker, use the rest. Skip if the H1 is a verbatim copy of the filename basename (tautological).
   2. **YAML frontmatter `description:` field** — only if present and non-empty. Ignore `title:` if it is a verbatim copy of the filename basename — it adds nothing.
   3. **LLM-generated 1-line summary.** Read the file (capped at 4 KB or 100 lines, whichever is smaller), produce a single English or Russian-matching-content sentence under 80 characters describing what's in the file. No fabrication: if the file is empty, opaque (binary), or content-free, leave the description blank.

   **Subdirectories:**
   1. **`<sub>/_about.md` H1 or first prose paragraph** — if `_about.md` exists, prefer its `# H1` (skip if tautological), else first non-empty non-heading line.
   2. **`<sub>/index.md` first non-list paragraph** — if `_about.md` is absent and the subdir's `index.md` happens to have a prose paragraph between the `# H1` and the `## Files` / `## Subdirectories` headings, use it.
   3. **LLM-generated summary** — read the subdir's listing (top 10 file names + their descriptions if any) and produce a single sentence under 80 characters.

3. **Owner edits** to descriptions (in any `index.md`) survive any number of subsequent runs. The linter only touches a description when it is creating a brand-new entry that wasn't there before.

4. **Stale entries** (in previous `index.md` but no longer on disk) are dropped.

5. **Renames** look like delete + add to the linter; the description does not survive a rename. That's an acceptable cost.

LLM derivation is invoked only on cache-miss (new entries). Cron runs over a stable vault produce zero LLM calls because the listing has no new entries. Initial seed of a vault that has many H1-less files burns one LLM call per such file, then quiesces.

## Excluded paths

Hard-coded skip list (not descended into, not indexed, not written to):

- `.git/`, `.obsidian/`, `node_modules/`, `__pycache__/`, `.venv/`, `dist/`, `build/`
- `_pending.md` — capture skill's pending-review queue.
- `_tools/` — legacy vault-side tools directory, now migrated to the repo.
- `_attachments/` and `attachments/` subtrees — binary blobs, not navigable.

**The `Auto-Wiki/` subtree is also skipped when `<root>` is outside it.** Auto-Wiki manages itself via `ingest-and-weave`. When walking the broader vault (e.g. `~/obsidian-vaul/`), descend into everything except `Auto-Wiki/`. When `<root>` is `Auto-Wiki/` itself (or under it), this skip doesn't apply — direct invocation on Auto-Wiki still works.

**Underscore-prefixed names are otherwise NOT excluded.** Owners commonly use leading underscores as a sort-order hack — e.g. `_Dashboard/` to pin a folder to the top of Obsidian's file explorer, or `__TODO.md` to pin a file. Treat those as normal directories and files: index them, list them, and let them appear in their parent's index.

## Workflow

### 1. Resolve mode

```bash
ROOT="${ROOT:-$GINARR_VAULT_ROOT}"
[ -d "$ROOT" ] || { echo "root not a directory: $ROOT" >&2; exit 1; }
```

If `<root>` is anywhere outside `$GINARR_VAULT_ROOT` (i.e. the owner's main Obsidian vault or any other tree), set `OUTSIDE=1`.

- With `OUTSIDE=1` and `--apply` and **no** `--cron` → show the dry-run plan and wait for an explicit owner confirmation ("ok apply", "пиши", "go ahead") before any write.
- With `OUTSIDE=1` and `--apply --cron` → proceed immediately. The cron entry IS the owner's standing authorization for that root.

### 2. Walk the tree

For each directory under `<root>` (depth-first, excludes skipped):

a. **Parse existing `index.md`** (if any). Capture every bullet line under `## Files` and `## Subdirectories` as `(name, target, description)`. The description is the text after the first `— ` on the line, trimmed.

b. **List on-disk entries.** Files (any extension) and subdirectories. Exclude `index.md` itself from the listing — it lists everything else, not itself. Excludes from the skip list never appear.

c. **For each new on-disk entry** (no matching `(name, target)` in the parsed previous index), derive a description per "Description derivation" above. Cache the derived description in-memory for this run.

d. **Build the fresh `index.md`** using the listing + preserved descriptions for existing entries + freshly derived descriptions for new ones.

e. **Compare.** If the existing `index.md` is byte-for-byte identical to the fresh one, no-op. Otherwise mark for write.

### 3. Dry-run output

For each directory the skill would change, print one block:

```
<rel-path>/
  + create index.md (<N> entries, <D> with descriptions)
  OR
  ~ rewrite index.md: <N> entries (was <M>); <K> new entries derived
```

End with a tally: `would create N indexes, rewrite M indexes across K directories; derived L new descriptions`. Exit 0.

### 4. Apply mode

Same workflow as dry-run, but actually create / overwrite `index.md` files. Print the same per-directory line plus a final tally:

`created N indexes, rewrote M indexes across K directories; derived L new descriptions`.

## Cross-vault safety

If `<root>` resolves outside `$GINARR_VAULT_ROOT` AND `--cron` is NOT set:

- Default to dry-run regardless of `--apply`.
- Show the full dry-run plan in the reply.
- Wait for an explicit owner confirmation in the conversation before any write.

This guards against the skill clobbering the owner's personal Obsidian notes by surprise during interactive use. Inside `Auto-Wiki/`, no extra confirmation is needed beyond `--apply` — that tree is LLM-managed by design.

For scheduled runs (`--cron --apply`), the crontab entry installed by the operator IS the standing authorization, and the interactive pause is skipped. The cron wrapper at `.claude/scripts/lint-indexes.sh` is the only sanctioned caller of `--cron`.

Note: prose intros and convention notes do **not** belong in `index.md` — only the heading + the two listing sections. Keep prose in a separate file in the same folder (convention: `_about.md`); the linter will list it under `## Files` like any other file and a description for it can be filled in (manually or via LLM derivation).

## When to invoke

- User asks: "lint indexes", "fix index.md", "обнови индексы", "пройдись по сейфу", "rebuild navigation", "sync indexes".
- After a large batch import of new notes, when navigation needs to catch up.
- Manual via `/lint-indexes [<root>] [--apply]`.
- Scheduled via `.claude/scripts/lint-indexes.sh` (every 6 hours, applies to `~/obsidian-vaul/`).

## Don't

- Don't rewrite an existing description. Once a description is in `index.md` (manual edit or prior LLM derivation), it is the owner's. Carry it forward verbatim.
- Don't fabricate a description from thin air. If derivation produces nothing meaningful (binary file, empty file, no usable signal), leave the entry without a description (just `- [name](<name>)`).
- Don't rename or move files. The skill only writes `index.md`.
- Don't preserve fragments of an existing `index.md` other than the per-entry descriptions captured under `## Files` / `## Subdirectories`. Heading and section structure are regenerated. Prose between sections is dropped — owner has been warned (above).
- Don't delete `index.md`. If a directory was indexed and is now empty, the index file stays — reduce to just the heading.
- Don't write inside `_pending.md`, `_tools/`, or `_attachments/` — those are scratch / Obsidian internals.
- Don't index `attachments/` or `_attachments/` subtrees.
- Don't descend into `Auto-Wiki/` when the walk root is outside it.
- Don't write outside `$GINARR_VAULT_ROOT` without an explicit owner confirmation in the conversation (unless `--cron` is set).
- Don't infer `--cron` from natural language; only the cron wrapper script may pass it.

## See also

- `docs/skills/lint-indexes.md` — operator doc.
- `docs/scripts/lint-indexes.md` — cron wrapper reference.
- `docs/roadmap/auto-wiki.md` — section 2 of the auto-wiki roadmap.

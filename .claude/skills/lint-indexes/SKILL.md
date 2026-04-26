---
name: lint-indexes
description: >
  Walk a directory tree and refresh per-folder `index.md` files: list
  every file and subdirectory with a one-line H1 description, never
  delete or rewrite existing content, only append missing entries.
  Use when the user asks to "lint indexes", "rebuild the index",
  "обнови индексы", "пройдись по сейфу", or to fix `index.md` across
  a specific path. Default mode is dry-run; pass `--apply` to actually
  write. Outside the Auto-Wiki vault, dry-run is mandatory and
  `--apply` requires explicit owner confirmation in the conversation.
metadata:
  project: Ginarr
  version: "1.0"
allowed-tools: Bash, Read, Write, Edit
---

# lint-indexes

Per-folder index maintainer. Walks any directory tree and ensures every folder has an `index.md` listing its files and subdirectories. Read-only by default; appends missing entries on `--apply`. Never rewrites or reorders existing bullets — the audit trail of human vs. linter edits stays clean.

This is the navigation half of the Karpathy-style auto-wiki: the wiki content layer (entity pages) is built by `ingest-and-weave`; this skill just makes sure every folder is browsable from its parent via clickable Obsidian-style links.

## Boundaries

- **Read scope**: every regular file under the root, just to extract its first H1 line.
- **Write scope**: only `index.md` files. Never any other file. Never deletes or rewrites existing index content.
- **Default mode**: dry-run. Prints a per-directory summary of what would change. Writes happen only when `--apply` is passed AND (when the root is outside the Auto-Wiki vault) the owner has explicitly confirmed.
- **Idempotent**: a second run after `--apply` produces no further changes.

## Inputs

- **`<root>`** (positional, optional) — directory to walk. Defaults to `$GINARR_VAULT_ROOT`.
- **`--apply`** (flag, optional) — actually create missing `index.md` and append missing entries. Without it, dry-run.

The owner can also pass intent in plain language: "lint indexes in `wiki/`", "обнови индексы в Auto-Wiki", "dry-run по основному сейфу". Parse the root and the apply flag from natural language when no explicit args are given.

## Excluded paths

Hard-coded skip list (not descended into, not indexed, not written to):

- `.git/`, `.obsidian/`, `node_modules/`, `__pycache__/`, `.venv/`, `dist/`, `build/`
- `_pending.md` — capture skill's pending-review queue.
- `_tools/` — legacy vault-side tools directory (per SPEC.v3, now migrated to the repo).
- `_attachments/` and `attachments/` subtrees — binary blobs, not navigable.

**Underscore-prefixed names are otherwise NOT excluded.** Owners commonly use leading underscores as a sort-order hack — e.g. `_Dashboard/` to pin a folder to the top of Obsidian's file explorer, or `__TODO.md` to pin a file. Treat those as normal directories and files: index them, list them, and let them appear in their parent's index.

## Workflow

### 1. Resolve mode

```bash
ROOT="${ROOT:-$GINARR_VAULT_ROOT}"
[ -d "$ROOT" ] || { echo "root not a directory: $ROOT" >&2; exit 1; }
```

If `<root>` is anywhere outside `$GINARR_VAULT_ROOT` (i.e. the owner's main Obsidian vault or any other tree), set `OUTSIDE=1`. With `OUTSIDE=1` and `--apply`, **show the dry-run plan and wait for an explicit owner confirmation** ("ok apply", "пиши", "go ahead") before any write — even if `--apply` was passed on the command line.

### 2. Walk the tree

For each directory under `<root>` (depth-first, excludes skipped):

a. **List entries.** Files (any extension) and subdirectories. Exclude `index.md` itself from the listing — it lists everything else, not itself.

b. **Check for index.md.**
   - **Missing** → mark for creation. Build a default body (template below).
   - **Present** → Read it. Detect which entries are already linked. An entry `<name>` counts as "covered" if any of these patterns appears in the file:
     - `](<name>)` or `]( <name>)` — direct file link
     - `](<name>/` or `](<name>/index.md)` — subdir link
     - `<name>/` listed as inline plain text
     - the basename appears as a Markdown link label or wikilink

c. **Compute the gap.** `entries minus covered = missing`. If empty, nothing to do for this directory.

### 3. New `index.md` template

For directories that lack one:

```markdown
# <directory basename>

## Files

- [<file.md>](<file.md>) — <first H1, or empty>
- [<file.ext>](<file.ext>)

## Subdirectories

- [<sub>/](<sub>/index.md) — <first H1 of <sub>/index.md, or empty>
```

Drop empty sections. If a directory has only files, omit `## Subdirectories`. If only subdirs, omit `## Files`.

For **`<first H1>`**: read the first 30 lines of the target file, find the first line that starts with `# ` (single hash + space), strip the `# `, keep the rest. If absent or non-markdown, leave the description blank — never fabricate.

### 4. Existing `index.md` — append missing only

When `index.md` exists and has missing entries:

- **Never** rewrite or reorder existing bullets, headings, or prose.
- **Append** missing entries under a section `## Recent additions` at the end of the file. If that section already exists from a prior run, merge into it.
- Each appended bullet uses the same shape as in the new template.
- Preserve the existing file's trailing newline conventions.

The `## Recent additions` marker is the audit trail: anything under it was added by this skill, anything above it is human-curated.

### 5. Dry-run output

For each directory the skill would change, print one block:

```
<rel-path>/
  + create index.md (<N> entries)
  OR
  + append to index.md: <entry1>, <entry2>, ...
```

End with a tally: `would create N indexes, append M entries across K directories`. Exit 0.

### 6. Apply mode

Same workflow as dry-run, but actually create / Edit `index.md` files. Print the same per-directory line plus a final tally:

`created N indexes, appended M entries across K directories`.

## Cross-vault safety

If `<root>` resolves outside `$GINARR_VAULT_ROOT`:

- Default to dry-run regardless of `--apply`.
- Show the full dry-run plan in the reply.
- Wait for an explicit owner confirmation in the conversation before any write.

This guards against the skill writing into the owner's personal Obsidian notes by surprise. Inside `Auto-Wiki/`, no extra confirmation is needed beyond the `--apply` flag — that tree is LLM-managed by design.

## When to invoke

- User asks: "lint indexes", "fix index.md", "обнови индексы", "пройдись по сейфу", "rebuild navigation".
- After a large batch import of new notes, when navigation needs to catch up.
- Manual via `/lint-indexes [<root>] [--apply]`.

## Don't

- Don't fabricate descriptions. If a file has no `# ` H1 in its first 30 lines, leave the description empty.
- Don't rename or move files. The skill only edits `index.md`.
- Don't delete `index.md`. If a directory was indexed and is now empty, the index file stays — reduce to just the heading.
- Don't sort or re-order existing bullets in an existing `index.md`.
- Don't write inside `_pending.md`, `_tools/`, or `_attachments/` — those are scratch / Obsidian internals.
- Don't index `attachments/` or `_attachments/` subtrees.
- Don't write outside `$GINARR_VAULT_ROOT` without an explicit owner confirmation in the conversation, even when `--apply` was passed.

## See also

- `docs/skills/lint-indexes.md` — operator doc.
- `docs/roadmap/auto-wiki.md` — section 2 of the auto-wiki roadmap.

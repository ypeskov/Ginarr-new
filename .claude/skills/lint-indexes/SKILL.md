---
name: lint-indexes
description: >
  Walk a directory tree and rebuild every folder's `index.md` from
  scratch as a navigation file: heading + list of files (each with a
  one-line description from the file's first H1) + list of
  subdirectories (no descriptions). The whole `index.md` is regenerated
  each run; nothing inside it is preserved.
  Use when the user asks to "lint indexes", "обнови индексы",
  "пройдись по сейфу", or to fix `index.md` across a specific path.
  Default mode is dry-run; pass `--apply` to actually write. Outside
  the Auto-Wiki vault, dry-run is mandatory and `--apply` requires
  explicit owner confirmation in the conversation, except in `--cron`
  mode (which is the standing authorization installed via crontab).
metadata:
  project: Ginarr
  version: "2.0"
allowed-tools: Bash, Read, Write, Edit
---

# lint-indexes

Per-folder index maintainer. Walks any directory tree and rewrites every folder's `index.md` from scratch as a pure navigation file: a heading, a list of files, and a list of subdirectories — each entry annotated with a one-line description pulled from the target's first H1, so an LLM (or a human) can decide whether a file is worth opening without reading it.

`index.md` is treated as fully linter-owned. Anything beyond the heading and the two lists has no place there — convention notes, cross-links, naming tables, intro paragraphs all belong elsewhere (in dedicated `.md` files in the same folder, or in skills like `obsidian-structure`). Each run regenerates `index.md` end-to-end from the on-disk listing; whatever was previously inside it is replaced.

This is the navigation half of the Karpathy-style auto-wiki: the wiki content layer (entity pages) is built by `ingest-and-weave`; this skill just makes sure every folder is browsable from its parent via clickable Obsidian-style links and that the listings track adds, deletes, and renames.

## Boundaries

- **Read scope**: every regular file under the root, just to extract its first H1 line for descriptions.
- **Write scope**: only `index.md` files. Never any other file. Each `index.md` is fully regenerated from the directory's contents — no in-place editing of fragments.
- **Default mode**: dry-run. Prints a per-directory summary of what would change. Writes happen only when `--apply` is passed AND (when the root is outside the Auto-Wiki vault) the owner has explicitly confirmed (or `--cron` is set).
- **Idempotent**: a second run after `--apply` produces no further changes.

## Inputs

- **`<root>`** (positional, optional) — directory to walk. Defaults to `$GINARR_VAULT_ROOT`.
- **`--apply`** (flag, optional) — actually write `index.md` files. Without it, dry-run.
- **`--cron`** (flag, optional) — non-interactive scheduled run. Implies "owner pre-authorized this root via crontab", so the cross-vault safety check (which otherwise pauses for conversation confirmation outside `$GINARR_VAULT_ROOT`) is skipped. Always combined with `--apply`. Used by `.claude/scripts/lint-indexes.sh`.

The owner can also pass intent in plain language: "lint indexes in `wiki/`", "обнови индексы в Auto-Wiki", "dry-run по основному сейфу". Parse the root and the apply flag from natural language when no explicit args are given. `--cron` is never inferred from natural language — it must be explicit, and only the cron wrapper passes it.

## `index.md` shape

Each `index.md` is regenerated to exactly this shape:

```markdown
# <directory basename>

## Files

- [<file.md>](<file.md>) — <first H1 of file, or empty>
- [<file.ext>](<file.ext>)

## Subdirectories

- [<sub>/](<sub>/index.md)
```

Section names are always English: `## Files` and `## Subdirectories`. Existing indexes in this vault standardized on English long ago; the linter does not switch language and does not localize. If a directory has only files, omit `## Subdirectories`. If only subdirs, omit `## Files`. If empty, write just the `# <basename>` heading.

For **`<first H1>` on file entries**: read the first 30 lines of the target file, find the first line that starts with `# ` (single hash + space), strip the `# `, keep the rest. If absent or non-markdown (binary, no H1, etc.), omit the description (no trailing `— ...`) — never fabricate.

**Subdirectory entries get no description.** Always rendered as `- [<sub>/](<sub>/index.md)` with nothing after the link. The subdir's own `index.md` H1 is regenerated to `# <basename>` (tautological), and `index.md` is fully linter-owned, so there is no stable surface for an owner-curated description. Click into the subdir to see what it contains.

Entries are sorted alphabetically (case-insensitive, locale-aware) within each section. Stable order keeps diffs across runs readable.

Filenames containing spaces or special characters use angle-bracket Markdown link syntax: `[Имя с пробелами.md](<Имя с пробелами.md>)`. Same for subdirectory names with spaces.

## Excluded paths

Hard-coded skip list (not descended into, not indexed, not written to):

- `.git/`, `.obsidian/`, `node_modules/`, `__pycache__/`, `.venv/`, `dist/`, `build/`
- `_pending.md` — capture skill's pending-review queue.
- `_tools/` — legacy vault-side tools directory (per SPEC.v3, now migrated to the repo).
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

a. **List entries.** Files (any extension) and subdirectories. Exclude `index.md` itself from the listing — it lists everything else, not itself. Excludes from the skip list never appear.

b. **Build the fresh `index.md`** from the entries using the shape above.

c. **Compare.** If the existing `index.md` is byte-for-byte identical to the fresh one, no-op. Otherwise mark for write.

### 3. Dry-run output

For each directory the skill would change, print one block:

```
<rel-path>/
  + create index.md (<N> entries)
  OR
  ~ rewrite index.md: <N> entries (was <M>)
```

End with a tally: `would create N indexes, rewrite M indexes across K directories`. Exit 0.

### 4. Apply mode

Same workflow as dry-run, but actually create / overwrite `index.md` files. Print the same per-directory line plus a final tally:

`created N indexes, rewrote M indexes across K directories`.

## Cross-vault safety

If `<root>` resolves outside `$GINARR_VAULT_ROOT` AND `--cron` is NOT set:

- Default to dry-run regardless of `--apply`.
- Show the full dry-run plan in the reply.
- Wait for an explicit owner confirmation in the conversation before any write.

This guards against the skill clobbering the owner's personal Obsidian notes by surprise during interactive use. Inside `Auto-Wiki/`, no extra confirmation is needed beyond `--apply` — that tree is LLM-managed by design.

For scheduled runs (`--cron --apply`), the crontab entry installed by the operator IS the standing authorization, and the interactive pause is skipped. The cron wrapper at `.claude/scripts/lint-indexes.sh` is the only sanctioned caller of `--cron`.

Note: because `index.md` is fully linter-owned, any prose, convention notes, or cross-links the owner wants to keep in a folder must live in a **separate** `.md` file inside that folder (the linter will list it under `## Files` like any other file). Do not write such material into `index.md` — the next run will overwrite it.

## When to invoke

- User asks: "lint indexes", "fix index.md", "обнови индексы", "пройдись по сейфу", "rebuild navigation", "sync indexes".
- After a large batch import of new notes, when navigation needs to catch up.
- Manual via `/lint-indexes [<root>] [--apply]`.
- Scheduled via `.claude/scripts/lint-indexes.sh` (every 6 hours, applies to `~/obsidian-vaul/`).

## Don't

- Don't fabricate descriptions. If a file has no `# ` H1 in its first 30 lines, leave the description empty.
- Don't rename or move files. The skill only writes `index.md`.
- Don't try to preserve fragments of an existing `index.md`. Anything inside it that isn't reproducible from the directory listing is collateral — and will be overwritten. The owner has been warned (above): keep prose in separate files.
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

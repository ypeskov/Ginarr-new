---
name: cross-link
description: >
  Propose `[[wikilink]]` insertions in the owner's main Obsidian vault
  (`~/obsidian-vaul/` minus `Auto-Wiki/`) and within other main-vault
  notes, pointing to existing entity pages (`Auto-Wiki/wiki/entities/`)
  or to other main-vault files. Reads target files, finds plain-text
  mentions of known entity names or aliases that are not already
  wikilinked, prints a diff. Default mode is dry-run; pass `--apply`
  AND wait for explicit owner confirmation in the conversation before
  writing. Never creates a link to a page that does not yet exist.
  Use when the user asks to "обнови ссылки", "cross-link <path>",
  "пройдись cross-link по `<dir>`", or invokes `/cross-link [<path>]`.
metadata:
  project: Ginarr
  version: "1.0"
allowed-tools: Bash, Read, Write, Edit, Glob
---

# cross-link

Suggests `[[wikilink]]` insertions in the owner's main Obsidian vault to improve graph connectivity. Read-only by default — produces a diff. Writes only when the owner explicitly confirms in the conversation, even if `--apply` was passed.

This is the **connectivity assist** for the personal-notes layer of the vault. The Auto-Wiki entity pages already cross-link themselves (via `capture` and `ingest-and-weave`). This skill goes the other direction: takes notes the owner wrote himself in his Obsidian and suggests where they could link to entity pages or to each other.

## Boundaries

- **Read scope**: any markdown file in `~/obsidian-vaul/` (or a sub-path the owner names), plus `~/obsidian-vaul/Auto-Wiki/wiki/entities/` for the link target catalogue.
- **Write scope**: the targeted main-vault note(s), only on `--apply` AND only after explicit owner confirmation. Edits insert `[[<slug>]]` around plain-text mentions; nothing else.
- **Default mode**: dry-run. Prints proposed inserts as a diff. No writes.
- **No new pages.** Only links to entity pages that already exist. If a mention has no matching entity, the skill flags it but does not create one.

## Inputs

- **`<path>`** (positional, optional) — file or directory to scan. Defaults to `~/obsidian-vaul/` minus the `Auto-Wiki/` subtree.
- **`--apply`** (flag, optional) — actually insert the wikilinks. Even with `--apply`, the skill **must show the dry-run diff and wait for owner confirmation in the conversation** before writing.

The owner can also pass intent in plain language: "пройдись cross-link по Health/", "cross-link на Resume/projects.md", "обнови ссылки в BG/".

## Excluded paths

Same exclusions as `lint-indexes`:

- `.git/`, `.obsidian/`, `node_modules/`, `__pycache__/`, `.venv/`, `dist/`, `build/`
- `_pending.md`, `_tools/`, `_attachments/`, `attachments/` subtrees

Plus:

- `Auto-Wiki/` itself — entity pages already cross-link via `capture` / `ingest-and-weave`.

## Workflow

### 1. Build the entity catalogue

Glob `~/obsidian-vaul/Auto-Wiki/wiki/entities/*.md`. For each page, read frontmatter:

- `name` — the canonical original-script rendering.
- `aliases` — list of alternate renderings.
- Slug from filename.

Build a list of `(matcher_text, slug, page_path)` tuples — one per name and per alias.

Filter: drop entries shorter than 4 characters (too prone to false positives), drop entries that are common nouns. Keep proper nouns and full names.

**Owner exception.** Skip the owner's own entity (`_owner.md`) — auto-linking «Юра» / «Yuriy» everywhere produces noise rather than signal. The owner adds `[[_owner]]` himself if he wants it explicit.

### 2. Build the main-vault page catalogue (optional)

If the run scope includes main-vault-to-main-vault linking, also glob `~/obsidian-vaul/**/*.md` (excluding the entity catalogue and excluded paths). Match a basename or H1 to a target. This is more conservative — only suggest a link when the basename is a multi-word phrase (single-word filenames trigger too many spurious matches).

### 3. Walk targets

For each markdown file in the input scope:

a. Read the file.

b. For each `(matcher_text, target_slug, target_path)` from the catalogue:
   - Find every whole-word, case-sensitive match of `matcher_text` in the body.
   - For each match, check whether it is already inside `[[...]]` (skip), inside a code fence, inside a YAML frontmatter block, or inside an existing markdown link `[text](url)` (all skip).
   - For surviving matches, queue a proposed insertion: replace `<matcher_text>` with `[[<target_slug>|<matcher_text>]]` (Obsidian alias-link syntax — preserves the visible text exactly, links via the slug).

c. Avoid linking the **same matcher** multiple times in the same file: link only the first occurrence per page (Obsidian convention).

### 4. Output

For each file with proposed insertions, print one block:

```
<rel-path-to-file>:
  line N: «<context...><matcher_text><...context>» → [[<slug>|<matcher_text>]]
  line M: «...» → [[<slug>|...]]
```

End with a tally: `would link N occurrences across K files`.

### 5. Apply (only after owner confirmation)

When the owner confirms:

- Open each target file with the Edit tool.
- For each queued insertion (in reverse line order to keep line numbers stable), replace `<matcher_text>` with `[[<slug>|<matcher_text>]]`.
- Save.
- Print `linked N occurrences across K files`.

If the owner said `--apply` on the command line but hasn't separately confirmed in the conversation: **show the dry-run plan and ask explicitly**. Do not assume `--apply` is the confirmation.

## Don't

- **Don't create new entity pages.** This skill only links to pages that already exist.
- **Don't auto-link the owner.** Skip `_owner.md` from the matcher list.
- **Don't link inside code fences** (` ``` `), inline code (`` ` ``), frontmatter (between `---` markers), or existing markdown / wiki links.
- **Don't match short matchers.** Drop anything under 4 characters.
- **Don't link more than once per page per matcher.** First occurrence only — Obsidian's convention.
- **Don't write outside the input scope.** If the user named `BG/Авто/`, don't drift into `Health/`.
- **Don't run `--apply` without an explicit conversational confirmation** — even when the flag was passed.

## When to invoke

- Manual: `/cross-link [<path>]` or "пройдись cross-link по `<dir>`".
- After adding several new entity pages — the main-vault notes that mention those people / projects / places need refreshing.
- After a slug rename — wikilinks pointing to the old slug should be updated (manual sub-task; this skill helps detect new mentions, not rename existing ones).

## See also

- `docs/skills/cross-link.md` — operator doc.
- `docs/skills/lint-wiki.md` — finds *missing* cross-references inside `wiki/entities/`. Complementary scope.
- `docs/roadmap/auto-wiki.md` — section 5.

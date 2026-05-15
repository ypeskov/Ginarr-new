---
name: edit-topic
description: >
  Create, add to, remove from, move within, or list entries in a tiered
  topic manifest at `wiki/topics/<name>.md`. Use when the user wants to
  create a topic, curate Hot / Warm / Cold / Archive context, add an
  entity or main-vault path to a topic, remove stale material, rename
  a manifest, or change a path's load priority. Sibling write-side
  skill of `load-topic` (read-side).
metadata:
  project: Ginarr
  version: "2.0"
allowed-tools: Bash, Read, Write, Edit, Glob
---

# edit-topic

Manifest curator for `wiki/topics/`. Owner-action-driven write skill paired with the read-side `load-topic`. Operations: `create`, `add`, `move`, `remove`, `list`, `show`, `rename`. Validates that referenced paths exist; never silently writes broken references.

Topic manifests are the working-memory control plane. They decide which relevant files are loaded deeply, which are summarized, which are merely visible, and which stay archived. Tier choices are the lever that keeps `load-topic` lean as the vault grows.

## Layout

- **Write scope**: `$GINARR_VAULT_ROOT/wiki/topics/<name>.md` only.
- Filename convention: `snake_case.md` (CLAUDE.md ground rule). Examples: `dating.md`, `bg_residency.md` — never `Dating.md` or `BG Residency.md`.
- Each manifest tier may contain Auto-Wiki entity links and main-vault links. Bullets are typically of the form ``- `<path>` — <description>``; Markdown link form `[Name](path.md)` is also accepted.

## Manifest Shape

Every topic manifest uses this shape:

```markdown
---
topic: <name>
description: <one-line description>
---

# <name>

<one-paragraph topic summary>

## Hot

Loaded deeply by `load-topic` (with size preflight). Keep small: active working-set entities, current plans, and the few main-vault paths needed almost every session.

- `wiki/entities/<topic>/<slug>.md` — <why it is hot>

## Warm

Loaded as entity autoload capsules or main-vault summaries. Nearby context that is often useful but not always needed.

- `wiki/entities/<topic>/<slug>.md` — <why it matters>

## Cold

Listed in the ready-state report but not read by default. Known context the assistant should be aware exists.

- `~/obsidian-vaul/<Folder>/` — <what is there>

## Archive

Historical or closed material. Indexed and visible, never loaded by default.

- `wiki/entities/<topic>/_archive/<slug>.md` — <why it may matter later>

## Topic-specific notes

- <instruction or context that applies whenever this topic is loaded>
```

Tier meaning:

| Tier | Entity read mode | Main-vault read mode |
|------|------------------|----------------------|
| `Hot` | Size preflight in `load-topic`, then full read only if it fits the Hot budget; larger files load capsule + H2 outline and defer body. | Size preflight first; full file only if it fits the Hot budget; directories load `_about.md` and `index.md`. |
| `Warm` | Autoload capsule only: frontmatter through `<!-- ginarr:autoload-end -->`. | `_about.md`, `index.md`, or first useful summary block. |
| `Cold` | Manifest description / frontmatter `description:` only; no body read. | Manifest description / index entry only. |
| `Archive` | Skipped at startup. Read later only on explicit request or grounded suspicion from search/index evidence. | Skipped at startup. |

Tiers are a context budget, not truth labels. The same entity can be Hot in one topic and Cold in another.

Free-form extra sections (e.g. `## Skills`) are tolerated and passed through unchanged into the ready-state report under "Notes from manifest". Don't invent synonyms for the four tier names.

## Operations

| Form | Effect |
|------|--------|
| `/edit-topic list` | List all manifests and topic folders missing a manifest. |
| `/edit-topic show <name>` | Print the current manifest for review. |
| `/edit-topic create <name>` | Scaffold a tiered manifest at `wiki/topics/<name>.md`. |
| `/edit-topic add <name> <Hot\|Warm\|Cold\|Archive> <path>` | Add an entity-page or main-vault path to a specific tier. |
| `/edit-topic move <name> <path> <Hot\|Warm\|Cold\|Archive>` | Move an existing entry between tiers. |
| `/edit-topic remove <name> <path>` | Remove a path from whichever tier contains it. |
| `/edit-topic rename <old> <new>` | Rename a manifest. Updates filename and frontmatter `topic:` only. |

Natural-language equivalents: "добавь anfisa в dating как Hot", "demote anfisa to Warm", "move audrey_scam to Archive", "убери boo из tech".

## Workflow

### `create <name>`

1. Validate name: `snake_case`, ASCII, lowercase. No leading underscore (reserved for sentinels). No slashes or spaces.
2. Check `wiki/topics/<name>.md` doesn't already exist.
3. Optionally check `wiki/entities/<name>/` exists; if not, mention that entity-folder creation is separate and normally happens through `capture` when the first entity is created.
4. Write the manifest using the shape above. If the owner did not provide a description, use a terse placeholder: `TODO: describe this topic.`
5. Print the path and a hint to add entries via `/edit-topic add <name> Warm <path>` (or `Hot` for core entries).

### `add <name> <Tier> <path>`

1. Read `wiki/topics/<name>.md`. If missing, suggest `create <name>` first.
2. Validate `<Tier>` is exactly one of `Hot`, `Warm`, `Cold`, `Archive`.
3. Validate `<path>`:
   - If path starts with `wiki/entities/` or resolves under `$GINARR_VAULT_ROOT/wiki/entities/` → must exist as a Markdown file.
   - If path starts with `~/obsidian-vaul/` or is an absolute path under the main vault (`~/obsidian-vaul/` minus `Auto-Wiki/`) → must exist as a file or directory.
   - If path is relative, resolve it relative to the manifest file first, then against `$GINARR_VAULT_ROOT`, then against `~/obsidian-vaul/`; if still ambiguous, ask the owner.
4. Check the target is not already listed in any tier. If it is, use `move` instead.
5. Insert the bullet into the requested tier, preserving alphabetical order if the existing list is alphabetical, else append.
6. Render the path as a code-spanned bullet (``- `<path>` — <description>``) or as a Markdown link if the existing tier uses links — match the prevailing style.
7. Add a short suffix after ` — ` explaining why the path belongs in that tier. Derive it from frontmatter `description:`, the file's autoload capsule, H1, or an index entry. If no grounded description is available, omit the suffix rather than inventing.
8. Write the updated manifest.
9. Confirm: `Added <path> to <Tier> in wiki/topics/<name>.md`.

### `move <name> <path> <Tier>`

1. Read the manifest and find `<path>` in any tier.
2. Validate the new tier.
3. Remove the bullet from the old tier and insert the same bullet into the new tier.
4. Preserve the existing description suffix unless it contradicts the new tier; if it does, shorten to a neutral factual description.
5. Write the updated manifest.
6. Confirm: `Moved <path> from <OldTier> to <Tier> in wiki/topics/<name>.md`.

### `remove <name> <path>`

1. Read manifest. If `<path>` is not present in any tier, error: `<path> not in wiki/topics/<name>.md`.
2. Remove the bullet line from its tier.
3. Write the manifest.
4. Confirm: `Removed <path> from wiki/topics/<name>.md`.

### `rename <old> <new>`

1. Validate `<new>` doesn't already exist as a manifest.
2. Read `wiki/topics/<old>.md`.
3. Update `topic:` frontmatter from `<old>` to `<new>`.
4. Update `# <old>` heading to `# <new>` if present.
5. Write to `wiki/topics/<new>.md`.
6. Delete `wiki/topics/<old>.md`.
7. Warn the owner that:
   - `wiki/entities/<old>/` was NOT renamed (separate operation; entity-page `topics:` fields would need updating).
   - The taxonomy in `lint-wiki`, `capture`, `ingest-and-weave` (topic-resolver default lists) is NOT updated automatically — operator must edit by hand if the rename is permanent.

### `show <name>` and `list`

Read-only display operations; no writes. `list` should include manifests plus topic folders that have no manifest so gaps are visible.

## Migration: flat → tiered

If a manifest still uses the legacy flat sections `## Auto-Wiki entities` / `## Main Obsidian vault` (from edit-topic v1.0):

1. Parse the flat sections.
2. Move "Primary list" entity bullets → `## Hot`.
3. Move "Secondary (cross-tagged)" bullets → `## Warm`.
4. Move `## Main Obsidian vault` bullets → `## Cold` (directories) or `## Warm` (specific files with high reuse).
5. Existing `## Archive` section → keep as `## Archive`.
6. Preserve `## Topic-specific notes` verbatim.
7. Free sections like `## Skills` → keep at the bottom; `load-topic` passes them through.
8. Write the migrated manifest.

This is invoked implicitly when `/edit-topic add` or `/edit-topic move` is run against a flat manifest — migrate first, then apply the operation. Or explicitly via natural language ("migrate dating to tiered").

## Validation Rules

- Topic name: `snake_case`, ASCII, lowercase. No leading underscore. No slashes or spaces.
- Tier name: exactly `Hot`, `Warm`, `Cold`, or `Archive`.
- Entity path: must exist as `*.md` under `wiki/entities/`. `_about.md` and `index.md` are not entity entries.
- Main-vault path: must exist as file or directory under `~/obsidian-vaul/` (excluding the `Auto-Wiki/` sub-folder).
- No duplicate targets across tiers within a manifest.
- Frontmatter `topic:` must match the filename (`<name>.md`).
- Manifest body sections must use the canonical tier names. No synonyms (`Active`, `Reference`, `Historical`).

## Boundaries

- **Write scope**: `wiki/topics/<name>.md` only. Never touches:
  - entity pages (that's `capture` / `ingest-and-weave` territory)
  - main-vault notes (owner-direct or `obsidian` skill)
  - the `topics:` field of an entity
  - physical archive moves
- **Read scope**: `wiki/topics/`, plus path-existence checks and small excerpts from targets when deriving link descriptions.
- **No web access.**

## Don't

- **Don't keep backward compatibility with flat manifests** beyond the one-shot migration above. After migration, the contract is tiered.
- **Don't add a path that doesn't exist.** Broken references poison `load-topic` runs.
- **Don't duplicate a path across tiers.** Move it.
- **Don't infer that `Archive` means deleting or moving files.** It is a load policy.
- **Don't auto-rename entity folders.** Manifest rename is metadata-only.
- **Don't write to entity pages or main vault.**

## When to invoke

- After creating a new entity that belongs to an existing topic — `add <name> Warm <path>`, then promote to `Hot` only if part of the active working set.
- When introducing a new topic — `create <name>`, then let `capture` create the first entity, then `add` initial Hot/Warm entries.
- When a project closes or stale context grows — `move` entries to `Cold` or `Archive` so `load-topic` stays lean.
- When a session starts feeling bloated — demote nonessential entries rather than deleting useful navigation.
- After running a flat-format manifest through `add`/`move` once — confirm migration looks right.

## See also

- `docs/skills/edit-topic.md` — operator doc.
- `docs/skills/load-topic.md` — sibling read-side skill.
- `wiki/topics/_about.md` — manifest format note.

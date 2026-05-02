---
name: edit-topic
description: >
  Create, add to, remove from, or list entries in a topic manifest at
  `wiki/topics/<name>.md`. Use when the user wants to add a new entity
  or main-vault path to a topic ("добавь Anna в дейтинг манифест"),
  remove a stale entry, create a new topic, or rename one. Sibling
  write-side skill of `load-topic` (read-side).
metadata:
  project: Ginarr
  version: "1.0"
allowed-tools: Bash, Read, Write, Edit, Glob
---

# edit-topic

Manifest curator for `wiki/topics/`. Owner-action-driven write skill paired with the read-side `load-topic`. Operations: create, add, remove, list, rename. Validates that referenced paths exist; never silently writes broken references.

## Layout

- **Write scope**: `$GINARR_VAULT_ROOT/wiki/topics/<name>.md` only.
- Manifest format defined in `wiki/topics/_about.md` and demonstrated by existing manifests (`dating.md`, `work.md`, etc.).

## Operations

| Form                                                      | Effect                                                                                       |
|-----------------------------------------------------------|----------------------------------------------------------------------------------------------|
| `/edit-topic list`                                        | List all topics that have manifests, plus topic folders without manifests.                   |
| `/edit-topic show <name>`                                 | Print the current contents of `<name>.md` for review.                                        |
| `/edit-topic create <name>`                               | Scaffold a new manifest at `wiki/topics/<name>.md` from the template. Owner fills sections.  |
| `/edit-topic add <name> <path>`                           | Add `<path>` to the manifest (auto-routes to entities or main-vault section based on path).  |
| `/edit-topic remove <name> <path>`                        | Remove `<path>` from the manifest. Path must currently be present.                           |
| `/edit-topic rename <old> <new>`                          | Rename a manifest. Updates filename and frontmatter `topic:` field. Does NOT rename the entity folder under `wiki/entities/<old>/` — that's an owner-driven move with consequences. |

Natural-language equivalents: "добавь boo в tech manifest", "убери lina_okcupid из dating", "создай health-recovery как отдельный топик", etc.

## Workflow

### `create <name>`

1. Validate name: `snake_case`, ASCII-transliterated, lowercase.
2. Check `wiki/topics/<name>.md` doesn't already exist.
3. Optionally check `wiki/entities/<name>/` exists; if not, ask the owner whether to also `mkdir` the matching entity folder.
4. Write the file with this template:

```markdown
---
topic: <name>
description: <one-line description prompted from owner>
---

# <name>

<one-line summary>

## Auto-Wiki entities

All entities in `wiki/entities/<name>/`. Plus any entity whose `topics:` includes `<name>`.

Primary list:

- (no entities yet)

## Main Obsidian vault

- (no main-vault paths yet)

## Topic-specific notes

- (none yet)
```

5. Print the file path and a hint to add entries via `/edit-topic add`.

### `add <name> <path>`

1. Read `wiki/topics/<name>.md`. If missing, suggest `create <name>` first.
2. Validate `<path>`:
   - If path starts with `wiki/entities/` → it must exist as a file. Add to `## Auto-Wiki entities` § Primary list.
   - If path starts with `~/obsidian-vaul/` or is an absolute path under the main vault → check existence as file or directory. Add to `## Main Obsidian vault`.
   - Otherwise → ask the owner to disambiguate.
3. Check the path isn't already listed (no dups).
4. Insert the new bullet into the correct section, preserving alphabetical order if the existing list is alphabetical, else append.
5. For entity paths, optionally fetch the file's `# H1` line for the description suffix; for main-vault paths, ask the owner for a one-line description if not derivable.
6. Write the updated manifest.
7. Confirm: `Added <path> to wiki/topics/<name>.md`.

### `remove <name> <path>`

1. Read manifest. If `<path>` not present, error: `<path> not in wiki/topics/<name>.md`.
2. Remove the bullet line.
3. Write the manifest.
4. Confirm: `Removed <path> from wiki/topics/<name>.md`.

### `rename <old> <new>`

1. Validate `<new>` doesn't already exist as a manifest.
2. Read `wiki/topics/<old>.md`.
3. Update `topic:` frontmatter from `<old>` to `<new>`.
4. Update `# <old>` heading to `# <new>` if present.
5. Write to `wiki/topics/<new>.md`.
6. Delete `wiki/topics/<old>.md`.
7. **Warn the owner** that:
   - The entity folder `wiki/entities/<old>/` was NOT renamed — that's a separate operation with consequences (entity-page `topics:` fields would need updating, the `_about.md` references too).
   - The taxonomy in `lint-wiki` (`SKILL.md` lists recognised topics) and `capture` / `ingest-and-weave` (topic-resolver default lists) are NOT updated automatically — operator must edit those by hand if the rename is permanent.

### `show <name>` and `list`

Read-only display operations; no writes. Useful for owner spot-check before edits.

## Validation rules

- Topic name: `snake_case`, ASCII, lowercase, no spaces.
- Entity path: must exist as `*.md` under `wiki/entities/`.
- Main-vault path: must exist as file or directory under `~/obsidian-vaul/` (excluding `Auto-Wiki/` itself).
- No duplicate entries within a manifest.
- Frontmatter `topic:` must match the filename (`<name>.md`).

## Boundaries

- **Write scope**: `wiki/topics/<name>.md` only. Never touches:
  - entity pages (those are `capture` / `ingest-and-weave` territory)
  - main-vault notes (those are `obsidian` skill / owner-direct territory)
  - the `topics:` field of an entity (separate concern; owner edits frontmatter directly or runs `ingest-and-weave <slug>` to rebuild)
- **Read scope**: `wiki/topics/`, plus path-existence checks on the targets being added.
- **No web access.**

## Don't

- **Don't auto-rename entity folders.** Renaming `wiki/topics/dating.md` → `wiki/topics/relationships.md` does NOT rename `wiki/entities/dating/` — that requires an entity-folder migration, not a manifest edit. Warn the operator.
- **Don't add a path the doesn't exist.** Validation is mandatory; broken references in manifests poison `load-topic` runs.
- **Don't change the manifest frontmatter schema.** The `topic` and `description` keys are stable; future schema changes need a coordinated update with `load-topic`.
- **Don't write to entity pages or main vault.** This skill curates the manifest only.

## When to invoke

- After creating a new entity that fits an existing topic — add it to the manifest so future `load-topic <name>` finds it explicitly (folder-walk also catches it, but manifest-listed entries get richer descriptions).
- When introducing a new topic taxonomy item — `create <name>` to scaffold the manifest, then `mkdir wiki/entities/<name>/` and start placing entities.
- When pruning a stale prospect or closed initiative — `remove <name> <path>` keeps `load-topic` reports tidy.

## See also

- `docs/skills/edit-topic.md` — operator doc.
- `docs/skills/load-topic.md` — sibling read-side skill.
- `wiki/topics/_about.md` — manifest format.

# `edit-topic` — topic manifest curator

Owner-action-driven writer of `wiki/topics/<name>.md` manifests. Sibling of the read-side `load-topic`. Operations: list, show, create, add, remove, rename. Validates references so manifests stay clean.

## Source

- Skill: [`.claude/skills/edit-topic/SKILL.md`](../../.claude/skills/edit-topic/SKILL.md) — authoritative behaviour.

## Operations

| Form                                       | Effect                                                                            |
|--------------------------------------------|-----------------------------------------------------------------------------------|
| `/edit-topic list`                         | List all topics with manifests, plus topic folders missing a manifest.            |
| `/edit-topic show <name>`                  | Print the manifest's contents.                                                    |
| `/edit-topic create <name>`                | Scaffold a new manifest from the template.                                        |
| `/edit-topic add <name> <path>`            | Add an entity-page or main-vault path to the manifest.                            |
| `/edit-topic remove <name> <path>`         | Remove a path from the manifest.                                                  |
| `/edit-topic rename <old> <new>`           | Rename a manifest. Does NOT rename the entity folder — separate operation.        |

Natural-language equivalents: "добавь boo в tech", "убери lina_okcupid из dating", etc.

## Validation

- Topic name: `snake_case`, ASCII, lowercase.
- Entity path: must exist under `wiki/entities/`.
- Main-vault path: must exist under `~/obsidian-vaul/` (excluding Auto-Wiki).
- No duplicates within a manifest.
- Frontmatter `topic:` must match filename.

## What it touches

- Write scope: `wiki/topics/<name>.md` only.
- Read scope: existence checks on referenced paths.

## What it doesn't do

- Doesn't touch entity pages (use `capture` for that).
- Doesn't change `topics:` frontmatter on entities — that's an owner-direct edit or an `ingest-and-weave <slug>` rebuild.
- Doesn't rename entity folders or migrate existing entities — manifest rename is metadata-only.
- Doesn't update the topic taxonomy in `lint-wiki` / `capture` / `ingest-and-weave` SKILL.md files; if you add a new topic that needs to live in those skills' default lists, edit them manually.

## Where to look when something's off

| Symptom                                       | Likely cause                                                                                  |
|-----------------------------------------------|-----------------------------------------------------------------------------------------------|
| `<path> doesn't exist` on add                 | Typo, or entity is in a different topic folder than expected. `find $GINARR_VAULT_ROOT/wiki/entities/ -name "*.md" \| grep <slug>`.   |
| `<path> already in manifest` on add           | Already curated — nothing to do.                                                              |
| `<path> not in manifest` on remove            | Wrong path (verify with `show <name>`) or already removed.                                    |
| Renamed manifest but `load-topic` still refers to the old name | Topic taxonomy is hard-coded in several SKILL.md files (default lists in `capture`, `ingest-and-weave`, `lint-wiki`). Update by hand if the rename is permanent. |

## Companion skill

- `load-topic` — reads manifests and loads context. Sibling read-side skill.

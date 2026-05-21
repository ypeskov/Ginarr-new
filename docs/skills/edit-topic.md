# `edit-topic` — tiered topic manifest curator

Owner-action-driven writer of `wiki/topics/<name>.md` manifests. Sibling of the read-side `load-topic`. Operations: `list`, `show`, `create`, `add`, `move`, `remove`, `rename`. Validates references so manifests stay clean.

## Source

- Skill: [`.claude/skills/edit-topic/SKILL.md`](../../.claude/skills/edit-topic/SKILL.md) — authoritative behaviour.
- Reader: [`load-topic.md`](load-topic.md).

## Operations

| Form | Effect |
|------|--------|
| `/edit-topic list` | List all topics with manifests, plus topic folders missing a manifest. |
| `/edit-topic show <name>` | Print the manifest's contents. |
| `/edit-topic create <name>` | Scaffold a new tiered manifest. |
| `/edit-topic add <name> <Hot\|Warm\|Cold\|Archive> <path>` | Add an entity-page or main-vault path to a specific tier. |
| `/edit-topic move <name> <path> <Hot\|Warm\|Cold\|Archive>` | Move an existing entry between tiers. |
| `/edit-topic remove <name> <path>` | Remove a path from whichever tier contains it. |
| `/edit-topic rename <old> <new>` | Rename a manifest. Does NOT rename the entity folder — separate operation. |

Natural-language equivalents: "добавь anfisa в dating как Hot", "demote anfisa to Warm", "move audrey_scam to Archive", "убери boo из tech".

## Tier semantics

| Tier | What `load-topic` does |
|------|------------------------|
| `Hot` | Active working set. Loaded deeply (size preflight; full read if it fits the budget, otherwise capsule + outline). Keep small. |
| `Warm` | Nearby context. Loaded as the entity autoload capsule (frontmatter through `<!-- ginarr:autoload-end -->`) or as a main-vault summary block. |
| `Cold` | Visible in the report, not read. Use for known background. |
| `Archive` | Skipped at startup. Use for closed funnel, retired projects, etc. |

Tiers are a context budget, not truth labels. The same entity can be Hot in one topic and Cold in another.

## Manifest shape

```markdown
---
topic: <name>
description: <one-line description>
---

# <name>

<one-paragraph summary>

## Hot
- [[<slug>]] — <why hot>

## Warm
- [[<slug>]] — <why warm>

## Cold
- [[<Folder>/index|<Folder>/]] — <what is there>

## Archive
- [[<archived_slug>]] — <historical context>

## Topic-specific notes
- <instruction or context that applies whenever this topic is loaded>
```

Bullet form rules:

- **Entity files** (`wiki/entities/.../<slug>.md`): `[[<slug>]]` — basenames under `wiki/entities/` are unique, so the short form resolves inside Obsidian. Fall back to `[[Auto-Wiki/wiki/entities/<topic>/<slug>|<slug>]]` only on collision (note the `Auto-Wiki/` prefix — the path is relative to the Obsidian vault root, not the Auto-Wiki sub-folder).
- **Main-vault files** (`~/obsidian-vaul/<Folder>/<file>.md`, excluding `Auto-Wiki/`): `[[<file>]]` if unambiguous across the whole Obsidian vault; otherwise the path form `[[<Folder>/<file>|<file>]]`.
- **Main-vault folders**: `[[<Folder>/index|<Folder>/]]` — every main-vault folder owns an `index.md` (folder note), so the wikilink opens the folder note in Obsidian. The trailing slash in the display label signals "this is a folder."
- **Entity companion folders** (`wiki/entities/<topic>/<slug>/`): stay backticked — they have no folder note.

Free-form extra sections (`## Skills` in `fitness.md` is the canonical example) are passed through unchanged into the load-topic ready-state report.

## Validation

- Topic name: `snake_case`, ASCII, lowercase. No leading underscore. No slashes / spaces.
- Tier name: exactly `Hot`, `Warm`, `Cold`, or `Archive`. No synonyms.
- Entity path: must exist as `*.md` under `wiki/entities/`.
- Main-vault path: must exist under `~/obsidian-vaul/` (excluding `Auto-Wiki/`).
- All navigable bullets (entity files, main-vault files, main-vault folders with `index.md`) must render as `[[wikilinks]]`. Backticked paths are reserved for entity companion folders and folders genuinely missing a folder note.
- No duplicate paths across tiers within a manifest.
- Frontmatter `topic:` must match the filename.

## Migration: flat → tiered

If a manifest still uses the legacy flat sections `## Auto-Wiki entities` / `## Main Obsidian vault`, the first `add`/`move` invocation migrates it: Primary list → Hot, Secondary cross-tagged → Warm, main-vault paths → Cold (directories) or Warm (high-reuse single files), existing `## Archive` → Archive, free sections preserved.

Can also be invoked explicitly: "migrate dating to tiered".

## Migration: backtick paths → wikilinks (v2.1)

Older v2.0 manifests rendered bullets as `` `<path>` `` — those don't navigate inside Obsidian. The skill rewrites them on the next `add`/`move`/`remove` against the manifest:

- `` `wiki/entities/.../slug.md` `` → `[[slug]]`
- `` `~/obsidian-vaul/<Folder>/<file>.md` `` → `[[<file>]]` (or path form on collision)
- `` `~/obsidian-vaul/<Folder>/` `` → `[[<Folder>/index|<Folder>/]]` when `<Folder>/index.md` exists.

Entity companion folders and folders without a folder note stay backticked. Idempotent.

## What it touches

- Write scope: `wiki/topics/<name>.md` only.
- Read scope: existence checks on referenced paths, plus small excerpts (frontmatter `description:`, H1) when deriving link descriptions.

## What it doesn't do

- Doesn't touch entity pages (use `capture` for that).
- Doesn't change `topics:` frontmatter on entities — owner-direct edit or `ingest-and-weave <slug>` rebuild.
- Doesn't rename entity folders or migrate existing entities — manifest rename is metadata-only.
- Doesn't update the topic taxonomy in `lint-wiki` / `capture` / `ingest-and-weave` SKILL.md files; if you add a new topic that needs to live in those skills' default lists, edit them manually.

## Where to look when something's off

| Symptom | Likely cause |
|---------|--------------|
| `<path> doesn't exist` on add | Typo, or entity is in a different topic folder than expected. `find $GINARR_VAULT_ROOT/wiki/entities/ -name "*.md" \| grep <slug>`. |
| `<path> already in manifest` on add | Already curated. Use `move` if the tier is wrong. |
| `<path> not in manifest` on remove | Wrong path (verify with `show <name>`) or already removed. |
| Migration didn't happen on a flat manifest | Run any `add`/`move`/`migrate` to trigger it. |
| Renamed manifest but `load-topic` still refers to the old name | Topic taxonomy is hard-coded in several SKILL.md files (default lists in `capture`, `ingest-and-weave`, `lint-wiki`). Update by hand if the rename is permanent. |

## Companion skill

- `load-topic` — reads manifests and loads context. Sibling read-side skill.

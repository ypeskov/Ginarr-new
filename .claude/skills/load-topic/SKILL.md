---
name: load-topic
description: >
  Load a named Auto-Wiki topic into the current session according to
  the tiered manifest at `wiki/topics/<name>.md`. Reads Hot context
  deeply (with size preflight), Warm context as autoload capsules,
  Cold context as visible references, and Archive context only on
  demand. Use when the user asks to "load topic X", "загрузи дейтинг",
  "переключись на работу", or invokes `/load-topic <name>`.
metadata:
  project: Ginarr
  version: "2.0"
allowed-tools: Bash, Read, Glob
---

# load-topic

Topic-scoped context loader. Reads a tiered topic manifest and loads only the amount of Auto-Wiki / main-vault context justified by each entry's priority. This keeps session startup useful as the vault grows past the point where loading every status-active entity in a topic folder is affordable.

This is the **read-side** companion of `edit-topic` (which curates manifests). Together they implement per-topic working memory on top of Ginarr's file-based architecture — vendor-neutral, no Claude-Code internals (UUIDs, sessions, `--resume`) involved.

## Layout

- **Manifest** (read-only): `$GINARR_VAULT_ROOT/wiki/topics/<name>.md`
- **Entity pages**: `$GINARR_VAULT_ROOT/wiki/entities/**/<slug>.md`
- **Entity autoload boundary**: `<!-- ginarr:autoload-end -->`
- **Main vault paths**: paths under `~/obsidian-vaul/` (excluding `Auto-Wiki/`) listed in manifest tiers
- **Output**: no writes. The skill loads files into context and prints a ready-state report.

Topic and entity filenames are `snake_case.md` (CLAUDE.md ground rule). No spaces, no Title Case — `wiki/topics/dating.md`, `wiki/entities/dating/anfisa.md`, not `Dating.md`.

## Topic taxonomy

Closed-by-convention list (extendable via `edit-topic`): `auto`, `career`, `dating`, `family`, `finance`, `fitness`, `health`, `immigration`, `owner`, `tech`, `work`.

## Manifest Contract

The manifest is authoritative. When a manifest exists, **do not** auto-load every file in the matching topic folder. Folder scans are only for reporting uncurated candidates so the owner can promote them with `edit-topic`.

Required sections:

- `## Hot`
- `## Warm`
- `## Cold`
- `## Archive`
- `## Topic-specific notes`

Each tier section may contain links or path bullets pointing at Auto-Wiki entity files, main-vault files, or main-vault directories. Bullets are typically of the form:

```markdown
- `wiki/entities/<topic>/<slug>.md` — <description>
- `~/obsidian-vaul/<Folder>/<File>.md` — <description>
```

Markdown links (`[Name](path.md)`) are also accepted; strip optional `<...>` and resolve relative paths from the manifest file.

Do not support the legacy flat sections `## Auto-Wiki entities` / `## Main Obsidian vault` after migration. If a manifest still has them, report it and fall back to auto-discovery mode for that topic until the owner runs `edit-topic` migration.

## Tier Semantics

| Tier | Entity read mode | Main-vault read mode |
|------|------------------|----------------------|
| `Hot` | Size preflight first, then full top-level entity file only if it fits the Hot budget; otherwise capsule + H2 outline with body deferred. | Size preflight first, then full file only if it fits the Hot budget. For directories: read `_about.md` and `index.md`, then only files explicitly listed as Hot. |
| `Warm` | Autoload capsule only: frontmatter through `<!-- ginarr:autoload-end -->`. If the marker is missing, read only frontmatter, H1, first paragraph, and the first three H2 sections, then flag the file as needing a capsule. | `_about.md`, `index.md`, or the first useful summary block only. |
| `Cold` | No body read. Use manifest suffix or frontmatter `description:` for the ready-state report only. | No body read. Use manifest suffix or index entry only. |
| `Archive` | Not read at startup. Listed in the report as skipped historical context. Read later only on explicit request or grounded suspicion from search/index evidence. | Not read at startup. |

Global overrides:

- `wiki/entities/_owner.md` is loaded for every topic as a Warm-style autoload capsule (it is slim by design). Deep owner details live under `wiki/entities/_owner/` and are read only on explicit request.
- Any file under an `_archive/` folder is treated as `Archive` even if listed elsewhere. Report the mismatch.
- Any entity whose frontmatter `status:` is `archived`, `closed`, `done`, `dropped`, `retired`, `superseded`, `banned`, `unmatched`, `passed`, or `scam-closed` should not be read beyond the autoload capsule unless it is explicitly Hot and the current task needs the old detail. Report it as status-closed.
- Companion folders next to an entity file (e.g. `anfisa/` next to `anfisa.md`) are never auto-loaded. Read them only on explicit request or when a loaded file points to a specific companion file needed for the task.

## Autoload Capsule

Entity pages are split into a startup capsule and deeper notes:

```markdown
---
name: <Name>
description: <one-line description>
status: active
topics: [<topic>]
...
---

# <Name>

<one-line description>

## Brief

- <stable summary>

## Current State

- <live state>

## Open Questions

- <open question or "None.">

<!-- ginarr:autoload-end -->

## Facts

...
```

For Warm entities, read only through the marker. If the marker is missing, fall back to: frontmatter + H1 + first paragraph + first three H2 sections, and flag the file in the report as needing a capsule.

For Hot entities, always run the size preflight before deciding whether to full-read.

## Hot Size Preflight

Before reading any Hot file body, measure it with Bash:

```bash
wc -l -c "$path"
```

Default thresholds:

| Size | Startup read mode |
|------|-------------------|
| `<= 250` lines and `<= 50 KB` | Full read. |
| `251-1000` lines or `50-200 KB` | Read the autoload capsule plus an H2 outline; defer body sections. |
| `> 1000` lines or `> 200 KB` | Read the autoload capsule only, plus H2 outline if cheap; defer all body sections. |

If a topic has many Hot entries, be stricter: preserve the small active working set rather than full-reading every borderline file.

For deferred Hot files, gather startup shape with targeted commands instead of reading the full file:

```bash
sed -n '1,/<!-- ginarr:autoload-end -->/p' "$path"
rg -n '^## ' "$path"
```

If the autoload marker is missing on a Hot file, read only frontmatter, H1, first paragraph, and an H2 outline, then report that the Hot file needs a capsule.

## Workflow

### 1. Resolve topic name

Args: `<name>` (mandatory; snake_case). Match against:

1. Existing manifest: `wiki/topics/<name>.md`
2. Existing topic folder: `wiki/entities/<name>/`

If neither exists, fall through to **auto-discovery mode** (step 8). Do not load a whole folder by default in auto-discovery either.

### 2. Read and parse the manifest

Read `$GINARR_VAULT_ROOT/wiki/topics/<name>.md`. Parse:

- Frontmatter (`topic`, `description`)
- Topic summary below the H1
- `## Hot`, `## Warm`, `## Cold`, `## Archive`
- `## Topic-specific notes`
- Any other free section (e.g. `## Skills`) → preserved verbatim in the ready-state report under "Notes from manifest"

For each tier bullet, extract:

- display label
- target path
- optional description suffix after ` — `
- resolved path
- path kind: entity file, main-vault file, main-vault directory, missing

Missing paths are reported and skipped — do not fail the whole load.

If the manifest still uses the legacy flat sections `## Auto-Wiki entities` / `## Main Obsidian vault`, report it and treat every entity bullet as Warm, every main-vault bullet as Cold, until the owner migrates with `edit-topic`.

### 3. Load `_owner.md`

Read `$GINARR_VAULT_ROOT/wiki/entities/_owner.md` through the autoload marker (or, if marker missing, the slim portion: frontmatter + H1 + first paragraph + first three H2 sections). If missing entirely, report it but continue.

### 4. Load Hot

For each Hot entry:

- **Entity file**: run `wc -l -c` first. Full-read only if at or below the Hot threshold. If larger, read capsule plus H2 outline and note deferred body sections in the report.
- **Main-vault Markdown/text file**: run `wc -l -c` first. Full-read only if at or below the Hot threshold; if larger, read first meaningful summary + H2 outline.
- **Main-vault directory**: read `_about.md` and `index.md`; do not sample arbitrary recent files. If specific child files matter, list them explicitly as Hot bullets.

### 5. Load Warm

For each Warm entry:

- **Entity file**: read only the autoload capsule through `<!-- ginarr:autoload-end -->`. If marker missing, frontmatter + H1 + first paragraph + first three H2 sections; flag in report.
- **Main-vault file**: read only the autoload capsule if present, otherwise a small summary excerpt.
- **Main-vault directory**: read `_about.md` and `index.md` only.

### 6. Register Cold and Archive

For each Cold entry, keep only manifest label, target path, and description suffix. If the suffix is missing and an adjacent `index.md` has an entry description, use that. Do not read the target body.

For each Archive entry, keep only label, path, and suffix. Do not read at startup. During the later conversation, read an Archive target only when the owner asks directly or when search / index evidence makes it likely to answer the current question.

### 7. Report uncurated candidates

After manifest loading, scan the matching topic folder and cross-tagged entities to find top-level entity files not listed in any tier:

```bash
find "$GINARR_VAULT_ROOT/wiki/entities/<name>/" \
  -maxdepth 1 \
  -type f -name "*.md" \
  -not -name "_about.md" \
  -not -name "index.md"

grep -rl "^topics:.*\b<name>\b" "$GINARR_VAULT_ROOT/wiki/entities/" \
  | grep -v "/<name>/"
```

Only report candidate paths and frontmatter `description:` (cheap to obtain via `sed -n '1,/^---/p'`). Do not load their bodies. The owner can promote them via `edit-topic add <name> <Tier> <path>`.

### 8. Auto-discovery fallback

If no manifest exists:

1. Read entity frontmatter (`name`, `description`, `status`) and autoload capsules only.
2. Read relevant `index.md` files in `$GINARR_VAULT_ROOT/wiki/` and the main vault under `~/obsidian-vaul/`.
3. Propose a tiered manifest draft with a small Hot set (a handful of the highest-`status`/most-recent entities), broader Warm set (the rest of the folder), and main-vault directories as Cold or Warm.
4. Ask the owner whether to save it through `edit-topic create`. Do not write without confirmation.

### 9. Ready-state report

Print a structured summary:

```text
Topic: <name> — <description>

Hot loaded full (<N>):
  <path> — <description> [<status>]

Hot deferred (<D>):
  <path> — <description> [<status>, <lines> lines / <bytes> bytes; capsule + outline]

Warm capsules loaded (<M>):
  <path> — <description> [<status>]

Cold visible (<K>):
  <path> — <description>

Archive skipped (<A>):
  <path> — <description>

Uncurated candidates (<U>):
  <path> — <description>

Notes from manifest:
  <each bullet from ## Topic-specific notes and any free sections>
```

End with one line: `Ready to work on "<name>".`

## Boundaries

- **Read scope**: the named manifest, listed paths in its tiers, `_owner.md`, cheap folder / cross-tag scans for candidate reporting, and `index.md` files needed to describe Cold entries.
- **Write scope**: none. Manifest creation or tier changes go through `edit-topic`.
- **No web access.**
- **Vendor-neutral**: pure file reads. No Claude-Code session internals.

## Companion-file conventions

One contract: an entity is a single `.md` file at the top level of its topic folder. If the entity has long-form details, they go into a sibling sub-folder named after the entity slug. `load-topic` never auto-loads sibling folders.

- `wiki/entities/<topic>/<slug>.md` — entity (auto-loadable via manifest).
- `wiki/entities/<topic>/<slug>/` — per-entity detail folder. Contents (`<slug>_full.md`, `<slug>_log.md`, transcript dumps) are **not** auto-loaded; read on demand.
- `wiki/entities/_owner.md` + `wiki/entities/_owner/` — same pattern at the entities root.
- `wiki/entities/<topic>/_archive/` — closed-funnel files. Skipped by default; reachable as Archive entries or on explicit Read.

Don't confuse `wiki/entities/_owner/` (per-entity details for the slim `_owner.md`) with `wiki/entities/owner/` (a topic-folder for owner-related entities like `pfu_digitization`). Different things; the leading underscore matters.

## Don't

- **Don't load `wiki/_pending.md`** — that's review-flow territory. Use `/review` separately.
- **Don't load `wiki/_health/`** — those are `lint-wiki` reports, not topic content.
- **Don't load every matching topic-folder entry** when a manifest exists. Manifest is authoritative.
- **Don't auto-load `_archive/`** or companion folders at startup.
- **Don't use Cold as a hidden Warm.** Cold is map-only.
- **Don't write a manifest** from auto-discovery without owner confirmation.
- **Don't double-load `_owner.md`** — load once even if multiple paths reference it.
- **Don't silently reinterpret legacy flat manifest sections** as new contract. Report and degrade.

## When to invoke

- **Session start** for any topic-scoped work: open new Claude Code session, first turn `/load-topic <name>`.
- **Mid-session topic switch** is supported but blunt — the prior topic's context stays in the window. Cleaner: end session, open new one, `/load-topic <new-name>`.
- **Backfill of a new topic**: invoke once after `edit-topic create` to verify the manifest loads cleanly.
- **After heavy manifest edits** — verify the load shape.

## See also

- `docs/skills/load-topic.md` — operator doc.
- `docs/skills/edit-topic.md` — manifest curator (sibling skill).
- `wiki/topics/_about.md` — manifest format notes.
- `feedback_ginarr_vendor_neutral.md` (private memory) — why no `claude --resume` wrappers.

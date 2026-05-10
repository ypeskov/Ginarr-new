---
name: load-topic
description: >
  Load all entity pages and main-vault paths relevant to a named topic
  into the current session's context, so the assistant can work on that
  topic with full state. Reads the manifest at
  `wiki/topics/<name>.md` (curated owner list) and walks
  `wiki/entities/<name>/` plus any entity whose `topics:` includes the
  topic. Use when the user asks to "load topic X", "загрузи дейтинг",
  "переключись на работу", or invokes `/load-topic <name>`. Used at
  session start to set up topic-scoped working memory.
metadata:
  project: Ginarr
  version: "1.0"
allowed-tools: Bash, Read, Glob
---

# load-topic

Topic-scoped context loader. Reads a topic manifest and the relevant entity / main-vault content into the current Claude Code session, so the rest of the conversation can run with that topic's full state available without ad-hoc grep on every turn.

This is the **read-side** companion of `edit-topic` (which curates manifests). Together they implement per-topic working memory on top of Ginarr's file-based architecture — vendor-neutral, no Claude-Code internals (UUIDs, sessions, `--resume`) involved.

## Layout

- **Manifest** (read-only): `$GINARR_VAULT_ROOT/wiki/topics/<name>.md`
- **Entity folder** (read-only): `$GINARR_VAULT_ROOT/wiki/entities/<name>/` plus entities elsewhere with `topics:` containing `<name>`
- **Main vault paths**: as listed in the manifest's `## Main Obsidian vault` section
- **Output**: nothing written. Skill loads files into context and prints a summary.

## Topic taxonomy

Closed-by-convention list (extendable via `edit-topic`): `dating`, `work`, `tech`, `health`, `finance`, `immigration`, `owner`, `family`.

## Workflow

### 1. Resolve topic name

Args: `<name>` (mandatory). Match against:

1. Existing manifest: `wiki/topics/<name>.md`
2. Existing folder: `wiki/entities/<name>/`

If neither exists → fall through to **auto-discovery mode** (see step 5).

### 2. Read the manifest

Read `wiki/topics/<name>.md`. Parse:

- Frontmatter (`topic`, `description`).
- `## Auto-Wiki entities` — explicit entity-page paths.
- `## Main Obsidian vault` — paths in the main vault to read.
- `## Topic-specific notes` — instructions / context for the assistant.

If manifest is missing but folder exists → use folder contents as the entity list and skip main-vault paths.

### 3. Walk the entity folder

```bash
find "$GINARR_VAULT_ROOT/wiki/entities/<name>/" \
  -maxdepth 1 \
  -type f -name "*.md" \
  -not -name "_about.md" \
  -not -name "index.md"
```

Collect every entity at the **top level** of the topic folder. `-maxdepth 1` is the entire mechanism — any subfolder (per-entity detail folder, `_archive/`, anything else) is automatically skipped. No special-casing needed.

Combine with the manifest's explicit list (deduplicate). Manifest entries pointing into a subfolder (e.g. `_archive/` listed under `## Archive` for human navigation) are likewise ignored by the default walk; the operator browses them by explicit `Read` if needed.

### 4. Walk cross-tagged entities

Find entities elsewhere whose `topics:` frontmatter includes `<name>`:

```bash
grep -rl "^topics:.*${name}" "$GINARR_VAULT_ROOT/wiki/entities/" | grep -v "/${name}/"
```

Add to the load list.

### 5. Auto-discovery fallback (when no manifest and no folder)

If `<name>` doesn't match any existing topic, the skill:

1. Reads **all** entity-page descriptions (frontmatter `name` + `description` line + first paragraph) — at the current vault scale (~25-50 entities), this fits in context.
2. Asks the LLM (itself) which subset is plausibly relevant to the topic name.
3. Reads index.md files in the main vault for additional candidate paths.
4. Reports the auto-discovered list:
   `Manifest not found. Best-effort discovery for "<name>": <N> entities, <M> main-vault paths. Save as wiki/topics/<name>.md? [y/n]`
5. If owner confirms `y`, hand off to `edit-topic` to create the manifest.

### 6. Read everything (two-level)

For each path in the load list, decide read depth from the entity's `status:` frontmatter:

**Active statuses → full `Read`:**

`opener-drafted`, `opener-sent`, `opener-pending`, `in-conversation`, `met`, `dating`, `live`, `verified-real`, `active`, `live-channel`.

**Non-active or missing status → summary read** (`Read` with `limit: 30`):

Anything else — `paused`, `paused-no-initiation`, `idle`, `profile-only`, `just-matched`, no `status:` field at all (platform pages, reference pages). Captures frontmatter + first paragraph + first one or two H2 headers, which is enough to know what the entity is and decide whether to load it fully later.

If during the conversation the assistant needs the full body of a summary-mode entity (e.g. owner asks specifically about it), `Read` it without `limit:` on the spot.

**Special files:**

- `_owner.md` is loaded for every topic — root-level central self-page. Always full read of `_owner.md` (slim by design); the deep companion lives at `wiki/entities/_owner/_owner_full.md` and is **not** auto-loaded — read on explicit request.
- Main-vault path: if a single file, `Read` it; if a directory, list contents and read its `_about.md` and `index.md`, then sample the most-recently-modified files (top 5 by mtime).

### 7. Report

Print a structured summary:

```
Topic: <name> — <description from manifest>

Entities loaded full (<N>):
  <topic>/<slug>           — <one-line description>  [<status>]
  ...

Entities loaded as summary (<M>):
  <topic>/<slug>           — <one-line description>  [<status or none>]
  ...

Archive (skipped, <K> files):
  _archive/<slug>          — <one-line description>
  ...

Main vault paths loaded (<P>):
  ~/obsidian-vaul/<path>   — <one-line context>
  ...

Notes from manifest:
  <each bullet from ## Topic-specific notes>
```

End with a one-line ready signal: `Ready to work on "<name>".`

## Boundaries

- **Read scope**: `wiki/topics/<name>.md`, top-level `.md` files in `wiki/entities/<name>/` (no sub-folder recursion), paths listed in the manifest's `## Main Obsidian vault` section, plus `wiki/entities/_owner.md`.
- **Write scope**: none. The skill is read-only. Manifest creation goes through `edit-topic`.
- **No web access.**
- **Vendor-neutral**: no Claude-Code internals (no `claude --resume`, no `~/.claude/projects/`). Pure file reads.

## Companion-file conventions

One contract: an entity is a single `.md` file at the top level of its topic folder. If the entity has long-form details (chronologies, transcripts, deep notes), they go into a sibling sub-folder named after the entity slug. The skill loads only top-level `.md` files; any sub-folder — for any reason — is automatically skipped.

- `wiki/entities/<topic>/<slug>.md` — entity (auto-loaded).
- `wiki/entities/<topic>/<slug>/` — per-entity detail folder. Contents (e.g. `<slug>_full.md`, `<slug>_log.md`, transcript dumps) are **not** auto-loaded; read on demand.
- `wiki/entities/_owner.md` + `wiki/entities/_owner/` — same pattern at the entities root.
- `wiki/entities/<topic>/_archive/` — closed-funnel files (`closed`, `banned`, `unmatched`, `passed`, `passé`, `scam-closed`). Same `-maxdepth 1` skip; not a special case.

Don't confuse `wiki/entities/_owner/` (per-entity details for the slim `_owner.md`) with `wiki/entities/owner/` (a topic-folder for owner-related entities like `chair_search`, `pfu_digitization`). Different things; the leading underscore matters.

## Don't

- **Don't load `wiki/_pending.md`** — that's review-flow territory. If owner wants to see pending captures, they invoke `/review` separately.
- **Don't load `wiki/_health/`** — those are `lint-wiki` reports, not topic content.
- **Don't write the manifest** when running auto-discovery without owner confirmation. Auto-save would create stale manifests on every speculative `<name>` invocation.
- **Don't double-load `_owner.md`** — load once even if multiple paths reference it.
- **Don't auto-load anything in a sub-folder of a topic** — entities live at the top level only. Sub-folders (per-entity detail folders, `_archive/`, etc.) exist precisely to keep the default load slim. Reach for them only on explicit owner request or when the conversation needs the depth.

## When to invoke

- **Session start** for any topic-scoped work: open new Claude Code session, first turn `/load-topic <name>`.
- **Mid-session topic switch** is supported but blunt — the prior topic's context stays in the window. Cleaner: end session, open new one, `/load-topic <new-name>`.
- **Backfill of a new topic**: invoke once after `edit-topic --create` to verify the manifest loads cleanly.

## See also

- `docs/skills/load-topic.md` — operator doc.
- `docs/skills/edit-topic.md` — manifest curator (sibling skill).
- `wiki/topics/_about.md` — manifest format.
- `feedback_ginarr_vendor_neutral.md` (private memory) — why no `claude --resume` wrappers.

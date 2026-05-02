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

`find $GINARR_VAULT_ROOT/wiki/entities/<name>/ -name "*.md" -not -name "_about.md" -not -name "index.md"` — collect every entity in the topic's primary folder. Combine with the manifest's explicit list (deduplicate).

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

### 6. Read everything

For each path in the load list:

- Entity page: `Read` it.
- Main-vault path: if a single file, `Read` it; if a directory, list contents and read its `_about.md` and `index.md`, then sample the most-recently-modified files (top 5 by mtime).
- `_owner.md` is loaded for every topic — root-level central self-page.

### 7. Report

Print a structured summary:

```
Topic: <name> — <description from manifest>

Entities loaded (<N>):
  <topic>/<slug>           — <one-line description>
  <topic>/<slug>           — <one-line description>
  cross/<slug>             — secondary topic via `topics:` field
  ...

Main vault paths loaded (<M>):
  ~/obsidian-vaul/<path>   — <one-line context>
  ...

Notes from manifest:
  <each bullet from ## Topic-specific notes>
```

End with a one-line ready signal: `Ready to work on "<name>".`

## Boundaries

- **Read scope**: `wiki/topics/<name>.md`, `wiki/entities/**`, paths listed in the manifest's `## Main Obsidian vault` section, plus `_owner.md`.
- **Write scope**: none. The skill is read-only. Manifest creation goes through `edit-topic`.
- **No web access.**
- **Vendor-neutral**: no Claude-Code internals (no `claude --resume`, no `~/.claude/projects/`). Pure file reads.

## Don't

- **Don't load `wiki/_pending.md`** — that's review-flow territory. If owner wants to see pending captures, they invoke `/review` separately.
- **Don't load `wiki/_health/`** — those are `lint-wiki` reports, not topic content.
- **Don't write the manifest** when running auto-discovery without owner confirmation. Auto-save would create stale manifests on every speculative `<name>` invocation.
- **Don't double-load `_owner.md`** — load once even if multiple paths reference it.

## When to invoke

- **Session start** for any topic-scoped work: open new Claude Code session, first turn `/load-topic <name>`.
- **Mid-session topic switch** is supported but blunt — the prior topic's context stays in the window. Cleaner: end session, open new one, `/load-topic <new-name>`.
- **Backfill of a new topic**: invoke once after `edit-topic --create` to verify the manifest loads cleanly.

## See also

- `docs/skills/load-topic.md` — operator doc.
- `docs/skills/edit-topic.md` — manifest curator (sibling skill).
- `wiki/topics/_about.md` — manifest format.
- `feedback_ginarr_vendor_neutral.md` (private memory) — why no `claude --resume` wrappers.

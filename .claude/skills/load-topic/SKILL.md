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
  version: "2.2"
allowed-tools: Bash, Read, Glob
---

# load-topic

Read-side topic loader. Read a tiered manifest and load only the context justified by each entry's priority. Companion of `edit-topic` (write-side). Background, taxonomy, capsule structure example, troubleshooting: `docs/skills/load-topic.md` and `wiki/topics/_about.md`.

Paths:

- Manifest (read-only): `$GINARR_VAULT_ROOT/wiki/topics/<name>.md`
- Entity pages: `$GINARR_VAULT_ROOT/wiki/entities/**/<slug>.md`
- Autoload boundary: `<!-- ginarr:autoload-end -->`

Snake-case filenames. No writes — output is loaded files + a ready-state report.

## Tier semantics

| Tier | Entity read mode | Main-vault read mode |
|------|------------------|----------------------|
| `Hot` | Size preflight, then full file only if within Hot budget; else capsule + H2 outline, body deferred. | Size preflight, then full file only if within budget. Directories: `_about.md` + `index.md`, plus files explicitly listed Hot. |
| `Warm` | Autoload capsule only (frontmatter → marker). If marker missing: frontmatter + H1 + first paragraph + first 3 H2 sections; flag in report. | Capsule if present, else short summary; `_about.md` + `index.md` for dirs. |
| `Cold` | Manifest suffix or frontmatter `description:` only. No body read. | Manifest suffix or adjacent index entry only. |
| `Archive` | Skipped at startup. Read later only on explicit request or grounded suspicion. | Same. |

Global overrides:

- `wiki/entities/_owner.md` always loads as a Warm-style capsule. Deep details in `wiki/entities/_owner/` — explicit request only. Don't double-load if a manifest also references it.
- Any file under an `_archive/` folder is Archive even if listed elsewhere; report the mismatch.
- Statuses that downgrade to capsule-only even if Hot: `archived`, `closed`, `done`, `dropped`, `retired`, `superseded`, `banned`, `unmatched`, `passed`, `scam-closed`. Report as status-closed.
- Companion folders next to an entity (`<slug>/` next to `<slug>.md`) are never auto-loaded. Read children only on explicit request.
- `wiki/entities/_owner/` is the owner's per-entity detail folder (leading underscore); `wiki/entities/owner/` is the `owner` topic folder. Different things.

## Hot size preflight

Measure first:

```bash
wc -l -c "$path"
```

| Size | Mode |
|------|------|
| `<= 250` lines AND `<= 50 KB` | Full read. |
| `251-1000` lines OR `50-200 KB` | Capsule + H2 outline; body deferred. |
| `> 1000` lines OR `> 200 KB` | Capsule only, H2 outline if cheap. |

For deferred Hot files, gather shape without full read:

```bash
sed -n '1,/<!-- ginarr:autoload-end -->/p' "$path"
rg -n '^## ' "$path"
```

If marker missing on a Hot file: frontmatter + H1 + first paragraph + H2 outline; flag as needing a capsule.

When a topic has many Hot entries, be stricter rather than full-reading every borderline file.

## Workflow

### 1. Resolve topic name

Args: `<name>` (mandatory; snake_case). Match:

1. `wiki/topics/<name>.md`
2. `wiki/entities/<name>/`

Neither → step 8 (auto-discovery).

### 2. Parse manifest

Read `wiki/topics/<name>.md`. Parse frontmatter, H1 summary, the four tier sections, `## Topic-specific notes`, and any free section (e.g. `## Skills`) — preserved verbatim under "Notes from manifest" in the report.

Per bullet, extract: display label, target path, optional ` — description` suffix, resolved path, kind (entity file / main-vault file / main-vault dir / missing). Missing paths: report and skip.

Bullet forms accepted:

- **Wikilink** (v2.1+ contract, written by `edit-topic`):
  - Short form `- [[<basename>]] — <desc>`: resolve by globbing `wiki/entities/**/<basename>.md` first, then the rest of `~/obsidian-vaul/` (excluding `Auto-Wiki/`). Unique match → that's the target. Multiple matches → report ambiguity and skip. Zero matches → mark missing.
  - Path form `- [[<vault-relative-path>|<display>]] — <desc>`: resolve `<vault-relative-path>` (with `.md` appended) directly against the Obsidian vault root `~/obsidian-vaul/`. For Auto-Wiki entity files, that path starts with `Auto-Wiki/wiki/entities/...`. Use this form for both basename-colliding files and folder bullets.
  - **Folder bullets** look like `- [[<Folder>/index|<Folder>/]] — <desc>` (trailing slash in display label). Read the same way as a main-vault directory bullet — `_about.md` + `index.md` for Warm/Hot, description-only for Cold/Archive — except the target file is the resolved `<Folder>/index.md` itself.
- **Backticked path** (legacy v2.0, still supported): `` - `<path>` — <desc>``. Path may start with `wiki/entities/`, `~/obsidian-vaul/`, or be absolute. Directory paths (trailing `/`) resolve to main-vault dirs.

Legacy flat sections `## Auto-Wiki entities` / `## Main Obsidian vault`: report and degrade — entity bullets → Warm, main-vault bullets → Cold. Don't reinterpret silently.

### 3. Load `_owner.md`

Through the marker (or fallback as in Warm). Missing: report and continue.

### 4. Load Hot

Per entry:

- Entity file: preflight, then full or deferred per thresholds.
- Main-vault file: preflight, then full or first useful summary + H2 outline.
- Main-vault directory: `_about.md` + `index.md` only; don't sample recent files.

### 5. Load Warm

Per entry:

- Entity file: capsule through marker (or fallback).
- Main-vault file: capsule if present, else small summary excerpt.
- Main-vault directory: `_about.md` + `index.md`.

### 6. Register Cold and Archive

No body read for either. Cold: if suffix missing, use adjacent `index.md` entry. Archive: list label + path + suffix only.

### 7. Report uncurated candidates

```bash
find "$GINARR_VAULT_ROOT/wiki/entities/<name>/" \
  -maxdepth 1 -type f -name "*.md" \
  -not -name "_about.md" -not -name "index.md"

grep -rl "^topics:.*\b<name>\b" "$GINARR_VAULT_ROOT/wiki/entities/" \
  | grep -v "/<name>/"
```

Report only path + frontmatter `description:` (via `sed -n '1,/^---/p'`). No body read. Owner promotes via `edit-topic add`.

### 8. Auto-discovery fallback

No manifest:

1. Read entity frontmatter + capsules only.
2. Read relevant `wiki/` and main-vault `index.md` files.
3. Propose a tiered draft (small Hot from highest-status / most-recent, broader Warm, main-vault dirs Cold/Warm).
4. Ask before saving via `edit-topic create`. Don't write without confirmation.

### 9. Ready-state report

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

## Don't

- Don't load `wiki/_pending.md` (review territory) or `wiki/_health/` (lint reports).
- Don't auto-load every matching folder entry when a manifest exists.
- Don't auto-load `_archive/` or companion folders at startup.
- Don't use Cold as a hidden Warm — Cold is map-only.
- Don't write a manifest from auto-discovery without owner confirmation.
- Don't silently reinterpret legacy flat sections as the new contract.

## See also

- `docs/skills/load-topic.md` — operator doc (taxonomy, capsule example, troubleshooting, vendor-neutral rationale).
- `docs/skills/edit-topic.md` — write-side companion.
- `wiki/topics/_about.md` — manifest format reference.

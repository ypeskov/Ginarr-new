# `load-topic` — tiered topic context loader

Loads a topic into the current Claude Code session according to its **tiered manifest** at `wiki/topics/<name>.md`: Hot is loaded deeply (with size preflight), Warm as autoload capsules, Cold as visible references in the report, Archive as skipped historical context.

## Source

- Skill: [`.claude/skills/load-topic/SKILL.md`](../../.claude/skills/load-topic/SKILL.md) — authoritative behaviour.
- Manifest writer: [`edit-topic.md`](edit-topic.md).

## When to invoke

- **Session start** for topic-scoped work: open new session, `/load-topic dating` (or `work`, `tech`, etc.) as the first turn.
- **After creating or reshaping a topic manifest**.
- **Mid-session topic switch** is supported but blunt (prior context stays); for a clean switch, end the session and start a new one.

## Args

`/load-topic <name>` — required. `<name>` is the topic name (folder name under `wiki/entities/` and manifest filename under `wiki/topics/`).

## Topic taxonomy

Closed-by-convention list (extendable via `edit-topic`):

- `auto`, `career`, `dating`, `family`, `finance`, `fitness`, `health`, `immigration`, `owner`, `tech`, `work`

## Manifest contract

The manifest is authoritative. When a manifest exists, `load-topic` does not auto-load every matching folder entry — uncurated files appear in a separate "candidates" section of the report so the owner can promote them via `edit-topic`.

Required sections:

- `## Hot`
- `## Warm`
- `## Cold`
- `## Archive`
- `## Topic-specific notes`

Free-form extra sections (e.g. `## Skills` in `fitness.md`) are passed through verbatim into the ready-state report.

The legacy flat sections `## Auto-Wiki entities` and `## Main Obsidian vault` are not supported after migration — if encountered, the skill reports them and degrades to a conservative load (entity bullets → Warm, main-vault bullets → Cold).

## Tier semantics

| Tier | Entity read mode | Main-vault read mode |
|------|------------------|----------------------|
| `Hot` | Size preflight first; full read only when it fits the Hot budget, otherwise capsule plus H2 outline. | Size preflight first; full file only when it fits the Hot budget. Directories load `_about.md` and `index.md`. |
| `Warm` | Autoload capsule through `<!-- ginarr:autoload-end -->`. | Summary block, `_about.md`, or `index.md`. |
| `Cold` | Manifest / index description only; no body read. | Manifest / index description only. |
| `Archive` | Skipped at startup; read later only on explicit request or grounded suspicion from search/index evidence. | Skipped at startup. |

Global overrides:

- `_owner.md` is always loaded as a Warm-style autoload capsule (it is slim by design).
- `_archive/` folders and entity companion folders are never auto-loaded.
- Entities with closed statuses (`archived`, `closed`, `done`, `dropped`, `retired`, `superseded`, `banned`, `unmatched`, `passed`, `scam-closed`) are not read beyond the capsule even if Hot, and flagged as status-closed.

## Entity autoload capsule

Entity pages are split at:

```markdown
<!-- ginarr:autoload-end -->
```

The startup capsule is frontmatter, H1, and typically `## Brief`, `## Current State`, `## Open Questions`. Warm reads stop there. Hot reads may continue below the marker if the size preflight permits.

If a Warm entity is missing the marker, `load-topic` falls back to: frontmatter + H1 + first paragraph + first three H2 sections, and flags the file in the report as needing a capsule. Existing entity pages can be retrofitted incrementally — the convention is documented in [`wiki/entities/_about.md`](../../docs/architecture.md) (and reflected in `capture` / `ingest-and-weave` over time).

## Hot size preflight

Before reading any Hot file body, `load-topic` measures it:

```bash
wc -l -c "$path"
```

Default thresholds:

| Size | Startup read mode |
|------|-------------------|
| `<= 250` lines and `<= 50 KB` | Full read. |
| `251-1000` lines or `50-200 KB` | Capsule plus H2 outline; body deferred. |
| `> 1000` lines or `> 200 KB` | Capsule only, plus H2 outline if cheap; body deferred. |

Deferred Hot files are reported separately so the assistant knows the file is important but not fully loaded.

## Workflow at a glance

1. Resolve topic name.
2. Read and parse the tiered manifest.
3. Load `_owner.md` as a capsule.
4. Load Hot entries with size preflight.
5. Load Warm entries as capsules / summaries.
6. Register Cold and Archive entries without reading their bodies.
7. Scan for uncurated candidates (folder + cross-tag scans) and report them without loading bodies.
8. Print a ready-state report and the `Ready to work on "<name>"` signal.

If no manifest and no folder match `<name>`, the skill enters **auto-discovery mode**: reads entity descriptions and capsules, proposes a draft tiered manifest, asks the owner whether to save it via `edit-topic create`.

## Companion-file conventions

One contract: an entity is a single `.md` file at the top level of its topic folder. If it has long-form details, they go into a sibling sub-folder named after the entity slug. The skill never auto-loads sibling folders.

- `wiki/entities/<topic>/<slug>.md` — entity (auto-loadable via manifest).
- `wiki/entities/<topic>/<slug>/` — per-entity detail folder. Read on demand only.
- `wiki/entities/_owner.md` + `wiki/entities/_owner/` — same pattern at the entities root.
- `wiki/entities/<topic>/_archive/` — closed-funnel files; Archive-tier by default.

When the conversation needs the deep version, request it explicitly ("прочитай anfisa_full") — the assistant should `Read` it on the spot rather than re-loading the whole topic.

## What it touches

- Read-only on `wiki/topics/`, paths listed in manifest tiers, `wiki/entities/_owner.md`, plus cheap folder / cross-tag scans for candidate reporting.
- Never writes. Manifest creation goes through `edit-topic`.

## Why no Claude-Code session wrapper

Ginarr is vendor-neutral. Per-topic context loading lives at the **skill** layer, not at the runtime-session layer. New session + `/load-topic <name>` works the same on Claude Code, Junie, or OpenCode + oh-my-opencode. No UUID maps, no `claude --resume` wrappers, no coupling to `~/.claude/projects/`. See `feedback_ginarr_vendor_neutral.md` in private memory for the reasoning.

## Where to look when something's off

| Symptom | Likely cause |
|---------|--------------|
| `Manifest not found` for a known topic | Typo in topic name, or manifest deleted; check `ls $GINARR_VAULT_ROOT/wiki/topics/`. |
| Hot file loaded only as capsule | Size preflight exceeded the threshold; either accept and request body on demand, or move material into the companion `<slug>/` folder. |
| Warm entity missing a capsule (flagged in report) | Page needs a `<!-- ginarr:autoload-end -->` marker; add manually or wait for `capture` / `ingest-and-weave` to migrate it. |
| Uncurated candidate keeps appearing in the report | Promote it via `/edit-topic add <name> Warm <path>` or `Hot`. |
| Auto-discovery proposed irrelevant entities | Edit the suggested draft before confirming, or save and prune via `edit-topic`. |

## Companion skill

- `edit-topic` — creates / adds / moves / removes / renames entries in topic manifests. Sibling write-side skill.

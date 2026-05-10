# `load-topic` — topic-scoped context loader

Loads a topic's full state (entity pages from `wiki/entities/<topic>/`, cross-tagged entities, main-vault paths from the manifest) into the current Claude Code session, so the rest of the conversation runs with the topic's working memory in context.

## Source

- Skill: [`.claude/skills/load-topic/SKILL.md`](../../.claude/skills/load-topic/SKILL.md) — authoritative behaviour.
- Manifest format: `$GINARR_VAULT_ROOT/wiki/topics/<name>.md` (owner-curated).

## When to invoke

- **Session start** for topic-scoped work: open new session, `/load-topic dating` (or `work`, `tech`, etc.) as the first turn.
- **Mid-session topic switch** is supported but blunt (prior context stays); for a clean switch, end the session and start a new one.
- After running `edit-topic --create <name>` to verify the new manifest loads.

## Args

`/load-topic <name>` — required. `<name>` is the topic name (folder name under `wiki/entities/` and manifest filename under `wiki/topics/`).

## Topic taxonomy

Closed-by-convention list (extendable via `edit-topic`):

- `dating`, `work`, `tech`, `health`, `finance`, `immigration`, `owner`, `family`

## Workflow at a glance

1. Read manifest at `wiki/topics/<name>.md`.
2. Walk `wiki/entities/<name>/` with `find -maxdepth 1` — top-level `.md` files only. Any sub-folder (per-entity detail folder, `_archive/`, anything else) is automatically skipped.
3. Find cross-tagged entities (`topics:` field includes `<name>`) elsewhere.
4. Read main-vault paths listed in the manifest.
5. Read `_owner.md` (always).
6. **Two-level read** — full `Read` for entities with an active `status:` (`opener-drafted`, `opener-sent`, `opener-pending`, `in-conversation`, `met`, `dating`, `live`, `verified-real`, `active`, `live-channel`); summary read (`Read` with `limit: 30`) for everything else, including pages without a `status:` field. The depth gating keeps the default load slim while still putting every relevant page on the radar.
7. Report loaded state, give a `Ready to work on "<name>"` signal.

If no manifest and no folder match `<name>`, the skill enters **auto-discovery mode**: reads all entity descriptions, asks the LLM which are plausibly relevant, asks the owner whether to save the result as a new manifest.

## Companion-file conventions

One contract: an entity is a single `.md` file at the top level of its topic folder. If it has long-form details, they go into a sibling sub-folder named after the entity slug. The skill loads only top-level `.md` files; any sub-folder is automatically skipped.

- `wiki/entities/<topic>/<slug>.md` — entity (auto-loaded).
- `wiki/entities/<topic>/<slug>/` — per-entity detail folder. Contents (`<slug>_full.md`, `<slug>_log.md`, transcript dumps) are not auto-loaded — read on demand.
- `wiki/entities/_owner.md` + `wiki/entities/_owner/` — same pattern at the entities root.
- `wiki/entities/<topic>/_archive/` — closed-funnel files (`closed`, `banned`, `unmatched`, `passed`, `passé`, `scam-closed`). Same `-maxdepth 1` skip; not a special case.

Don't confuse `wiki/entities/_owner/` (per-entity details for the slim `_owner.md`) with `wiki/entities/owner/` (a topic-folder for owner-related entities like `chair_search`, `pfu_digitization`). The leading underscore matters.

When the conversation needs the deep version, request it explicitly ("прочитай anfisa_full") — the assistant should `Read` it on the spot rather than re-loading the whole topic.

## What it touches

- Read-only on `wiki/topics/`, top-level `.md` files in `wiki/entities/<name>/` (no sub-folder recursion), the listed main-vault paths, plus `wiki/entities/_owner.md`.
- Never writes. Manifest creation goes through `edit-topic`.

## Why no Claude-Code session wrapper

Ginarr is vendor-neutral. Per-topic context loading lives at the **skill** layer, not at the runtime-session layer. New session + `/load-topic <name>` works the same on Claude Code, Junie, or OpenCode + oh-my-opencode. No UUID maps, no `claude --resume` wrappers, no coupling to `~/.claude/projects/`. See `feedback_ginarr_vendor_neutral.md` in private memory for the reasoning.

## Where to look when something's off

| Symptom                                       | Likely cause                                                                                  |
|-----------------------------------------------|-----------------------------------------------------------------------------------------------|
| `Manifest not found` for a known topic        | Typo in topic name, or manifest deleted; check `ls $GINARR_VAULT_ROOT/wiki/topics/`.          |
| Entity loaded twice                           | Listed both in manifest AND in the entity folder — dedup is automatic, but a stale manifest entry can be removed.       |
| Main-vault path read but not relevant         | Manifest is curated by hand; trim the `## Main Obsidian vault` list in `wiki/topics/<name>.md`. |
| Auto-discovery picked irrelevant entities     | Edit the suggested manifest before saving, or save and prune the list afterwards via `edit-topic`. |

## Companion skill

- `edit-topic` — creates / adds / removes / renames entries in topic manifests. Sibling write-side skill.

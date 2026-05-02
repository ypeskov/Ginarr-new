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
2. Walk `wiki/entities/<name>/` (primary folder).
3. Find cross-tagged entities (`topics:` field includes `<name>`) elsewhere.
4. Read main-vault paths listed in the manifest.
5. Read `_owner.md` (always).
6. Report loaded state, give a `Ready to work on "<name>"` signal.

If no manifest and no folder match `<name>`, the skill enters **auto-discovery mode**: reads all entity descriptions, asks the LLM which are plausibly relevant, asks the owner whether to save the result as a new manifest.

## What it touches

- Read-only on `wiki/topics/`, `wiki/entities/`, the listed main-vault paths.
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

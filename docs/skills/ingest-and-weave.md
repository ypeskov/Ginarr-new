# `ingest-and-weave` — entity-page weaver

Walks daily summaries built by `summarize-day` and updates per-entity pages under `wiki/entities/<topic>/`. One page per person, project, place, technology, or organization, addressed by primary topic folder + slug. Idempotent — re-running produces no further changes once a day has been ingested.

## Source

- Skill: [`.claude/skills/ingest-and-weave/SKILL.md`](../../.claude/skills/ingest-and-weave/SKILL.md) — authoritative behaviour.
- Cron launcher: `.claude/scripts/ingest-and-weave.sh`.

## When to invoke

- **Cron**: chained after `summarize-day` at 00:25 UTC. Picks up yesterday's UTC summary, weaves entities.
- **Manual**: `/ingest-and-weave [<date>|<range>|<entity>|now]` for backfill, repair, or urgent updates.

## Args

| Arg                          | Effect                                                                          |
|------------------------------|---------------------------------------------------------------------------------|
| (none)                       | Yesterday's UTC summary. (Cron default.)                                        |
| `<YYYY-MM-DD>`               | One specific day.                                                               |
| `<YYYY-MM-DD>..<YYYY-MM-DD>` | Date range, oldest first.                                                       |
| `now`                        | Today's summary if it exists; otherwise exits — never falls back to raw JSONL.  |
| `<entity-slug>`              | Rebuild that one entity from every known summary (for repair after rename or topic move). |

## Output

- `wiki/entities/<topic>/<slug>.md` per entity — created or updated.
  - `<topic>` = primary topic from the entity's `topics:` frontmatter (first element).
  - Topic folders: `dating/`, `work/`, `tech/`, `health/`, `finance/`, `immigration/`, `owner/`, `family/`.
- Console report per entity (`<topic>/<slug> — created/updated — <N> new facts`).
- Final tally: `processed N day(s); created M entity(ies) across <K> topic folders, updated J`.
- Topic-uncertainty warnings as a separate block when an entity's primary topic could not be resolved with confidence.

## What it touches

Only `wiki/entities/<topic>/<slug>.md`. Never:

- `wiki/entities/_owner.md` (capture-only)
- `wiki/entities/_about.md` or `wiki/entities/index.md` (lint-indexes / manual)
- the entities root (every new page must land in a topic folder)
- summaries, JSONL, or `wiki/topics/` (those belong to other skills)

## Topic resolution

When creating a new entity page, the skill picks the **primary topic** by:

1. Reading the bullets in the source summary that mentioned the entity.
2. Tallying co-mentioned existing entities' primary topics (mode wins).
3. Falling back to type-defaults: `person` → conversational context, `technology` → `tech`, `organization` → `work`, `place` → owner-context, `event` → event domain, `scam_persona` → `dating`.
4. If still unresolved, picking the most-likely guess and logging a warning for owner review.

Existing pages are **not** moved between topic folders by ingest — topic curation is owner-driven. Use the `<entity-slug>` rebuild path after a manual move or rename.

## Conflict handling

When a new claim contradicts an existing one, both facts stay in `## Facts` with their date anchors, and a `## Conflicts` section captures the disagreement. The owner resolves manually (delete the wrong fact and trim the Conflicts entry).

## Where to look when something's off

| Symptom                                          | Likely cause                                                                                                     |
|--------------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| Entity page has duplicate facts after re-running | The skill failed to detect the date anchor — check that bullets start with `[[YYYY-MM-DD]]`.                  |
| New entity created at entities root              | Bug — every new page must land in `wiki/entities/<topic>/`. Check the topic-resolver step in the run log.       |
| New entity created for the owner                 | Bug — the owner's own name should be filtered out.                                                               |
| Cron didn't fire on time                         | Check `.claude/scripts/logs/ingest-and-weave.log`; the chain only fires after `summarize-day` succeeds.          |
| Slug collision                                   | Two distinct entities mapped to the same slug. Rename one manually and add the other to the renamed entity's `aliases:` frontmatter. |
| Entity in the wrong topic folder                 | Move the file with `mv` (vault is not in git), bump `topics:` in frontmatter, then `ingest-and-weave <slug>` to rebuild references. |

## Schema

Entity frontmatter:

```yaml
---
name: <canonical name>
aliases: [<alt name>, ...]
type: <person|project|place|technology|organization|event|scam_persona>
topics: [<primary>, <secondary>, ...]
created: YYYY-MM-DD
updated: YYYY-MM-DD
related: [<other-slug>, ...]
---
```

The `topics:` field is mandatory. First element = folder location. The page lives at `wiki/entities/<topics[0]>/<slug>.md`.

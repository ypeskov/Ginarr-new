# `ingest-and-weave` — entity-page weaver

Walks daily summaries built by `summarize-day` and updates per-entity pages under `wiki/entities/`. One page per person, project, place, technology, or organization. Idempotent — re-running produces no further changes once a day has been ingested.

## Source

- Skill: [`.claude/skills/ingest-and-weave/SKILL.md`](../../.claude/skills/ingest-and-weave/SKILL.md) — authoritative behaviour.
- Cron launcher: `.claude/scripts/ingest-and-weave.sh` (planned in roadmap step 3.2).

## When to invoke

- **Cron**: chained after `summarize-day` at 00:15 UTC. Picks up yesterday's UTC summary, weaves entities.
- **Manual**: `/ingest-and-weave [<date>|<range>|<entity>|now]` for backfill, repair, or urgent updates.

## Args

| Arg                          | Effect                                                                          |
|------------------------------|---------------------------------------------------------------------------------|
| (none)                       | Yesterday's UTC summary. (Cron default.)                                        |
| `<YYYY-MM-DD>`               | One specific day.                                                               |
| `<YYYY-MM-DD>..<YYYY-MM-DD>` | Date range, oldest first.                                                       |
| `now`                        | Today's summary if it exists; otherwise exits — never falls back to raw JSONL.  |
| `<entity-slug>`              | Rebuild that one entity from every known summary (for repair).                  |

## Output

- `wiki/entities/<slug>.md` per entity — created or updated.
- Console report per entity (`<slug> — created/updated — <N> new facts`).
- Final tally: `processed N day(s); created M entity(ies), updated K`.

## What it touches

Only `wiki/entities/<slug>.md`. Never summaries, JSONL, or other `wiki/` subdirs.

## Conflict handling

When a new claim contradicts an existing one, both facts stay in `## Facts` with their date anchors, and a `## Conflicts` section captures the disagreement. The owner resolves manually (delete the wrong fact and trim the Conflicts entry).

## Where to look when something's off

| Symptom                                       | Likely cause                                                                                                     |
|-----------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| Entity page has duplicate facts after re-running | The skill failed to detect the date anchor — check that bullets start with `[[YYYY-MM-DD]]`.                  |
| New entity created for the owner              | Bug — the owner's own name should be filtered out.                                                               |
| Cron didn't fire on time                      | Check `.claude/scripts/logs/ingest-and-weave.log`; the chain only fires after `summarize-day` succeeds.          |
| Slug collision                                | Two distinct entities mapped to the same slug. Rename one manually and add the other to the renamed entity's `aliases:` frontmatter. |

## Migration

Roadmap step 3.4 migrates the existing `wiki/{decisions,feedback,user}/` content into `wiki/entities/` and rewrites the `capture` skill to write directly here. Until then, both layers coexist.

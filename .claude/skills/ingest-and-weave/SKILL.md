---
name: ingest-and-weave
description: >
  Maintain LLM-managed entity pages under `wiki/entities/<topic>/`: one
  page per person, project, place, technology, or organization, primary-
  topic-folder addressed and tagged with `topics:` for cross-cutting
  membership. Walks the daily summaries built by `summarize-day`,
  extracts mentioned entities, resolves their primary topic, and either
  creates a new page (with a short description and a date-anchored fact
  log) or appends new facts to an existing page. Idempotent — already-
  recorded facts are not duplicated; new claims that contradict existing
  claims get a conflict marker rather than silently overwriting. Use
  when the user asks to "обнови entity-страницы", "пройдись ingest-and-
  weave", or invokes `/ingest-and-weave [<date>|<range>|<entity>|now]`.
  Also runs from cron at 00:15 UTC chained after `summarize-day`.
metadata:
  project: Ginarr
  version: "2.0"
allowed-tools: Bash, Read, Write, Edit, Glob
---

# ingest-and-weave

Wiki maintainer for entity pages. Reads `summarize-day` output, weaves the entities mentioned across days into per-entity pages, builds the cross-link graph that the navigation indexes (from `lint-indexes`) make discoverable.

This is the **content half** of the Karpathy-style auto-wiki. The navigation half is `lint-indexes`. Together they keep the wiki self-maintaining: raw JSONL → daily summary → entity pages → folder indexes.

## Layout

- **Source** (read-only): `$GINARR_VAULT_ROOT/logs/summaries/YYYY/MM/<date>.md`
- **Output** (write-scope): `$GINARR_VAULT_ROOT/wiki/entities/<topic>/<slug>.md`
  - `<topic>` is the entity's **primary** topic — the first entry in its `topics:` frontmatter field, which also dictates the folder location
  - Slug: `snake_case`, ASCII-transliterated where possible (`Наталья` → `natalya`, `Open AI` → `open_ai`). Original-script name lives in frontmatter `name:`; alternative renderings in `aliases:`
  - Root-level files (`_owner.md`, `_about.md`, `index.md`) are off-limits to this skill — see the Boundaries section
- **Topic folders** (current taxonomy): `dating/`, `work/`, `tech/`, `health/`, `finance/`, `immigration/`, `owner/`, `family/`. The list is closed-by-convention but extensible — add a new folder + `_about.md` if a recurring cluster of entities does not fit any existing topic.

## Entity types

Recognised in frontmatter `type:`:

- `person` — humans (owner's contacts, family, colleagues, public figures)
- `project` — ongoing initiatives with a start/end (work projects, side projects, life projects)
- `place` — geographic locations (cities, neighbourhoods, restaurants, landmarks)
- `technology` — tools, frameworks, services
- `organization` — companies, institutions
- `event` — one-time occurrences with a date (medical procedures, trips, deadlines)
- `scam_persona` — suspected catfish / scam profiles encountered on dating platforms

The list is open — add new types when nothing fits, but prefer collapsing into existing types.

## Entity page format

```markdown
---
name: <canonical name, in original script>
aliases: [<alt name>, <transliteration>, <nickname>]
type: <person|project|place|technology|organization|event|scam_persona>
topics: [<primary-topic>, <secondary-topic>, ...]
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
related: [<other-slug>, <other-slug>]
---

# <name>

<one-line description in the language the entity is mostly discussed in>

## Facts

- [[<date>]] <fact, declarative, one line>
- [[<date>]] <fact mentioning [[<other-slug>]] inline>
- ...

## Conflicts

- [[<date>]] <claim A> ↔ [[<date>]] <claim B> — unresolved
```

- **`topics:` field** is mandatory for every entity page outside the entities root. First element = primary topic = folder location. Subsequent elements = secondary topics for cross-cutting membership (e.g. `topics: [dating, tech]` for the Boo dating app).
- **Date anchors** in `[[YYYY-MM-DD]]` are Obsidian wikilinks resolving to `logs/summaries/YYYY/MM/<date>.md`.
- **Facts** are dry, declarative, one line each — same style rules as `summarize-day` bullets, including per-bullet language matching (Russian / Ukrainian / English depending on the source conversation).
- **Conflicts** section is omitted when empty. Both contradicting facts stay in `## Facts` with their original date anchors; the conflict is also recorded under `## Conflicts` for explicit owner review.

## Workflow

### 1. Resolve scope

Args are parsed from the trigger (`/ingest-and-weave [...]` or natural language):

| Arg form                          | Meaning                                                                                           |
|-----------------------------------|---------------------------------------------------------------------------------------------------|
| (none)                            | Process the previous UTC day's summary. (Cron default.)                                           |
| `<YYYY-MM-DD>`                    | Process that specific day's summary. Re-ingestion is idempotent — same facts will not duplicate.  |
| `<YYYY-MM-DD>..<YYYY-MM-DD>`      | Date range, oldest first.                                                                         |
| `now`                             | Today's summary if it exists; otherwise exit with `today's summary not yet built` — never falls back to raw JSONL. |
| `<entity-slug>`                   | Rebuild that one entity from every known summary (slow; for repair after a slug rename, merge, or topic move). |

### 2. Read the summary

`$GINARR_VAULT_ROOT/logs/summaries/<year>/<month>/<date>.md`. If missing, print `summary not found for <date>` and exit 1 — this skill is a downstream consumer; the upstream is `summarize-day`.

### 3. Extract entities

Walk the summary structure:

- **`## People`** — primary source for `person` entities. Each comma-separated name is one candidate.
- **`## Topics` and `## Decisions`** — extract proper nouns and recurring named concepts. These commonly produce `place`, `project`, `technology`, `organization`, and `event` entities.
- **`## Files and paths`** — paths usually map to existing project entities. New project mentions can surface here when the owner started a new initiative.

For each candidate decide:

- Is this a named, persistent thing worth a page? → entity.
- Is this a one-off mention of a noun the owner is unlikely to revisit? → skip.
- Owner's own name? → skip. The owner does have an entity page (`wiki/entities/_owner.md`), but it is owned by the `capture` skill — never write to it from summary-derived runs. Summaries are by definition mostly about the owner; auto-routing every mention there would dump 50+ facts a day onto one page.

When in doubt, lean toward creating — entity pages are cheap to delete; missing entities slow down `recall`.

### 4. Resolve to slug and existing page

For each candidate:

- Generate slug: lowercase, ASCII-transliterated, `snake_case`.
- Search **recursively** for an existing page:
  - `find $GINARR_VAULT_ROOT/wiki/entities/ -name "<slug>.md"` — direct match in any subfolder
  - If no direct match, glob frontmatter `aliases:` across `wiki/entities/**/*.md` for the candidate name in any rendering
- If found → update path (entity already lives in some topic folder — keep it there)
- If not found → creation path (resolve target topic, see step 5)

### 5. Resolve primary topic (creation path only)

Decide the **primary topic** for a new entity:

1. **Read the surrounding bullets** in the summary — which `## Topics` / `## Decisions` cluster mentioned this entity?
2. **Tally co-mentioned entities' topics:** for each existing entity that appears in the same bullets, read its `topics:` frontmatter (first element). The mode of those primary topics is the strongest signal.
3. **Type-defaults** when co-mention signal is weak:
   - `person` → infer from conversational context (dating talk → `dating`, work talk → `work`, family talk → `family`)
   - `technology` → `tech` unless used inside another topic (Boo: `dating` primary, `tech` secondary)
   - `organization` → `work` unless explicitly otherwise (medical org → `health`)
   - `place` → owner-context (where he lives / works / receives care)
   - `event` → match the event's domain (medical → `health`, deal closed → `work`, trip → `owner` or domain of the trip)
   - `scam_persona` → `dating`
4. **Secondary topics:** include any non-primary topic that the entity genuinely participates in (Boo example: `dating` primary, `tech` secondary because the platform is also part of the tech stack).
5. **If still unresolved:** pick the most-likely topic, log a warning in the run report (`<slug> — topic uncertain, picked <topic>; owner please review`), and rely on `lint-wiki` to flag entities with thin topic-justification later.

### 6. Create or update

**Creation path**:
- Compute target path: `wiki/entities/<primary-topic>/<slug>.md`. Create the topic folder if it doesn't exist (rare; folders are pre-seeded).
- Write the file with the template above:
  - `name:` — original-script rendering as the owner uses it
  - `aliases:` — the slug plus any alternate rendering seen in the source
  - `topics: [<primary>, <secondary>, ...]` — at minimum the primary
  - One-line description: synthesise from the bullets that mentioned the entity. If unclear, leave a placeholder `<TBD>` for the owner to fill
  - First fact bullet anchors to today's source date

**Update path**:
- Read the existing page from wherever it lives (recursive search resolved this in step 4).
- For each candidate fact from this run:
  - Scan `## Facts` for any bullet anchored to the same `[[<date>]]` whose body matches by substring on the noun core or by Levenshtein-distance threshold. If matched → skip (idempotent).
  - Otherwise → append.
- If the new fact contradicts an existing one (e.g. "lives in Sofia" vs "lives in Varna"):
  - Append the new fact to `## Facts` with its date.
  - Add or update the `## Conflicts` section with both anchors and a one-line description of the disagreement.
- Bump `updated:` in frontmatter to today's UTC date.
- **Don't move the file between topic folders** based on an update — topic moves are an owner-driven action, not a side effect of fact ingestion. If the entity's topic genuinely changes, owner triggers `<entity-slug>` rebuild path with explicit intent (or moves the file by hand and re-runs).

### 7. Cross-link

When a fact's body mentions another entity that already has a page (or is being created in this same run), rewrite the mention as `[[<slug>]]` inline. Add the other slug to **this** page's `related:` frontmatter (deduplicated). Bi-directional updates (also adding this page to the other entity's `related:`) are deferred to `lint-wiki` (roadmap step 4) — do not chase them here.

### 8. Report

Print one line per entity touched:

```
<topic>/<slug> — <created|updated> — <N> new fact(s)
```

End with a tally: `processed N day(s); created M entity(ies) across <K> topic folders, updated J`. Include any topic-uncertainty warnings as a separate block at the end. Exit 0.

## Cron

The wrapper `.claude/scripts/ingest-and-weave.sh` chains after `summarize-day` at 00:25 UTC. It runs `claude -p "/ingest-and-weave"` with no args — picks up yesterday's summary by default. Logs to `.claude/scripts/logs/ingest-and-weave.log`.

If the previous summary fails to build, this skill should not run for that day — the chain stops on `summarize-day`'s failure.

## Boundaries

- **Read scope**: `logs/summaries/**/*.md` is the default. Falling back to `logs/<date>.jsonl` is allowed only on the `<entity-slug>` rebuild path or when the summary is suspiciously thin (`event_count < 5` and the day clearly had substantive content).
- **Write scope**: `wiki/entities/<topic>/<slug>.md` only. Never:
  - touches `wiki/entities/_owner.md` (capture-only)
  - touches `wiki/entities/_about.md` or `wiki/entities/index.md` (lint-indexes / manual)
  - creates entities at the entities root level (always must land in a topic folder)
  - touches summaries, JSONL, or `wiki/topics/` (those belong to other skills)
- **No web access.** The skill operates entirely on the vault.
- **No deletions.** Entity pages are never deleted by this skill — the owner removes them by hand if a page turns out to be noise.
- **No topic-folder moves on update.** Topic membership for an existing page is owner-curated; ingestion only appends facts and bumps `updated:`.

## Idempotency

A second run on the same date must produce no further changes. Mechanisms:

- Every fact bullet starts with a `[[<date>]]` anchor.
- Before appending a fact, the skill scans the existing page for any bullet with the same anchor and a similar body (substring-on-noun-core match, or Levenshtein threshold).
- The conflict path follows the same rule: a contradiction recorded once stays once.
- Recursive search by slug (step 4) ensures a re-ingest finds the existing page no matter which topic folder it lives in.

When the same date is re-ingested with **different** content (because the upstream summary was regenerated), only the genuinely-new facts get appended; the prior facts stay verbatim.

## Don't

- **Don't fabricate.** If the summary doesn't say something specific, don't put it in the entity page. The skill is a refactor of summary content into entity-shaped layout, not a generative source.
- **Don't write to the owner's entity page (`wiki/entities/_owner.md`).** That page is owned by the `capture` skill; summary-derived facts must not land there. The owner can appear inline in other entities' facts but never as the page subject from this skill.
- **Don't create entities at the entities root.** Every new page must land in a topic folder. If the topic is genuinely unclear, log the uncertainty and pick the best guess; do not bypass the folder requirement.
- **Don't move existing pages between topic folders.** That's an owner-driven curation step, not an ingest side-effect.
- **Don't promote one-off mentions** to permanent entities. If a name appears in a single bullet across all of history and looks transient, skip it. A second mention is the natural confirmation.
- **Don't index `_pending.md` or other `wiki/` scratch.** That's the `review-pending` skill's territory.
- **Don't rewrite existing facts.** Only append. The conflict protocol handles changes; older facts stay verbatim with their original date anchor.
- **Don't run inside the cron path on a date whose summary doesn't exist** — the chain stops on `summarize-day` failure for a reason.

## When to invoke

- **Cron**, after `summarize-day`, daily at 00:25 UTC.
- **Manual** via `/ingest-and-weave [...]` for backfill, repair, or urgent updates.
- **After a batch of summaries** has been backfilled (e.g. server was down for a week): pass the appropriate date range.
- **After a slug rename or topic move:** pass `<entity-slug>` to rebuild that single page from every known summary against the new location.

## See also

- `docs/skills/ingest-and-weave.md` — operator doc.
- `docs/skills/summarize-day.md` — upstream source of summaries.
- `docs/skills/lint-indexes.md` — navigation half of the auto-wiki.
- `docs/skills/capture.md` — sibling write-path skill (owner-action driven, owns `_owner.md`).
- `docs/roadmap/auto-wiki.md` — section 3 in the roadmap.

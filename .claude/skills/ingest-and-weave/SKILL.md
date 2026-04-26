---
name: ingest-and-weave
description: >
  Maintain LLM-managed entity pages under `wiki/entities/`: one page
  per person, project, place, technology, or organization. Walks the
  daily summaries built by `summarize-day`, extracts mentioned
  entities, and either creates a new page (with a short description
  and a date-anchored fact log) or appends new facts to an existing
  page. Idempotent — already-recorded facts are not duplicated; new
  claims that contradict existing claims get a conflict marker rather
  than silently overwriting. Use when the user asks to "обнови
  entity-страницы", "пройдись ingest-and-weave", or invokes
  `/ingest-and-weave [<date>|<range>|<entity>|now]`. Also runs from
  cron at 00:15 UTC chained after `summarize-day`.
metadata:
  project: Ginarr
  version: "1.0"
allowed-tools: Bash, Read, Write, Edit, Glob
---

# ingest-and-weave

Wiki maintainer for entity pages. Reads `summarize-day` output, weaves the entities mentioned across days into per-entity pages, builds the cross-link graph that the navigation indexes (from `lint-indexes`) make discoverable.

This is the **content half** of the Karpathy-style auto-wiki. The navigation half is `lint-indexes`. Together they keep the wiki self-maintaining: raw JSONL → daily summary → entity pages → folder indexes.

## Layout

- **Source** (read-only): `$GINARR_VAULT_ROOT/logs/summaries/YYYY/MM/<date>.md`
- **Output** (write-scope): `$GINARR_VAULT_ROOT/wiki/entities/<slug>.md`
- **Slug**: `snake_case`, ASCII-transliterated where possible (`Наталья` → `natalya`, `Open AI` → `open_ai`). Original-script name lives in frontmatter `name:`; alternative renderings in `aliases:`.
- **Subdirectories** under `wiki/entities/` are allowed for very large entity sets (`people/`, `projects/`, `places/`) but the default is flat — split only when the directory genuinely needs it.

## Entity types

Recognised in frontmatter `type:`:

- `person` — humans (owner's contacts, family, colleagues, public figures)
- `project` — ongoing initiatives with a start/end (work projects, side projects, life projects)
- `place` — geographic locations (cities, neighbourhoods, restaurants, landmarks)
- `technology` — tools, frameworks, services
- `organization` — companies, institutions
- `event` — one-time occurrences with a date (medical procedures, trips, deadlines)

The list is open — add new types when nothing fits, but prefer collapsing into existing types.

## Entity page format

```markdown
---
name: <canonical name, in original script>
aliases: [<alt name>, <transliteration>, <nickname>]
type: <person|project|place|technology|organization|event>
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
| `<entity-slug>`                   | Rebuild that one entity from every known summary (slow; for repair after a slug rename or merge). |

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

### 4. Resolve to slug

For each candidate:

- Generate slug: lowercase, ASCII-transliterated, `snake_case`.
- Check if `wiki/entities/<slug>.md` exists. If yes → update path. If no → first scan every existing entity's `aliases:` frontmatter for a match (cheap glob + grep) — the same person can appear under multiple renderings. If still no match → creation path.

### 5. Create or update

**Creation path**:
- Write `wiki/entities/<slug>.md` with the template above.
- `name:` is the original-script rendering as the owner uses it.
- `aliases:` includes the slug plus any alternate rendering seen in the source.
- One-line description: synthesise from the bullets that mentioned the entity. If unclear, leave a placeholder `<TBD>` for the owner to fill.
- First fact bullet anchors to today's source date.

**Update path**:
- Read the existing page.
- For each candidate fact from this run:
  - Scan `## Facts` for any bullet anchored to the same `[[<date>]]` whose body matches by substring on the noun core or by Levenshtein-distance threshold. If matched → skip (idempotent).
  - Otherwise → append.
- If the new fact contradicts an existing one (e.g. "lives in Sofia" vs "lives in Varna"):
  - Append the new fact to `## Facts` with its date.
  - Add or update the `## Conflicts` section with both anchors and a one-line description of the disagreement.
- Bump `updated:` in frontmatter to today's UTC date.

### 6. Cross-link

When a fact's body mentions another entity that already has a page (or is being created in this same run), rewrite the mention as `[[<slug>]]` inline. Add the other slug to **this** page's `related:` frontmatter (deduplicated). Bi-directional updates (also adding this page to the other entity's `related:`) are deferred to `lint-wiki` (roadmap step 4) — do not chase them here.

### 7. Report

Print one line per entity touched:

```
<slug> — <created|updated> — <N> new fact(s)
```

End with a tally: `processed N day(s); created M entity(ies), updated K`. Exit 0.

## Cron

The wrapper `.claude/scripts/ingest-and-weave.sh` (planned in roadmap step 3.2) chains after `summarize-day` at 00:15 UTC. It runs `claude -p "/ingest-and-weave"` with no args — picks up yesterday's summary by default. Logs to `.claude/scripts/logs/ingest-and-weave.log`.

If the previous summary fails to build, this skill should not run for that day — the chain stops on `summarize-day`'s failure.

## Boundaries

- **Read scope**: `logs/summaries/**/*.md` is the default. Falling back to `logs/<date>.jsonl` is allowed only on the `<entity-slug>` rebuild path or when the summary is suspiciously thin (`event_count < 5` and the day clearly had substantive content).
- **Write scope**: `wiki/entities/<slug>.md` only. Never touches summaries, never touches JSONL, never touches other `wiki/` subdirs (those are owned by `capture` and the future migration step 3.4).
- **No web access.** The skill operates entirely on the vault.
- **No deletions.** Entity pages are never deleted by this skill — the owner removes them by hand if a page turns out to be noise.

## Idempotency

A second run on the same date must produce no further changes. Mechanisms:

- Every fact bullet starts with a `[[<date>]]` anchor.
- Before appending a fact, the skill scans the existing page for any bullet with the same anchor and a similar body (substring-on-noun-core match, or Levenshtein threshold).
- The conflict path follows the same rule: a contradiction recorded once stays once.

When the same date is re-ingested with **different** content (because the upstream summary was regenerated), only the genuinely-new facts get appended; the prior facts stay verbatim.

## Don't

- **Don't fabricate.** If the summary doesn't say something specific, don't put it in the entity page. The skill is a refactor of summary content into entity-shaped layout, not a generative source.
- **Don't write to the owner's entity page (`wiki/entities/_owner.md`).** That page is owned by the `capture` skill; summary-derived facts must not land there. The owner can appear inline in other entities' facts but never as the page subject from this skill.
- **Don't promote one-off mentions** to permanent entities. If a name appears in a single bullet across all of history and looks transient, skip it. A second mention is the natural confirmation.
- **Don't index `_pending.md` or other `wiki/` scratch.** That's the `review-pending` skill's territory.
- **Don't rewrite existing facts.** Only append. The conflict protocol handles changes; older facts stay verbatim with their original date anchor.
- **Don't run inside the cron path on a date whose summary doesn't exist** — the chain stops on `summarize-day` failure for a reason.

## When to invoke

- **Cron**, after `summarize-day`, daily at 00:15 UTC.
- **Manual** via `/ingest-and-weave [...]` for backfill, repair, or urgent updates.
- **After a batch of summaries** has been backfilled (e.g. server was down for a week): pass the appropriate date range.

## See also

- `docs/skills/ingest-and-weave.md` — operator doc.
- `docs/skills/summarize-day.md` — upstream source of summaries.
- `docs/skills/lint-indexes.md` — navigation half of the auto-wiki.
- `docs/roadmap/auto-wiki.md` — section 3 in the roadmap.

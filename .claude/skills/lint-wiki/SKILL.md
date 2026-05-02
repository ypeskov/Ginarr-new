---
name: lint-wiki
description: >
  Health check for the `wiki/entities/` tree: find contradictions
  (pages with non-empty `## Conflicts` sections), orphan pages (no
  inbound `[[...]]` links from anywhere else in the wiki), missing
  cross-references (an entity name or alias appears as plain text in
  another page but is not wikilinked), `related:` frontmatter that is
  not bidirectionally consistent, missing or stale frontmatter fields,
  and pages where `updated:` is older than the latest fact's date
  anchor. Read-only on entity pages — never modifies them. Writes a
  report to `wiki/_health/<date>.md` and prints a summary in the
  reply. Use when the user asks to "lint wiki", "проверь вики",
  invokes `/lint-wiki`, or wants an audit of the entity graph.
metadata:
  project: Ginarr
  version: "1.1"
allowed-tools: Bash, Read, Write, Glob
---

# lint-wiki

Health check for `wiki/entities/`. Surfaces problems for owner review without changing the entity content itself. Read-only on the wiki layer; writes only a report file under `wiki/_health/<date>.md`.

This is the **graph-quality half** of the auto-wiki maintenance trio:

- `summarize-day` builds the daily index.
- `ingest-and-weave` weaves entity pages from those summaries.
- `capture` writes owner-action-driven facts.
- `lint-indexes` keeps per-folder navigation correct.
- **`lint-wiki` audits the entity graph itself.**

## What it checks

1. **Contradictions** — every page where `## Conflicts` exists and has at least one entry. Surface for owner resolution.
2. **Orphans** — entity pages that no other page references via `[[<slug>]]`. May be intentional (a rarely-mentioned person) or may indicate a missed cross-link.
3. **Missing cross-references** — when an entity's `name` or any of its `aliases:` appears as plain text in another page's body, but not wrapped as `[[<slug>]]`. Suggests a wikilink should be added (the actual edit is the owner's call, or `cross-link`'s).
4. **Bidirectional `related:` consistency** — if A's `related:` lists B, but B's `related:` does not list A, flag the mismatch.
5. **Frontmatter completeness** — required fields present (`name`, `type`, `created`, `updated`); `aliases` includes the slug itself; `type` is from the recognised list (`person`, `project`, `place`, `technology`, `organization`, `event`, `scam_persona`).
6. **`topics:` field validity** — every entity page outside the entities root must have `topics: [...]` with at least one element. The first element (primary topic) must equal the parent folder name (`wiki/entities/dating/eli_badoo.md` → `topics[0] == 'dating'`). Mismatch = either file in wrong folder, or `topics:` out of sync. Pages at the entities root (`_owner.md`, `_about.md`) are exempt from `topics:` requirement.
7. **Topic taxonomy** — primary topic in `topics:` must be one of the recognised topic folders (`dating`, `work`, `tech`, `health`, `finance`, `immigration`, `owner`, `family`). Secondary topics may be any of the recognised set; unknown topic names are flagged.
8. **Stale `updated:`** — pages where `updated:` is more than 30 days older than the latest fact's `[[<date>]]` anchor in `## Facts`.

The owner's `_owner.md` page does **not** have a flat `## Facts` section by design (it uses topical headers); skip the "stale updated vs latest fact" check for that page.

The `_about.md` files inside topic folders are folder-metadata, not entities — exclude them from the entity audit (they have no frontmatter and no `topics:` field by design).

## What it doesn't do

- **No auto-fix.** Owner reviews and resolves manually.
- **No write to entity pages.** Read-only on the wiki content layer.
- **No grep over logs.** Operates only on `wiki/entities/`.

## Report shape

A new file at `wiki/_health/<YYYY-MM-DD>.md`. One per run; if the run produces nothing notable, the file still gets written so the owner has a record.

```markdown
---
date: <YYYY-MM-DD>
generated_at: <UTC ISO>
entity_count: <N>
issue_count: <M>
---

# Wiki health <YYYY-MM-DD>

## Contradictions

- [[<slug>]] — <one-line summary of the conflict from the page's `## Conflicts` section>

## Orphans

- [[<slug>]] (<type>) — no inbound `[[...]]` references anywhere in `wiki/entities/`

## Missing cross-references

- in [[<page>]]: «<exact quoted plain-text mention>» → suggest `[[<entity-slug>]]`

## Related: mismatches

- [[<A>]] lists [[<B>]] in `related:`, but [[<B>]] does not list [[<A>]]

## Frontmatter issues

- [[<slug>]] missing `<field>`
- [[<slug>]] `type` is `<unknown>`, not in recognised list

## Topic mismatches

- [[<slug>]] lives in `<folder>/`, but `topics[0]` is `<other-topic>`
- [[<slug>]] missing `topics:` field
- [[<slug>]] `topics:` contains `<unknown>` not in taxonomy

## Stale updated:

- [[<slug>]] updated: <date>, latest fact: [[<later-date>]]

## Tally

- Entities scanned: N
- Issues by category: contradictions=A, orphans=B, missing_xrefs=C, related_mismatch=D, frontmatter=E, topic_mismatch=F, stale=G
```

Empty sections are dropped. The chat reply summarises in 5-10 lines and points to the report file.

## Workflow

1. **Resolve scope.** Always `$GINARR_VAULT_ROOT/wiki/entities/`. No args.
2. **List pages.** `find $GINARR_VAULT_ROOT/wiki/entities -maxdepth 2 -name '*.md' -not -name 'index.md' -not -name '_about.md'`. The `-maxdepth 2` covers root-level pages (`_owner.md`) plus one level of topic folder. Exclude `_pending.md` (lives at `wiki/`, not under entities, but be defensive). Exclude `_about.md` files (folder metadata, not entities).
3. **Parse each page.** Read frontmatter (`name`, `aliases`, `type`, `topics`, `created`, `updated`, `related`). Note the page's parent folder (= primary topic, except for root-level pages). Read body. Extract `[[<slug>]]` references. Detect `## Conflicts` section.
4. **Build the link graph.** For each page A, record outbound links (slugs A references) and aggregate inbound (slugs A is referenced by).
5. **Run checks.**
   - Contradictions: pages with non-empty `## Conflicts`.
   - Orphans: pages with zero inbound links (skip `_owner.md` — it's a hub, expected to have many inbound and few outbound, but it can never be an orphan in a healthy vault).
   - Missing xrefs: for each page A and each other entity B, scan A's body for B's `name` or any alias as a whole-word substring. If found and not already inside `[[...]]`, flag.
   - Related mismatch: bidirectional check on `related:`.
   - Frontmatter: required fields, type validity, alias-includes-slug.
   - Topics: presence of `topics:` field for non-root pages; `topics[0]` matches parent folder; all topic names are in recognised taxonomy.
   - Stale: parse all `[[YYYY-MM-DD]]` anchors in `## Facts`, compare to `updated:`.
6. **Compose the report** in the format above.
7. **Write `wiki/_health/<YYYY-MM-DD>.md`.** Create the dir if missing. Overwrite if the file already exists for today (rerunning on the same day should refresh, not pile up).
8. **Reply to chat.** Short summary (counts per category + a couple of headline issues), point to the report path.

## Cron reminder (separate from running the skill)

A weekly cron line (`.claude/scripts/lint-wiki-reminder.sh`) sends a Telegram nudge — «Время прогнать /lint-wiki, еженедельная проверка». **The reminder does not run the skill itself.** Auto-running would either flood `_health/` with redundant reports or require auto-resolution, neither desired. The skill stays a deliberate owner action.

## Don't

- Don't modify entity pages. Read-only on the content layer.
- Don't fabricate "missing fact" entries — the skill audits structure, not content.
- Don't suggest wikilinks for the owner's own name («Юра» / «Yuriy» etc.). Auto-linking everywhere to `[[_owner]]` would noise up every page; cross-references to the owner stay as plain text or as explicit `[[_owner]]` only when the owner himself or `capture` chose to write them that way.
- Don't index the `_health/` reports themselves into the entity graph.

## When to invoke

- Manual: `/lint-wiki` or "проверь вики" / "lint wiki" / "audit entities".
- After a backfill that added many entities at once.
- After a manual rename of an entity slug — pages referencing the old slug become broken links.

## See also

- `docs/skills/lint-wiki.md` — operator doc.
- `docs/scripts/lint-wiki-reminder.md` — weekly cron reminder.
- `docs/roadmap/auto-wiki.md` — section 4.

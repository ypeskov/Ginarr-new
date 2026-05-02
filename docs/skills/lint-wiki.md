# `lint-wiki` — entity-graph health check

Audits `wiki/entities/` for structural problems: contradictions, orphan pages, missing cross-references, `related:` mismatches, frontmatter completeness, stale `updated:`. Read-only on entity pages; writes a report to `wiki/_health/<date>.md` and prints a summary in the reply.

## Source

- Skill: [`.claude/skills/lint-wiki/SKILL.md`](../../.claude/skills/lint-wiki/SKILL.md) — authoritative behaviour.
- Cron reminder (does NOT run the skill, only nudges): [`.claude/scripts/lint-wiki-reminder.sh`](../../.claude/scripts/lint-wiki-reminder.sh).

## When to invoke

- Manual: `/lint-wiki` or "проверь вики" / "lint wiki" / "audit entities".
- After a backfill that added many entities at once.
- After a manual rename of an entity slug — pages referencing the old slug become broken links.

## Checks

1. **Contradictions** — pages with non-empty `## Conflicts`.
2. **Orphans** — entity pages with no inbound `[[<slug>]]` reference anywhere else in the wiki.
3. **Missing cross-references** — entity name or alias appears as plain text in another page but is not wikilinked.
4. **`related:` mismatch** — A lists B in `related:`, but B does not list A.
5. **Frontmatter completeness** — required fields, `type` from the recognised list (`person`, `project`, `place`, `technology`, `organization`, `event`, `scam_persona`), `aliases` includes the slug.
6. **`topics:` field validity** — every non-root entity page must have `topics: [...]` whose first element matches the parent folder. Pages at the entities root (`_owner.md`) are exempt.
7. **Topic taxonomy** — primary and secondary topics must be in the recognised set: `dating`, `work`, `tech`, `health`, `finance`, `immigration`, `owner`, `family`.
8. **Stale `updated:`** — `updated:` more than 30 days older than the latest fact's `[[<date>]]` anchor.

## Output

| Where           | What                                                                                      |
|-----------------|-------------------------------------------------------------------------------------------|
| Chat reply      | 5–10 line summary: counts per category + a couple of headline issues + report path.       |
| Report file     | `wiki/_health/<YYYY-MM-DD>.md` — full structured report (frontmatter + per-category section). |

Empty categories are dropped from the report.

## What it touches

Only `wiki/_health/<date>.md`. Never the entity pages themselves — auto-fix would defeat the audit purpose.

## What it skips

- The owner's `_owner.md` is exempt from the orphan check (it's a hub, but never absent inbound traffic in a healthy vault). It is also exempt from the "stale updated vs latest fact" check (`_owner.md` uses topical sections, not a flat `## Facts` list) and from the `topics:` requirement (root-level page).
- `_about.md` files inside topic folders are folder-metadata, not entities — excluded from the entity audit (no frontmatter, no `topics:` by design).
- The `_health/` reports themselves are never indexed back into the entity graph.

## Where to look when something's off

| Symptom                                       | Likely cause                                                                                  |
|-----------------------------------------------|-----------------------------------------------------------------------------------------------|
| Same orphan flagged every run                 | Page is intentionally standalone — owner can ignore the warning per page.                     |
| Missing-xref noise on common words            | Catalogue entry has a too-generic name; add a more-specific `aliases:` set.                   |
| Bidirectional `related:` mismatch on every run | Skill is one-shot; `lint-wiki` does not auto-fix. Either fix manually or add a follow-up `lint-wiki --apply` mode (out of scope for v1). |
| Topic mismatch flagged on every run            | Page is in the wrong folder OR `topics:` field is out of sync with location. Move the file to match `topics[0]`, or update `topics[0]` to match the folder. |

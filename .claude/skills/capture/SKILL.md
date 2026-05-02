---
name: capture
description: >
  Decide whether a user statement is worth persisting to the Auto-Wiki
  vault and, if so, route it to the correct entity page under
  `wiki/entities/<topic>/`. Consult whenever the user states a fact
  about themselves, expresses a preference, gives feedback on how to
  work with them, makes a decision, or explicitly asks to remember. Do
  not trigger on purely operational questions, debugging sessions, code
  tasks, or one-off task requests — those are not memory.
metadata:
  project: Ginarr
  version: "2.1"
---

# capture

Triage each memorable statement into one of four paths: **auto-save**, **unconfirmed save**, **`_pending.md`**, or **ask-immediately**. Operate on the shared vault at `$GINARR_VAULT_ROOT/wiki/` — owner-facing, mirrored to Obsidian. **Separate from your private per-session auto-memory**; do not confuse the two.

This skill is the **owner-action-driven** writer to `wiki/entities/`. The cron-driven `ingest-and-weave` is the other writer — it reads daily summaries and weaves entities. Both write into the same entity-page format and follow the same topic-folder convention; the two never touch `wiki/entities/_owner.md` simultaneously, because `ingest-and-weave` is explicitly forbidden from writing there.

## Confidence triage

| Confidence | Cue examples                                                                                                       | Path                                                                                       |
|------------|--------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------|
| **High**   | "remember X", "запомни Y", explicit feedback ("don't do Y"), factual claim about the owner, confirmed decision     | **Auto-save silently** to the relevant entity page.                                        |
| **Medium** | Indirect preference, one-off choice, inferred fact                                                                 | **Auto-save with `unconfirmed` marker** on the fact line. Confirm lazily on next mention.  |
| **Low / ambiguous** | Speculation, thinking out loud, idle reflection                                                           | **Append a block to `wiki/_pending.md`.** Reviewed later via `/review`.                    |

## Always ask immediately (overrides triage)

Stop and ask the owner before writing when:

- The new claim **contradicts** an existing entity-page fact (see Conflict protocol).
- The fact involves **external stakeholders** (other people, deadlines, commitments you might act on).
- The content **borders on sensitive data** (finances, health, credentials).

## Never save

- Ephemeral task / session state (what's running now, what you just did).
- Information trivially derivable from an existing entity page (dedup, not duplicate).
- Low-confidence hunches → those go to `_pending.md`, never directly to an entity page.

## Routing — pick the entity

Every non-pending fact lives on an entity page under `wiki/entities/<topic>/<slug>.md` (or at the entities root for `_owner.md`). Decide the entity:

### Owner-meta facts → `_owner.md`

Anything **about the owner himself** routes to `wiki/entities/_owner.md` (root level, not in any topic folder):

- Self-facts (biography, profile, language, family, work, education, legal status, home tech stack).
- Health (metabolic, varicose, knee, etc.).
- Values, goals, fears, patterns.
- **Communication preferences** (formatting rules, language preferences, push-back style, plan-doc language, media to avoid). These were the old `feedback/` content — they all live on `_owner.md` now under `## Communication preferences`.
- Default timezone.

`_owner.md` has top-level sections (Profile, Family, Biography, Work, Health, Values …, Communication preferences, …). Append to the **most appropriate existing section**. If no section fits, add a new top-level `## <section name>` rather than creating a separate file.

### Entity-specific facts → `<topic>/<slug>.md`

Facts **about a specific named entity** (person, project, place, technology, organization, event, scam_persona) route to that entity's page:

- Owner mentions a colleague's situation → `entities/work/<colleague_slug>.md`.
- Owner mentions a city he's visiting → `entities/<topic>/<city_slug>.md` (topic depends on the visit context — `health` for a clinic city, `dating` for a date location, etc.).
- Owner makes a decision about a specific project → `entities/<topic>/<project_slug>.md` (e.g. `entities/immigration/bg_residency.md`, `entities/work/ringcentral.md`).
- Owner notes a fact about a tool or service → `entities/tech/<tech_slug>.md` (or another topic if the tool is primarily used inside that domain — Boo dating app: `entities/dating/boo.md` with `topics: [dating, tech]`).

If the entity page does not yet exist, create it under the resolved primary topic (see Topic resolution below). If it does exist, append to its `## Facts` section.

### Cross-entity facts

A statement that involves **the owner's relationship with another entity** (e.g. "Mikhail returns from leave next week, and I'm preparing the case for him") goes on the **other entity** (`entities/work/ringcentral.md` or whatever the case-context is), not on `_owner.md`. Owner is mentioned inline as `[[_owner]]` or simply «владелец / I».

## Workflow

1. **Classify confidence.** High / medium / low.
2. **Always-ask overrides?** → Ask the owner inline; wait for the answer before acting.
3. **Never-save?** → Stop.
4. **Low-confidence?** → Append a block to `$GINARR_VAULT_ROOT/wiki/_pending.md` (format below). Stop.
5. **Identify the target entity.** Owner-meta → `_owner.md`. Otherwise the slug of the entity the fact is about.
6. **Resolve the slug AND find the existing page.**
   - `snake_case`, ASCII-transliterated.
   - **Search recursively** for `<slug>.md` under `wiki/entities/` — the page may live in any topic folder. Use `find $GINARR_VAULT_ROOT/wiki/entities/ -name "<slug>.md"`.
   - If not found by slug, scan every existing entity's `aliases:` frontmatter via `grep -r "^aliases:" $GINARR_VAULT_ROOT/wiki/entities/` — the same person can appear under multiple renderings.
7. **Match found?** → Read the page. Decide which section the new fact belongs to. Append the fact (date-anchored, declarative, one line). Bump `updated:` in frontmatter. **Do not move the file** between topic folders — topic curation is a separate owner-driven action. If a contradiction → Conflict protocol.
8. **No match?** → Resolve primary topic (see Topic resolution below). Create the page at `wiki/entities/<topic>/<slug>.md` using the template. Add the new fact as the first line under `## Facts`.
9. **Telegram feedback** (see below). Never echo the stored value in the reply.

## Topic resolution

When creating a new entity page (step 8), pick the **primary topic** by:

1. **Conversational context:** what topic was the current conversation about? (Owner discussing dating prospects → `dating`; debugging a tech issue → `tech`; talking about doctor visit → `health`.)
2. **Co-mentioned existing entities:** if the new entity appeared alongside others in the same statement, read those entities' `topics:` frontmatter — the mode of their primary topics is a strong signal.
3. **Type-defaults** (when context is thin):
   - `person` → conversational context (dating talk → `dating`, work talk → `work`, family talk → `family`, etc.)
   - `technology` → `tech` unless used primarily inside another topic (e.g. dating-specific platform → `dating` primary, `tech` secondary)
   - `organization` → `work` unless explicitly otherwise (medical org → `health`, mail forwarder → `family` or `finance`)
   - `place` → owner-context (where the owner lives, works, receives care, dates)
   - `event` → match the event's domain (medical procedure → `health`, deal closure → `work`, trip → context-of-trip)
   - `scam_persona` → `dating`
4. **Secondary topics:** include any non-primary topic the entity genuinely participates in. The `topics:` field is `[<primary>, <secondary>, ...]`; first element dictates the folder.
5. **If still unresolved:** ask the owner inline — capture is owner-action-driven, asking is on-pattern. (Unlike `ingest-and-weave` which has no human in the loop and must guess.)

Closed-by-convention topic list (current taxonomy): `dating`, `work`, `tech`, `health`, `finance`, `immigration`, `owner`, `family`. Extensible — propose a new topic + folder if a recurring cluster doesn't fit.

## Entity-page format

Aligned with `ingest-and-weave`. Same shape so both skills produce a consistent file:

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

<one-line description>

## Facts

- [[<date>]] <fact, declarative, one line>

## Conflicts

- [[<date>]] <claim A> ↔ [[<date>]] <claim B> — unresolved
```

`_owner.md` has additional structured sections (Profile, Family, Biography, Health, Values, etc.) instead of a single flat `## Facts` list — owner-meta naturally taxonomises that way. `_owner.md` does **not** carry a `topics:` field — it is a root-level page outside the topic-folder system.

`[[<date>]]` resolves to the daily summary at `logs/summaries/YYYY/MM/<date>.md` via Obsidian's wikilink resolver. For owner-statements without a summary anchor (today's UTC date, no summary yet), use the message's UTC date as the anchor.

For medium-confidence saves, append `(unconfirmed)` to the bullet body — no separate `status` frontmatter on the page itself, since one entity page can mix confidence levels. The `unconfirmed` marker is per-fact.

## `_pending.md` block format

`$GINARR_VAULT_ROOT/wiki/_pending.md` already contains the template at its top. Each low-confidence candidate is appended as a block separated by a blank line:

```
## <short title>
- ts: <UTC ISO>
- source: logs/YYYY/MM/YYYY-MM-DD.jsonl#ts=...
- proposed entity: <topic>/<slug> or _owner
- proposed section: <e.g. Health, Communication preferences, Facts>

<body / quote>
```

Append via Read → rewrite with the new block appended → Write. Do not overwrite earlier candidates.

### Threshold notification (≥5 pending)

After any low-confidence append to `_pending.md`, count the `## ` headings in the file. Call that `N`.

- `N >= 5` **and** `$GINARR_VAULT_ROOT/wiki/.pending_notified` does **not** exist → send one short Telegram message: `Накопилось N кандидатов в /review — разберёшь?` (match the owner's recent language; default to Russian). Then create `.pending_notified` so the ping does not repeat at every subsequent capture while the queue stays above the threshold.
- `N < 5` **and** `.pending_notified` exists → delete it. The flag is a latch — set once on the upward crossing, cleared on the downward crossing.
- No Telegram context on the current turn (no `<channel>` tag) → skip the notification. Do not write to stdout; proactive pings only make sense against a chat.

Do not notify about individual high/medium-confidence saves — those surface via the 💾 reaction at save time.

## Conflict protocol

When updating an existing entity page and a new claim contradicts an existing fact:

1. **Do not overwrite.** Both facts stay in `## Facts` with their original date anchors.
2. Add a `## Conflicts` section entry pointing to both anchors and a one-line description of the disagreement.
3. Ask the owner at the next natural break: "I have two conflicting facts on `<topic>/<slug>` — the older one says A ([[<date1>]]), the new one says B ([[<date2>]]). Which is right?".
4. When the owner resolves it, delete the losing fact and trim the matching `## Conflicts` line.

## Telegram feedback

The `<channel>` tag on the user prompt carries `chat_id` and `message_id`. Use them for the tools below.

- **High-confidence save** → react **💾** on the originating message via `mcp__plugin_telegram_telegram__react`. No text reply about the save itself. Fallback: 💾 → 🧠 → 👌.
- **Medium-confidence save** → react 💾 **and** send one short reply: `Saved as unconfirmed to wiki/entities/<topic>/<slug>.md` (path only; no paraphrase of content).
- **Low-confidence (pending)** → no reaction, no reply. The `/review` flow surfaces it later.
- **Always-ask** → send a direct text question; wait for the answer; then apply the resulting routing.

Never echo the saved value in the visible reply — the reply itself lands in the log and defeats the point for sensitive captures.

## Slug discipline

- **`snake_case`, ASCII-transliterated.** `Наталья` → `natalya`. `Open AI` → `open_ai`. Cyrillic name lives in frontmatter `name:`.
- **Underscore-prefix** for sort-priority hacks (`_owner.md`) is allowed and meaningful — these are the **only** files that intentionally start with `_` in `wiki/entities/`. The skill rule that excludes `_pending.md` / `_tools/` / `_attachments/` does not apply here.
- One entity = one file. The dedup mechanism. Always check `aliases:` frontmatter across **all topic folders** before creating a new one (`grep -r "^aliases:" $GINARR_VAULT_ROOT/wiki/entities/`).
- Owner is **never** a separate person entity — he is `_owner.md`. Don't create `yuriy.md`.

## Auto-Wiki vault ≠ your private memory

`$GINARR_VAULT_ROOT/wiki/` is the **owner-facing** vault, mirrored to their Obsidian client. Your private auto-memory under `~/.claude/projects/.../memory/` is a separate, Claude-only notebook. For memorable *owner-visible* facts, capture into the Auto-Wiki vault (the entity model). For meta-behaviour about how *you* should operate (skill conventions, tool quirks), stay in private memory. When in doubt, a fact about the human or about a named entity in his life goes to the Auto-Wiki vault.

## Migration history

- **2026-04-26** — SPEC.v3 per-type folders (`wiki/{decisions,feedback,projects,reference,user}/`) collapsed into the entity-page model under `wiki/entities/`; old folders archived under `wiki/archive/migration-2026-04-26/`. The capture skill was rewritten to route directly to `wiki/entities/<slug>.md`.
- **2026-05-02** — flat entity layout split into topic folders (`dating/`, `work/`, `tech/`, `health/`, `finance/`, `immigration/`, `owner/`, `family/`). Mandatory `topics:` field added to entity frontmatter. Slug resolution and creation paths updated to handle nested directories.

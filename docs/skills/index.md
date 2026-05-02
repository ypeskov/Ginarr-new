# Skills

Agent Skills available in this project, all under `.claude/skills/<name>/`. Each skill is authoritative in its own `SKILL.md`; this index is just a pointer list.

## Installed

- **`create-skill`** — scaffolds a new skill following the [agentskills.io](https://agentskills.io/specification) spec. Source: copied from OpenClaw. Authoritative doc: [`.claude/skills/create-skill/SKILL.md`](../../.claude/skills/create-skill/SKILL.md).
- **`save-to-repo`** — the commit / push workflow for this repo. Enforces English messages, no AI co-author footer, bundled docs updates, inline git identity, and the Layer 1 denylist-trap workaround. Authoritative doc: [`.claude/skills/save-to-repo/SKILL.md`](../../.claude/skills/save-to-repo/SKILL.md).
- **`/nolog`** — slash command that pauses / resumes the write-path log (SPEC.v3 Layer 4). Template: [`.claude/commands/nolog.md`](../../.claude/commands/nolog.md); behaviour documented in [`nolog.md`](nolog.md).
- **`/redact`** — slash command that appends a value to the Layer 3 owner-marked denylist; `redactor.py` scrubs matches on every log write (SPEC.v3 Layer 3). Template: [`.claude/commands/redact.md`](../../.claude/commands/redact.md); behaviour documented in [`redact.md`](redact.md).
- **`capture`** — write-side memory skill: triages a user statement into auto-save, unconfirmed save, `_pending.md`, or ask-immediately; writes to `$GINARR_VAULT_ROOT/wiki/entities/<topic>/<slug>.md` (or `_owner.md` for owner-meta). Authoritative doc: [`.claude/skills/capture/SKILL.md`](../../.claude/skills/capture/SKILL.md); operator doc: [`capture.md`](capture.md).
- **`recall`** — read-side memory skill: on retrospective questions, greps `$GINARR_VAULT_ROOT/wiki/` first, then `logs/summaries/`, only then drills into a specific day's `logs/.../*.jsonl`, cites the source in the reply. Never writes. Authoritative doc: [`.claude/skills/recall/SKILL.md`](../../.claude/skills/recall/SKILL.md); operator doc: [`recall.md`](recall.md).
- **`summarize-day`** — cron-driven daily roll-up: reads `$GINARR_VAULT_ROOT/logs/YYYY/MM/<date>.jsonl`, writes a brief grep-friendly Markdown summary to `logs/summaries/YYYY/MM/<date>.md`. Idempotent, backfills gaps, never overwrites without an explicit ask. Authoritative doc: [`.claude/skills/summarize-day/SKILL.md`](../../.claude/skills/summarize-day/SKILL.md); operator doc: [`summarize-day.md`](summarize-day.md).
- **`lint-indexes`** — walks a directory tree and rebuilds every folder's `index.md` from scratch as a pure navigation file: heading + list of files (with one-line descriptions from each file's first H1) + list of subdirectories. Each `index.md` is fully linter-owned; convention notes and prose belong in separate files. Dry-run by default; `--apply` writes; `--cron` (used only by the wrapper) skips the cross-vault confirmation. Authoritative doc: [`.claude/skills/lint-indexes/SKILL.md`](../../.claude/skills/lint-indexes/SKILL.md); operator doc: [`lint-indexes.md`](lint-indexes.md).
- **`ingest-and-weave`** — reads daily summaries built by `summarize-day` and weaves the mentioned entities into per-entity pages under `$GINARR_VAULT_ROOT/wiki/entities/`. Idempotent; appends only; conflicts get a marker rather than silent overwrites. Triggered manually (`/ingest-and-weave`) or via cron chained after `summarize-day` at 00:15 UTC. Authoritative doc: [`.claude/skills/ingest-and-weave/SKILL.md`](../../.claude/skills/ingest-and-weave/SKILL.md); operator doc: [`ingest-and-weave.md`](ingest-and-weave.md).
- **`lint-wiki`** — health check for `wiki/entities/`: contradictions, orphans, missing cross-references, `related:` mismatches, frontmatter issues, stale `updated:`. Read-only on entity pages; writes a report to `wiki/_health/<date>.md` and replies with a summary. Manual only — a separate cron sends a weekly reminder. Authoritative doc: [`.claude/skills/lint-wiki/SKILL.md`](../../.claude/skills/lint-wiki/SKILL.md); operator doc: [`lint-wiki.md`](lint-wiki.md).
- **`cross-link`** — proposes `[[wikilink]]` insertions in the owner's main Obsidian vault, pointing to existing entity pages or to other main-vault notes. Dry-run by default; `--apply` writes only after explicit owner confirmation. Never creates a new page. Authoritative doc: [`.claude/skills/cross-link/SKILL.md`](../../.claude/skills/cross-link/SKILL.md); operator doc: [`cross-link.md`](cross-link.md).
- **`/review`** — slash command + `review-pending` skill that walks `wiki/_pending.md` candidates one-by-one (save / drop / skip / edit). Template: [`.claude/commands/review.md`](../../.claude/commands/review.md); skill: [`.claude/skills/review-pending/SKILL.md`](../../.claude/skills/review-pending/SKILL.md); operator doc: [`review.md`](review.md).
- **`load-topic`** — topic-scoped context loader: reads `wiki/topics/<name>.md` manifest, walks `wiki/entities/<name>/` plus cross-tagged entities, reads listed main-vault paths, prints a structured summary. Read-only. Authoritative doc: [`.claude/skills/load-topic/SKILL.md`](../../.claude/skills/load-topic/SKILL.md); operator doc: [`load-topic.md`](load-topic.md).
- **`edit-topic`** — topic manifest curator: list / show / create / add / remove / rename operations on `wiki/topics/<name>.md`. Validates referenced paths exist. Authoritative doc: [`.claude/skills/edit-topic/SKILL.md`](../../.claude/skills/edit-topic/SKILL.md); operator doc: [`edit-topic.md`](edit-topic.md).

## External utilities (copied from OpenClaw)

Convenience skills — no interaction with the memory layer, kept here so the assistant can act on day-to-day requests without bouncing between repos. Authoritative behaviour stays in each skill's own `SKILL.md`; the operator doc linked below notes Ginarr-specific integration points only.

- **`/email-digest`** — IMAP inbox summary across three mailboxes, rendered in Russian. Authoritative: [`.claude/skills/email-digest/SKILL.md`](../../.claude/skills/email-digest/SKILL.md). Operator doc: [`email-digest.md`](email-digest.md).
- **`/news-digest`** — RSS + Hacker News + ETF portfolio summary. Authoritative: [`.claude/skills/news-digest/SKILL.md`](../../.claude/skills/news-digest/SKILL.md). Operator doc: [`news-digest.md`](news-digest.md).
- **`/weather`** — Open-Meteo forecast, no API key, default Sofia / 7 days. Authoritative: [`.claude/skills/weather/SKILL.md`](../../.claude/skills/weather/SKILL.md). Operator doc: [`weather.md`](weather.md).
- **`/calendar-digest`** — Google Calendar agenda via MCP. Authoritative: [`.claude/skills/calendar-digest/SKILL.md`](../../.claude/skills/calendar-digest/SKILL.md). Operator doc: [`calendar-digest.md`](calendar-digest.md).
- **`obsidian`** — full Obsidian vault access (distinct from Ginarr's `Auto-Wiki/` sub-vault). Authoritative: [`.claude/skills/obsidian/SKILL.md`](../../.claude/skills/obsidian/SKILL.md). Operator doc: [`obsidian.md`](obsidian.md).
- **`obsidian-structure`** — folder taxonomy and routing rules for the vault. Authoritative: [`.claude/skills/obsidian-structure/SKILL.md`](../../.claude/skills/obsidian-structure/SKILL.md). Operator doc: [`obsidian-structure.md`](obsidian-structure.md).

## Not yet built

Each will get its own entry here when added:

- `consolidate` — wraps the consolidation CLI tool (dry-run → review → apply).

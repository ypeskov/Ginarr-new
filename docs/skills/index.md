# Skills

Agent Skills available in this project, all under `.claude/skills/<name>/`. Each skill is authoritative in its own `SKILL.md`; this index is just a pointer list.

## Installed

- **`create-skill`** — scaffolds a new skill following the [agentskills.io](https://agentskills.io/specification) spec. Source: copied from OpenClaw. Authoritative doc: [`.claude/skills/create-skill/SKILL.md`](../../.claude/skills/create-skill/SKILL.md).
- **`save-to-repo`** — the commit / push workflow for this repo. Enforces English messages, no AI co-author footer, bundled docs updates, inline git identity, and the Layer 1 denylist-trap workaround. Authoritative doc: [`.claude/skills/save-to-repo/SKILL.md`](../../.claude/skills/save-to-repo/SKILL.md).
- **`/nolog`** — slash command that pauses / resumes the write-path log (SPEC.v3 Layer 4). Template: [`.claude/commands/nolog.md`](../../.claude/commands/nolog.md); behaviour documented in [`nolog.md`](nolog.md).
- **`/redact`** — slash command that appends a value to the Layer 3 owner-marked denylist; `redactor.py` scrubs matches on every log write (SPEC.v3 Layer 3). Template: [`.claude/commands/redact.md`](../../.claude/commands/redact.md); behaviour documented in [`redact.md`](redact.md).
- **`capture`** — write-side memory skill: triages a user statement into auto-save, unconfirmed save, `_pending.md`, or ask-immediately; writes to `$GINARR_VAULT_ROOT/notes/<type>/<snake_case>.md`. Authoritative doc: [`.claude/skills/capture/SKILL.md`](../../.claude/skills/capture/SKILL.md); operator doc: [`capture.md`](capture.md).
- **`recall`** — read-side memory skill: on retrospective questions, greps `$GINARR_VAULT_ROOT/notes/` first, then bounded date windows in `logs/`, cites the source in the reply. Never writes. Authoritative doc: [`.claude/skills/recall/SKILL.md`](../../.claude/skills/recall/SKILL.md); operator doc: [`recall.md`](recall.md).
- **`/review`** — slash command + `review-pending` skill that walks `notes/_pending.md` candidates one-by-one (save / drop / skip / edit). Template: [`.claude/commands/review.md`](../../.claude/commands/review.md); skill: [`.claude/skills/review-pending/SKILL.md`](../../.claude/skills/review-pending/SKILL.md); operator doc: [`review.md`](review.md).

## External utilities (copied from OpenClaw)

Convenience skills — no interaction with the memory layer, kept here so the assistant can act on day-to-day requests without bouncing between repos. Authoritative behaviour stays in each skill's own `SKILL.md`; the operator doc linked below notes Ginarr-specific integration points only.

- **`/email-digest`** — IMAP inbox summary across three mailboxes, rendered in Russian. Authoritative: [`.claude/skills/email-digest/SKILL.md`](../../.claude/skills/email-digest/SKILL.md). Operator doc: [`email-digest.md`](email-digest.md).
- **`/news-digest`** — RSS + Hacker News + ETF portfolio summary. Authoritative: [`.claude/skills/news-digest/SKILL.md`](../../.claude/skills/news-digest/SKILL.md). Operator doc: [`news-digest.md`](news-digest.md).
- **`/weather`** — Open-Meteo forecast, no API key, default Sofia / 7 days. Authoritative: [`.claude/skills/weather/SKILL.md`](../../.claude/skills/weather/SKILL.md). Operator doc: [`weather.md`](weather.md).
- **`/calendar-digest`** — Google Calendar agenda via MCP. Authoritative: [`.claude/skills/calendar-digest/SKILL.md`](../../.claude/skills/calendar-digest/SKILL.md). Operator doc: [`calendar-digest.md`](calendar-digest.md).
- **`obsidian`** — full Obsidian vault access (distinct from Ginarr's `chat-memory/` sub-vault). Authoritative: [`.claude/skills/obsidian/SKILL.md`](../../.claude/skills/obsidian/SKILL.md). Operator doc: [`obsidian.md`](obsidian.md).
- **`obsidian-structure`** — folder taxonomy and routing rules for the vault. Authoritative: [`.claude/skills/obsidian-structure/SKILL.md`](../../.claude/skills/obsidian-structure/SKILL.md). Operator doc: [`obsidian-structure.md`](obsidian-structure.md).

## Not yet built

Planned per SPEC.v3. Each will get its own entry here when added:

- `consolidate` — wraps the consolidation CLI tool (dry-run → review → apply).

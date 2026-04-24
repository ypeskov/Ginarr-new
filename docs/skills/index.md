# Skills

Agent Skills available in this project, all under `.claude/skills/<name>/`. Each skill is authoritative in its own `SKILL.md`; this index is just a pointer list.

## Installed

- **`create-skill`** — scaffolds a new skill following the [agentskills.io](https://agentskills.io/specification) spec. Source: copied from OpenClaw. Authoritative doc: [`.claude/skills/create-skill/SKILL.md`](../../.claude/skills/create-skill/SKILL.md).
- **`save-to-repo`** — the commit / push workflow for this repo. Enforces English messages, no AI co-author footer, bundled docs + roadmap updates, inline git identity, and the Layer 1 denylist-trap workaround. Authoritative doc: [`.claude/skills/save-to-repo/SKILL.md`](../../.claude/skills/save-to-repo/SKILL.md).
- **`/nolog`** — slash command that pauses / resumes the write-path log (SPEC.v3 Layer 4). Template: [`.claude/commands/nolog.md`](../../.claude/commands/nolog.md); behaviour documented in [`nolog.md`](nolog.md).
- **`/redact`** — slash command that appends a value to the Layer 3 owner-marked denylist; `redactor.py` scrubs matches on every log write (SPEC.v3 Layer 3). Template: [`.claude/commands/redact.md`](../../.claude/commands/redact.md); behaviour documented in [`redact.md`](redact.md).
- **`capture`** — write-side memory skill: triages a user statement into auto-save, unconfirmed save, `_pending.md`, or ask-immediately; writes to `$GINARR_VAULT_ROOT/notes/<type>/<snake_case>.md`. Authoritative doc: [`.claude/skills/capture/SKILL.md`](../../.claude/skills/capture/SKILL.md); operator doc: [`capture.md`](capture.md).

## Not yet built

Planned per SPEC.v3. Each will get its own entry here when added:

- `recall` — searches `notes/` and `logs/` before answering.
- `review` — walks through `notes/_pending.md` candidates with confirm / drop / edit.
- `consolidate` — wraps the consolidation CLI tool (dry-run → review → apply).

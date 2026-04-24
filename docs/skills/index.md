# Skills

Agent Skills available in this project, all under `.claude/skills/<name>/`. Each skill is authoritative in its own `SKILL.md`; this index is just a pointer list.

## Installed

- **`create-skill`** — scaffolds a new skill following the [agentskills.io](https://agentskills.io/specification) spec. Source: copied from OpenClaw. Authoritative doc: [`.claude/skills/create-skill/SKILL.md`](../../.claude/skills/create-skill/SKILL.md).
- **`save-to-repo`** — the commit / push workflow for this repo. Enforces English messages, no AI co-author footer, bundled docs + roadmap updates, inline git identity, and the Layer 1 denylist-trap workaround. Authoritative doc: [`.claude/skills/save-to-repo/SKILL.md`](../../.claude/skills/save-to-repo/SKILL.md).
- **`/nolog`** — slash command that pauses / resumes the write-path log (SPEC.v3 Layer 4). Template: [`.claude/commands/nolog.md`](../../.claude/commands/nolog.md); behaviour documented in [`nolog.md`](nolog.md).

## Not yet built

Planned per SPEC.v3. Each will get its own entry here when added:

- `capture` — decides whether a statement is worth saving and to which note type/file.
- `recall` — searches `notes/` and `logs/` before answering.
- `review` — walks through `notes/_pending.md` candidates with confirm / drop / edit.
- `consolidate` — wraps the consolidation CLI tool (dry-run → review → apply).
- `redact` — handles `/redact <value>` for the Layer 3 denylist.

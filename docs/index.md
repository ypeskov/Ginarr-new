# Ginarr docs

Operator-level documentation of the bot: what exists, how it wires together, where to look when something is off.

## Update rule

Every directory under `docs/` carries an `index.md` listing its files and subdirectories with a one-line description. When you add, modify, or remove a script, hook, or skill, update the matching doc **and** the parent `index.md` in the same commit that touches the code. Out-of-date docs are worse than missing ones.

## Contents

### Files

- [architecture.md](architecture.md) — big picture: bot process, Auto-Wiki vault, hook-driven write-path.
- [configuration.md](configuration.md) — environment variables, `.env` locations, bootstrap recipe.
- [hooks.md](hooks.md) — Claude Code hooks wired in `settings.json`; assistant-text extraction logic.

### Subdirectories

- [roadmap/](roadmap/index.md) — active and closed implementation plans (in Russian, with checkboxes).
- [scripts/](scripts/index.md) — one file per `.claude/scripts/*` utility.
- [skills/](skills/index.md) — installed Agent Skills, with pointers to their authoritative `SKILL.md`.
- [tools/](tools/index.md) — standalone maintenance CLIs (`consolidate`, `search`, `archive`) under `tools/` at the repo root.

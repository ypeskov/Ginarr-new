# TODO

Features not yet scheduled for implementation. Short description per entry; details come when we start the work.

## Multi-vault support

`GINARR_VAULT_ROOT` currently pins the bot to exactly one Auto-Wiki vault: all writes (logs, new notes) go there, recall searches there.

Add the ability to attach **secondary vaults** alongside the primary:

- **Primary vault** — unchanged; the only destination for writes.
- **Secondary vaults** — read-only for recall/search. The agent can reference notes from them but never modifies them.

Use cases: shared knowledge bases across personas, read-only archive of a previous vault, or household-shared notes alongside private memory.

## Runtime migration check (Junie / OpenCode + oh-my-opencode)

Claude Code is the reference runtime, but per CLAUDE.md, Junie and OpenCode with the `oh-my-opencode` plugin are supported migration targets on the same skill/agent format. Walk the full write-path and the memory skills on each of those runtimes to confirm skill descriptions trigger correctly, hooks map cleanly (or degrade gracefully on hook-less runtimes), and vault reads/writes land where expected. Document any per-runtime quirks in `docs/architecture.md` and, if behaviour diverges, split per-runtime skill variants.

## SPEC v4 formalisation

SPEC.v3 placed `skills/`, `agents/`, and `_tools/` inside the vault; the Ginarr deployment moved them out (skills/agents into `.claude/`, tools into repo-root `tools/`). Also missing from v3's directory map: the `notes/reference/` directory, which is in use. A v4 revision should reconcile these, re-publish the directory layout, and keep `logs/` and `notes/` as the only portable data dirs.

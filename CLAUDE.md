# Ginarr — chat-memory

## Ground rules (read first)

- **Language.** All documentation, comments, commit messages, code identifiers, and other artifacts committed to this repo are in **English**. Conversation with the user is not covered by this rule and may be in any language.
- **Docs stay in sync.** Operator documentation lives under [`docs/`](docs/index.md). Every directory there carries an `index.md`. When you add, modify, or remove a script, hook, or skill, update the matching doc **and** the parent `index.md` in the **same commit** that touches the code. Out-of-date docs are worse than missing ones.
- **Current bot state lives in `docs/`, not here.** `CLAUDE.md` holds stable project conventions and invariants; the moving target (what's wired right now) is maintained there.

A vendor-neutral long-term memory system for a single-user, always-on LLM personal assistant. The canonical spec is `SPEC.v3.md`. Earlier drafts (`SPEC.md` = v1, `SPEC.v2.md`) are kept for history — do not edit them. New revisions go as `SPEC.vN.md`.

## What this project is

A file-based memory layer that lives as plain Markdown + JSONL, readable by any agent runtime. The reference deployment is a Telegram bot running as a long-lived process on a server, with one owner as the only user. Memory survives process restarts, runtime migrations, and years of use.

No embeddings, no vector DB, no vendor-specific storage.

## Runtime targets

- **Reference runtime:** Claude Code.
- **Supported migration targets** (same skill/agent format): Junie, OpenCode with the `oh-my-opencode` plugin.
- **Out of scope:** Cursor (different skill model). Do not produce Cursor-specific advice.

## Directory layout

Behavior (scripts, hooks, skills) lives in **this repo** under `.claude/`. Data (logs, notes) lives in a **separate** vault at `$GINARR_VAULT_ROOT` — by default `~/obsidian-vaul/chat-memory/`. The split is deliberate: data is format-portable and long-lived; behavior is runtime-specific and replaceable.

Current wiring is documented in [`docs/architecture.md`](docs/architecture.md). SPEC.v3's original layout put `skills/`, `agents/`, and `_tools/` inside the vault — that is superseded, pending formalisation in SPEC v4.

## Core design principles

Read `SPEC.v3.md` for the full spec. These are the load-bearing invariants — do not violate them without an explicit revision:

- **Event log is a natural chat transcript.** Roles are only `user | assistant | system`. No `tool_call` / `tool_result` events. `content` is always a string. Attachments are referenced inline as `[image: path]` / `[file: path]` / `[audio: path]`. Tool internals are not part of the history.
- **UTC everywhere.** Log `ts`, filenames, frontmatter dates, resolved relative dates. Local-time interpretation is a query-time concern, not a storage concern. No `OWNER_TZ` config.
- **Append-only is a writer-side discipline**, not cryptographic immutability. Manual scrubbing of secrets is the documented escape hatch.
- **Ordering** = file position. `ts` is displayed time. On ties, file order wins.
- **No session_id / no turn.** Always-on single-owner bot has no meaningful session lifecycle. Don't reintroduce these fields.
- **One topic = one file** in `notes/`. Filenames are **snake_case** (mandatory, not optional). Primary dedup mechanism.
- **Conflict detection is agent judgment**, not an algorithm. The spec prescribes the resolution protocol, not a detector.
- **OWNER_ID enforcement** is adapter-level only. Skills trust they run in an owner-authenticated process.
- **Layer 1 (path denylist)** is runtime-level access control via pre-tool hook. On hook-less runtimes it degrades to convention.

## Naming and language conventions

- Note filenames: `snake_case.md`.
- Directory names in the vault: neutral (`logs`, `notes`, `skills`, `agents`, `_tools`) — no `claude_*`, `gpt_*`, `anthropic_*`, `openai_*`.
- `_tools/` scripts: one file, one language, pure Python/Node, no LLM-SDK dependencies.
- Reserved `system` event `content` identifiers (snake_case): `bot_started`, `bot_stopped`, `log_paused`, `log_resumed`, `hook_error`, `consolidation_run`.

## Anti-patterns (do not suggest these)

- RAG / embeddings / vector index — spec explicitly rejects these; `grep` is the search mechanism.
- ML-based PII detection — spec rejects; regex layers 1-4 only.
- Retroactive rescan of historical logs for secrets — creates false sense of safety.
- Versioning `logs/` in git — manual redactions leak through history; not recommended.
- Internal bot scheduler for consolidation — breaks portability. Use system cron / systemd timer.
- Multi-user or group-chat extensions — explicitly out of scope.

## Git workflow for this repo

- Remote: `git@github.com:ypeskov/Ginarr-new.git` (SSH via existing `id_ed25519`).
- Git identity is **not configured** globally or locally. Commits use inline `-c user.name="Yuriy Peskov" -c user.email="yuriy.peskov@gmail.com"`.
- Co-authored commits with Claude are acceptable (see initial commit for format).
- Default branch: `main`.

## Current state

See [`docs/`](docs/index.md) — tracked there alongside the code it describes.

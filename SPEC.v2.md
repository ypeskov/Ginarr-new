# chat-memory

A vendor-neutral long-term memory system for a single-user LLM personal assistant.

**Status:** experimental / opinionated draft.
**Revision:** v2 (replaces v1 in `SPEC.md`).

## Purpose

`chat-memory` is a file-based memory layer for a personal assistant running on top of an LLM agent runtime (Claude Code, OpenCode, Cursor, Junie, etc.). The assistant is expected to be **always-on** (e.g. a Telegram bot running in a long-lived process on a server), with **one owner** as the only user.

Data is stored as plain Markdown and JSONL, readable by any agent that understands those formats. No vendor-specific storage, no embeddings, no database. If you switch runtimes — or move to a local LLM later — the memory moves with you intact and human-readable.

## Scope

**In scope**
- Long-running personal-assistant conversations: advice, planning, reflection, decisions, facts about the owner.
- Continuity across process restarts and across months.
- Single owner, single conversational stream (one bot, one user).

**Out of scope**
- Per-repository coding memory — lives with each codebase (`.claude/`, `.cursor/`, `AGENTS.md`, etc.), not here.
- Multi-user or group-chat memory.
- Large binary assets — only text and small attachments.

## Assumed runtime

- One long-running agent process (e.g. `claude --channels` inside tmux).
- Messages arrive through a single channel (Telegram in the reference setup).
- Owner identity is pinned in configuration (`OWNER_ID`); every memory-touching skill checks it before acting.

## Directory layout

```
chat-memory/
├── SPEC.md
├── _tools/              — portable scripts, no agent dependency
│   ├── redactor.py
│   ├── consolidate.py
│   └── search.py
├── skills/              — Agent Skills (portable across CC, Cursor, OpenCode, Junie)
├── agents/              — subagent definitions (portable)
├── logs/                — raw event log
│   └── YYYY/
│       └── MM/
│           ├── YYYY-MM-DD.jsonl
│           └── attachments/
│               └── YYYY-MM-DD_<hash>.<ext>
├── notes/               — curated knowledge
│   ├── user/            — facts about the owner
│   ├── feedback/        — how to work with the owner
│   ├── projects/        — ongoing life projects
│   ├── decisions/       — decisions with rationale
│   ├── archive/         — retired / superseded notes
│   └── _pending.md      — digest candidates awaiting review
└── _index.md            — navigation, entry points
```

## Event log (JSONL)

One file per day: `logs/YYYY/MM/YYYY-MM-DD.jsonl`. Each line is one event. Append-only.

### Required fields

| Field | Type | Notes |
|---|---|---|
| `ts` | ISO 8601 string | UTC, sub-second precision (`2026-04-24T14:32:01.123Z`) |
| `role` | enum | `user`, `assistant`, `tool_call`, `tool_result`, `system` |
| `content` | string or array | Plain text, or array of blocks `{type, text\|...}` |

That's it. Order is implied by `ts`.

### Optional `meta` object

| Field | Purpose |
|---|---|
| `model` | Model identifier (for provenance) |
| `tool_name` | Name of the tool invoked (e.g. `save_memory`, `search_memory`, `web_fetch`) |
| `tool_call_id` | Correlates `tool_call` → `tool_result` when interleaved with other events |
| `thinking` | Reasoning trace, if the model provides one |
| `tokens` | `{in, out}` for cost tracking |

### `system` role

Reserved for non-conversational events: `bot_started`, `bot_stopped`, `hook_error`, `consolidation_run`, `log_paused`. Keeps lifecycle signals out of chat history while preserving them in the timeline.

### Rules

- **Append-only.** Never edit existing lines. Corrections go into notes.
- **Day boundary rolls the file.** An event is written to the file matching its date. Pick one timezone policy (UTC or local) and stick to it — the reference setup uses owner-local for filename, UTC for `ts`.
- **Parallel writers.** Writes under 4 KB are atomic via `O_APPEND` on POSIX. Relevant mostly for maintenance scripts (consolidation, archive) running alongside the live bot. Larger tool results must be split or written under a lock.
- **One line = one valid JSON + newline.** Parsers skip malformed lines.
- **Context compaction.** If the agent compacts its in-memory context, log the original events — not the generated summary.

### On not having `session_id` or `turn`

An always-on single-owner bot has no natural session lifecycle and no meaningful per-session counter. Timestamps with sub-second precision are enough for ordering; restart boundaries are captured as `system` events (`bot_stopped`, `bot_started`). If a "conversation" ever needs to be reconstructed as a contiguous block (e.g. for note linking), it can be derived from timestamp gaps at read time — no schema field required.

## Notes (Markdown + YAML frontmatter)

### Required frontmatter

```yaml
---
type: user | feedback | project | reference | decision
name: short handle
description: one line — why this note exists
created: 2026-04-24
updated: 2026-04-24
---
```

### Optional frontmatter

```yaml
tags: [health, finance]
source: logs/2026/04/2026-04-24.jsonl#ts=2026-04-24T14:32:01Z..2026-04-24T14:47:12Z
status: confirmed | unconfirmed
supersedes: user/previous_note.md
```

`source:` now references a timestamp range inside a log file, since there is no session_id.

### Body conventions

`feedback` and `project` notes follow this structure:

```markdown
Primary rule / fact / decision in one sentence.

**Why:** the reason (past incident, constraint, stated preference).

**How to apply:** when and where this guidance kicks in.
```

`user`, `reference`, and `decision` notes use free-form prose — keep it terse.

### File naming

- **Filename is the topic key, not an event.**
  Good: `user_languages.md`, `feedback_tone.md`, `project_marathon_training.md`.
  Bad: `2026-04-24_chat_about_running.md`.
- **One topic = one file.** Primary dedup mechanism.
- Consistent casing vault-wide (kebab-case or snake_case; pick one).

## Policies

### Deduplication

- **Search before write.** Before creating a note, grep for matching topic/tags. If a file exists, update it.
- **Hybrid structure.** Slot-like data (tags, timestamps) in frontmatter; narrative in body.
- **Consolidation pass.** On command or on schedule: merge duplicates, refresh outdated facts, move retired projects to `notes/archive/`.
- **Conflicts.** Never silently overwrite. Keep both values with timestamps, mark `status: unconfirmed`, surface for resolution.

### Capture rules

| Confidence | Examples | Mechanism |
|---|---|---|
| High | Explicit "remember X", explicit feedback ("don't do Y"), factual statements about the owner, confirmed decisions | Auto-save silently |
| Medium | Indirect preferences, one-off choices | Auto-save with `status: unconfirmed`. Confirm lazily on first real application |
| Low / ambiguous | Speculation, thinking out loud | Append to `notes/_pending.md`. Surface for review at a natural break — max 3–5 candidates, one-click [y / n / edit] |

Always ask immediately (even in batch mode) when:
- The new fact contradicts an existing note.
- The fact involves external stakeholders (deadlines, people, commitments).
- The content borders on sensitive data.

Never save:
- Ephemeral task state.
- Information trivially derivable from existing notes.
- Low-confidence hunches.

### Secrets and PII

Four layers, enforced by the agent's tool layer.

**Layer 1 — path denylist (pre-read hook).**
Contents of these paths never reach the log:
`.env*`, `*.pem`, `*.key`, `id_rsa*`, `credentials*`, `~/.ssh/**`, `~/.aws/**`, `~/.config/gcloud/**`, `~/.kube/config`.
Log records `[REDACTED: path in denylist]` instead.

**Layer 2 — regex filter on write.**
Applied to every event (`user`, `assistant`, `tool_call`, `tool_result`) before persistence.

Known token formats:
- AWS: `AKIA[0-9A-Z]{16}`, `ASIA[0-9A-Z]{16}`
- GitHub: `ghp_[0-9a-zA-Z]{36}`, `gho_`, `ghs_`
- OpenAI-style: `sk-[a-zA-Z0-9]{20,}`
- Slack: `xox[baprs]-[0-9a-zA-Z-]+`
- Stripe: `sk_live_[0-9a-zA-Z]{24}`
- Connection strings: `(postgres|mysql|redis|mongodb)://[^:]+:[^@]+@`
- PEM blocks: `-----BEGIN .* PRIVATE KEY-----[\s\S]*?-----END`
- Generic: `(?i)(api[_-]?key|token|secret|password)["\s:=]+[^\s"']{12,}`

Matches are replaced with `[REDACTED:<category>]`, not `***` — preserves debuggability.

**Layer 3 — process-local denylist (owner-marked).**
Syntax: `/redact <value>` command, or inline `<secret>value</secret>` tag.
All occurrences of `value` within the current process lifetime are replaced with `[REDACTED:user-marked]` on write.
The list resets on restart.

**Layer 4 — `/nolog` flag.**
Logging is paused until `/nolog off` or process restart. A `system` event `{event: "log_paused"}` / `{event: "log_resumed"}` records the window boundaries. Content inside the window is not persisted.

**Deliberately not implemented:**
- **Retroactive rescan of historical logs** — creates a false sense of safety; leaked secrets are already in backups, cloud sync, and git history.
- **ML-based PII detection** — unpredictable signal-to-noise.
- **Whitelist-only writes** — unrealistic for arbitrary conversation.

**Accept the limit.** Regex cannot catch proprietary token formats. For truly sensitive material, use `/nolog` or keep it out of chat entirely.

### Time boundaries

- **Day boundary rolls the file.** Nothing else does.
- **No session concept.** Topic structure lives in notes, not in the log.
- **Cross-day continuity** goes through notes, not by re-reading old JSONL. Logs are the archive; notes are the working memory.

## Search

Search notes first, logs second.

- Notes: `grep -r <keyword> notes/` plus frontmatter tag queries.
- Logs: `grep -r <keyword> logs/YYYY/` with an explicit date scope.
- A note's `source:` field points to the originating day and time range.
- Reconstruct a time slice: `jq 'select(.ts >= "..." and .ts < "...")' <file>`.

No RAG or embeddings. At realistic volumes (tens of MB per year) direct grep is faster than maintaining a vector index, and the failure modes are human-debuggable.

## Vendor neutrality

The system separates **data** (permanent, neutral) from **code** (agent-specific, replaceable).

### Portable across agents (lives inside the vault)

| Artifact | Portability |
|---|---|
| Data in `logs/` and `notes/` | Any agent that reads text |
| Agent Skills in `skills/` | Claude Code, Cursor, OpenCode, Junie (same format) |
| Subagent definitions in `agents/` | Claude Code, OpenCode, Junie (same format) |
| Slash command files | File format portable; invocation context varies |
| Scripts in `_tools/` | Pure Python/Node, no LLM-SDK dependency |
| MCP servers | Protocol supported by multiple agents |

### Agent-specific (rewritten on switch)

| Artifact | Where it lives |
|---|---|
| Hook configuration | `settings.json` — hook events, matchers |
| MCP server wiring | `settings.json` config blocks |
| Global agent permissions / env | `settings.json` |
| Hook-driven automation glue | Whatever the hooks invoke |

### Migration procedure

1. Copy `chat-memory/` to the new environment.
2. Wire the new agent's hooks to invoke `_tools/` scripts.
3. Register `skills/` and `agents/` in the new agent's discovery path.
4. Run a smoke interaction before trusting auto-save.

### Naming discipline

- `role` values: strictly `user | assistant | tool_call | tool_result | system`.
- `type` values: strictly from the Notes enum.
- Directory names: `logs`, `notes`, `skills`, `agents`, `_tools` — no `claude_*`, `gpt_*`, `anthropic_*`, `openai_*`.
- Tool names in logs (e.g. `save_memory`, `search_memory`) recorded verbatim.

## Operational conventions

- Log timestamps: UTC, ISO 8601, sub-second precision.
- Dates in filenames and frontmatter: owner-local (for readability in file listings).
- Relative dates in user messages ("yesterday", "next Thursday") converted to absolute dates on save.
- Paths in `source:` fields are relative to `chat-memory/`.
- Attachments live alongside their day's log.

## Portable tools (`_tools/`)

CLI utilities with no agent dependency. Invoked from hooks.

| Script | Purpose |
|---|---|
| `redactor.py <infile> > <outfile>` | Applies Layer 2 (regex) + Layer 3 (owner-marked denylist via `--denylist-file`) |
| `consolidate.py [--dry-run \| --apply]` | Scans for duplicate notes by tag/name, proposes merges |
| `search.py <query> [--scope notes\|logs] [--since <date>]` | Unified grep with frontmatter awareness |
| `archive.py --older-than <duration>` | Moves retired projects to `notes/archive/` |

Contract: each script is one file, one language, reads stdin/args, writes stdout. No LLM-SDK dependencies. Portable between environments.

## Changelog from v1

- Renamed `sessions/` → `logs/`. "Session" is no longer a first-class concept.
- Removed `session_id` and `turn` from required fields. Ordering is by `ts`.
- Added `system` role for lifecycle events (`bot_started`, `bot_stopped`, `log_paused`, etc.).
- Added explicit "Assumed runtime" section pinning single-owner, always-on, single-channel assumption.
- Removed residual coding-agent framing in Purpose and "Never save".
- `source:` field now uses time ranges instead of `session_id` + `turn` ranges.
- "Session boundaries" → "Time boundaries".
- `/redact` scope is now process lifetime (resets on restart), not session.
- `/nolog` is a window inside the log rather than a session-level flag; boundaries recorded as `system` events.

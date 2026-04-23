# chat-memory

A vendor-neutral long-term memory system for LLM-based personal assistants.

**Status:** experimental / opinionated draft.

## Purpose

`chat-memory` is a file-based memory layer for personal assistants built on top of coding agents (Claude Code, OpenCode, Cursor, Junie, etc.). It preserves conversation history and curated knowledge across sessions in a format readable by any agent that understands Markdown, YAML, and JSONL. No vendor-specific storage, no embeddings, no database.

If you switch agents — or run a local LLM in the future — your memory comes with you, intact and human-readable.

## Scope

**In scope**
- Long-running personal-assistant conversations: advice, planning, reflection, decisions, facts about the user.
- Cross-session continuity for a single "assistant persona".

**Out of scope**
- Per-repository coding memory — that belongs with each codebase (`.claude/`, `.cursor/`, etc.).
- Large binary assets — only text and small attachments.

## Directory layout

```
chat-memory/
├── SPEC.md                   — this document
├── _tools/                   — portable scripts (no agent dependency)
│   ├── redactor.py
│   ├── consolidate.py
│   └── search.py
├── skills/                   — Agent Skills (portable across CC, Cursor, OpenCode, Junie)
├── agents/                   — subagent definitions (portable)
├── sessions/
│   └── YYYY/
│       └── MM/
│           ├── YYYY-MM-DD.jsonl
│           └── attachments/
│               └── YYYY-MM-DD_<hash>.<ext>
├── notes/
│   ├── user/                 — facts about the user
│   ├── feedback/             — how to work with the user
│   ├── projects/             — ongoing life projects (not code repos)
│   ├── decisions/            — decisions with rationale
│   ├── archive/              — retired / superseded notes
│   └── _pending.md           — end-of-session digest candidates
└── _index.md                 — navigation, entry points
```

## Session logs (JSONL)

One file per day: `sessions/YYYY/MM/YYYY-MM-DD.jsonl`. Each line is one event. Append-only.

### Required fields

| Field | Type | Notes |
|---|---|---|
| `ts` | ISO 8601 string | UTC timestamp |
| `session_id` | string | Opaque identifier — one agent process = one `session_id` |
| `turn` | integer | Monotonic within a session |
| `role` | enum | `user`, `assistant`, `tool_call`, `tool_result` |
| `content` | string or array | Plain text, or array of blocks `{type, text\|...}` |

### Optional `meta` object

| Field | Purpose |
|---|---|
| `model` | Model identifier (for provenance) |
| `tool_name` | Name of the tool invoked (`Bash`, `Read`, ...) |
| `tool_call_id` | Correlates `tool_call` → `tool_result` |
| `thinking` | Reasoning trace, if the model provides one |
| `tokens` | `{in, out}` for cost tracking |

### Rules

- **Append-only.** Never edit existing lines. Corrections go into notes, not into the log.
- **Crossing midnight.** A session that starts on day N and continues past midnight keeps its `session_id`; later events are appended to day N+1's file. Rejoin by `session_id` on read.
- **Parallel writers.** Writes under 4 KB are atomic via `O_APPEND` on POSIX. Larger tool results must be split or written under a lock.
- **One line = one valid JSON + newline.** Parsers skip malformed lines.
- **Compaction.** If the agent compacts context, log the original events — not the generated summary.

## Notes (Markdown + YAML frontmatter)

### Required frontmatter

```yaml
---
type: user | feedback | project | reference | decision
name: short handle
description: one line — why this note exists
created: 2026-04-23
updated: 2026-04-23
---
```

### Optional frontmatter

```yaml
tags: [python, testing]
source: sessions/2026/04/2026-04-23.jsonl#session_id=abc123&turn=12-18
status: confirmed | unconfirmed
supersedes: user/previous_note.md
```

### Body conventions

`feedback` and `project` notes must follow this structure:

```markdown
Primary rule / fact / decision in one sentence.

**Why:** the reason (past incident, constraint, stated preference).

**How to apply:** when and where this guidance kicks in.
```

`user`, `reference`, and `decision` notes use free-form prose — keep it terse.

### File naming

- **Filename is the topic key, not an event.**
  Good: `user_languages.md`, `feedback_testing.md`, `project_marathon_training.md`.
  Bad: `2026-04-23_chat_about_python.md`.
- **One topic = one file.** This is the primary dedup mechanism — two agents cannot independently create "the same" note under different names.
- Use consistent casing vault-wide (kebab-case or snake_case; pick one).

## Policies

### Deduplication

- **Search before write.** Before creating a new note, grep for matching topic/tags. If a file exists, update it in place.
- **Hybrid structure.** Slot-like data (role, languages, tags, timestamps) in frontmatter; narrative (reasoning, context) in the body.
- **Consolidation pass.** Every N sessions, or on command: merge duplicates, refresh outdated facts, move retired projects to `notes/archive/`.
- **Conflicts.** Never silently overwrite. Keep both values with timestamps, mark `status: unconfirmed`, surface for resolution.

### Capture rules

What gets saved and how we decide:

| Confidence | Examples | Mechanism |
|---|---|---|
| High | Explicit "remember X", explicit feedback ("don't do Y"), factual statements about the user, confirmed decisions | Auto-save silently |
| Medium | Indirect preferences, one-off technical choices | Auto-save with `status: unconfirmed`. Confirm lazily on first real application |
| Low / ambiguous | Speculation, task context | Append to `notes/_pending.md`. Review at session end — max 3–5 candidates, one-click [y / n / edit] |

Always ask immediately (even in batch mode) when:
- The new fact contradicts an existing note.
- The fact involves external stakeholders (deadlines, people, commitments).
- The content borders on sensitive data.

Never save:
- Ephemeral task state.
- Information trivially derivable from current code or project files.
- Duplicates of existing `CLAUDE.md` / `AGENTS.md` / `README.md` content.
- Low-confidence hunches.

### Secrets and PII

Four layers, enforced by the agent's tool layer:

**Layer 1 — path denylist (pre-read hook).**
These paths never reach the log as content:
`.env*`, `*.pem`, `*.key`, `id_rsa*`, `credentials*`, `~/.ssh/**`, `~/.aws/**`, `~/.config/gcloud/**`, `~/.kube/config`.
The log records `[REDACTED: path in denylist]` instead of the file's content.

**Layer 2 — regex filter on write.**
Applied to every event (user, assistant, tool_call, tool_result) before persistence.

Known token formats:
- AWS: `AKIA[0-9A-Z]{16}`, `ASIA[0-9A-Z]{16}`
- GitHub: `ghp_[0-9a-zA-Z]{36}`, `gho_`, `ghs_`
- OpenAI-style: `sk-[a-zA-Z0-9]{20,}`
- Slack: `xox[baprs]-[0-9a-zA-Z-]+`
- Stripe: `sk_live_[0-9a-zA-Z]{24}`
- Connection strings: `(postgres|mysql|redis|mongodb)://[^:]+:[^@]+@`
- PEM blocks: `-----BEGIN .* PRIVATE KEY-----[\s\S]*?-----END`
- Generic: `(?i)(api[_-]?key|token|secret|password)["\s:=]+[^\s"']{12,}`

Matches are replaced with `[REDACTED:<category>]`, not `***` — this preserves debuggability.

**Layer 3 — session-local denylist (user-marked).**
Syntax: `/redact <value>` command, or inline `<secret>value</secret>` tag.
All occurrences of `value` within the current session are replaced with `[REDACTED:user-marked]` on write.
The list lives per-session and is not shared across sessions.

**Layer 4 — `/nolog` session flag.**
The current session is not persisted at all. Only a stub is recorded: `{session_id, started_at, ended_at, content: "[session redacted]"}`.
Scope: until process exit or `/clear`. Defaults to `off` (safer).

**Deliberately not implemented:**
- **Retroactive rescan of historical logs** — creates a false sense of safety; leaked secrets are already in backups, cloud sync, and git history.
- **ML-based PII detection** — unpredictable signal-to-noise.
- **Whitelist-only writes** — unrealistic for arbitrary coding/conversation sessions.

**Accept the limit.** Regex cannot catch proprietary token formats. For truly sensitive workflows, use `/nolog` or a separate unsynced vault.

### Session boundaries

- **A day boundary rolls the file**, not the session.
- **A session is one agent process**, identified by `session_id` (UUID generated at start).
- **No automatic topic segmentation inside a session.** Topic structure lives in notes, not logs.
- **Cross-session continuity** goes through notes, not by re-reading old JSONL. JSONL is the archive; notes are the working memory.

## Search

Search notes first, sessions second.

- Notes: `grep -r <keyword> notes/` plus frontmatter tag queries.
- Sessions: `grep -r <keyword> sessions/YYYY/` with an explicit date scope.
- A note's `source:` field points to the originating session file and turn range.
- Reconstruct a full session: `jq 'select(.session_id=="abc123")' <file>`.

No RAG or embeddings. At realistic volumes (tens of MB per year) direct grep is faster than maintaining a vector index, and the failure modes are human-debuggable.

## Vendor neutrality

The system separates **data** (permanent, neutral) from **code** (agent-specific, replaceable).

### Portable across agents (lives inside the vault)

| Artifact | Portability |
|---|---|
| Data in `sessions/` and `notes/` | Any agent that can read text |
| Agent Skills in `skills/` | Claude Code, Cursor, OpenCode, Junie (same format) |
| Subagent definitions in `agents/` | Claude Code, OpenCode, Junie (same format) |
| Slash command files | File format portable; invocation context varies by agent |
| Scripts in `_tools/` | Pure Python/Node, no LLM-SDK dependency |
| MCP servers | Protocol supported by multiple agents |

### Agent-specific (rewritten on switch)

| Artifact | Where it lives |
|---|---|
| Hook configuration | `settings.json` — `PreToolUse`, `PostToolUse`, `Stop`, matchers |
| MCP server wiring | `settings.json` config blocks |
| Global agent permissions / env | `settings.json` |
| Hook-driven automation glue | Whatever the hooks invoke |

### Migration procedure

1. Copy `chat-memory/` verbatim to the new environment.
2. Wire the new agent's hooks to invoke `_tools/` scripts.
3. Register `skills/` and `agents/` in the new agent's discovery path.
4. Run a smoke session before trusting auto-save.

### Naming discipline

- `role` values: strictly `user | assistant | tool_call | tool_result`.
- `type` values: strictly from the enum in the Notes section.
- Directory names: `sessions`, `notes`, `skills`, `agents`, `_tools` — no `claude_*`, `gpt_*`, `anthropic_*`, `openai_*`.
- Tool names in logs (`Bash`, `Read`) are recorded verbatim — any reader understands them as "there was a tool by this name".

## Operational conventions

- Timestamps in logs: UTC, ISO 8601.
- Dates in filenames and frontmatter: user-local (for readability in file listings).
- Relative dates in user messages ("yesterday", "next Thursday") are converted to absolute dates on save.
- Paths in `source:` fields are relative to `chat-memory/`.
- Attachments live alongside their day's log: `sessions/YYYY/MM/attachments/YYYY-MM-DD_<hash>.<ext>`.

## Portable tools (`_tools/`)

CLI utilities with no agent dependency. Invoked from hooks.

| Script | Purpose |
|---|---|
| `redactor.py <infile> > <outfile>` | Applies Layer 2 (regex) + Layer 3 (session denylist via `--denylist-file`) |
| `consolidate.py [--dry-run \| --apply]` | Scans for duplicate notes by tag/name, proposes merges |
| `search.py <query> [--scope notes\|sessions] [--since <date>]` | Unified grep with frontmatter awareness |
| `archive.py --older-than <duration>` | Moves retired projects to `notes/archive/` |

Contract: each script is one file, one language, reads stdin/args, writes stdout. No LLM-SDK dependencies. Portable between environments.

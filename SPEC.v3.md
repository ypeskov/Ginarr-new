# chat-memory

A vendor-neutral long-term memory system for a single-user LLM personal assistant.

**Status:** experimental / opinionated draft.
**Revision:** v3 (replaces v2 in `SPEC.v2.md`).

## Purpose

`chat-memory` is a file-based memory layer for a personal assistant running on top of an LLM agent runtime. The assistant is expected to be **always-on** (e.g. a Telegram bot running in a long-lived process on a server), with **one owner** as the only user.

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
- Owner identity is pinned in configuration (`OWNER_ID`). The channel adapter is the **sole enforcement point**: non-owner messages are dropped before reaching the agent. Memory-touching skills trust that they run only in an owner-authenticated process and perform no secondary check. Adding a new inbound channel means adding its `OWNER_ID` filter — an architectural requirement of the channel adapter, not of individual skills.
- **Reference runtime:** Claude Code. Junie and OpenCode (with the `oh-my-opencode` plugin) are supported migration targets sharing the same skill/agent model. Cursor is out of scope.

## Directory layout

```
chat-memory/
├── SPEC.md
├── _tools/              — portable scripts, no agent dependency
│   ├── redactor.py
│   ├── consolidate.py
│   └── search.py
├── skills/              — Agent Skills (portable across CC, Junie, OpenCode+oh-my-opencode)
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
| `role` | enum | `user`, `assistant`, `system` |
| `content` | string | Plain text. For attachments, use inline markers (see below). |

### Optional `meta` object

| Field | Purpose |
|---|---|
| `model` | Model identifier (for provenance) |
| `thinking` | Reasoning trace, if the model provides one |
| `tokens` | `{in, out}` for cost tracking |

Additional fields are permitted for `system` events — see below.

### Ordering

Events are ordered by their position in the file. `ts` is the displayed time. When two events share the same `ts` (rare under sub-second resolution, single-writer), **file order is authoritative**.

### Attachments

Binary content (images, files) is stored alongside the day's log at `logs/YYYY/MM/attachments/YYYY-MM-DD_<hash>.<ext>`. In the event `content`, attachments are referenced inline:

```json
{"ts":"2026-04-24T14:32:01.123Z","role":"user","content":"look at this [image: attachments/2026-04-24_abc123.jpg]"}
```

Markers: `[image: path]`, `[file: path]`, `[audio: path]`. Paths are relative to the `logs/YYYY/MM/` directory containing the event.

### `system` role

Reserved for non-conversational events. `content` is a short snake_case event identifier; structured details go in `meta`.

Reserved identifiers:

| `content` | Purpose |
|---|---|
| `bot_started` | Process boot |
| `bot_stopped` | Graceful shutdown (best-effort — see below) |
| `log_paused` | `/nolog` window opened |
| `log_resumed` | `/nolog` window closed |
| `hook_error` | Hook / tool-layer failure; details in `meta.hook`, `meta.error` |
| `consolidation_run` | Maintenance script ran; details in `meta` |

Future identifiers: snake_case, lowercase.

#### `bot_stopped` is best-effort

Written on graceful shutdown (SIGTERM, clean exit); cannot be written on crash (SIGKILL, OOM, power loss).

The authoritative lifecycle marker is `bot_started`. When reading the log:

- `bot_started` → ... → `bot_stopped` → ... → `bot_started` = clean restart cycle.
- `bot_started` → ... → `bot_started` (no `bot_stopped` in between) = previous process crashed.

### Rules

- **Append-only** (writer-side discipline, not immutability — see "Manual redaction").
- **Day boundary rolls the file.** An event is written to the file matching its UTC date.
- **Parallel writers.** Writes under 4 KB are atomic via `O_APPEND` on POSIX. Relevant mostly for maintenance scripts (consolidation, archive) running alongside the live bot. Larger tool results must be split or written under a lock.
- **One line = one valid JSON + newline.** Parsers skip malformed lines.
- **Context compaction.** If the agent compacts its in-memory context, log the original events — not the generated summary.

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

`source:` references a time range inside a log file. Ranges are **inclusive on both ends**: `#ts=X..Y` covers all events with `X <= ts <= Y`.

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
- **`snake_case.md` is mandatory** — consistency across the vault is enforced, not optional. Without it, dedup grep misses near-duplicates like `user_languages.md` vs. `user-languages.md`.

## Policies

### Deduplication

- **Search before write.** Before creating a note, grep for matching topic/tags. If a file exists, update it.
- **Hybrid structure.** Slot-like data (tags, timestamps) in frontmatter; narrative in body.
- **Consolidation pass.** On command or on schedule (see "Consolidation triggers"): merge duplicates, refresh outdated facts, move retired projects to `notes/archive/`.

### Conflict resolution

Conflict detection is the **agent's judgment during read-before-write**, not a deterministic algorithm. When the agent, while updating an existing note, judges that a new claim contradicts an existing claim:

1. Do not overwrite. Keep both claims in the note body, each annotated with the date it was recorded.
2. Set `status: unconfirmed` in frontmatter.
3. Surface the conflict to the owner at the next natural break (per the "Always ask immediately" rule below — contradictions trigger immediate ask).
4. When the owner resolves it, remove the losing claim, drop `unconfirmed`.

### Capture rules

| Confidence | Examples | Mechanism |
|---|---|---|
| High | Explicit "remember X", explicit feedback ("don't do Y"), factual statements about the owner, confirmed decisions | Auto-save silently |
| Medium | Indirect preferences, one-off choices | Auto-save with `status: unconfirmed`. Confirm lazily on first real application |
| Low / ambiguous | Speculation, thinking out loud | Append to `notes/_pending.md`. Review via `/review` (see "Pending review") |

Always ask immediately (even in batch mode) when:
- The new fact contradicts an existing note.
- The fact involves external stakeholders (deadlines, people, commitments).
- The content borders on sensitive data.

Never save:
- Ephemeral task state.
- Information trivially derivable from existing notes.
- Low-confidence hunches (those go to `_pending.md`, not `notes/`).

### Pending review

Low-confidence candidates accumulate in `notes/_pending.md`. Review is triggered by:

- **`/review` slash command** (owner-initiated, primary mechanism).
- **Threshold notification.** When ≥5 candidates accumulate, the bot posts a single unobtrusive message inviting review. No auto-review. No repeat nudges.

Each candidate offers three actions: **confirm** (save as a note), **drop** (discard), **edit** (modify then confirm). The UI widget is channel-specific — in Telegram, inline keyboard buttons; in other channels, equivalent one-input confirmation. The spec mandates the three actions, not the widget.

### Consolidation triggers

`_tools/consolidate.py` is a standalone CLI script. Scheduling uses system-level mechanisms:

- **System cron / systemd timer** (primary). Vendor-neutral, survives bot downtime. A typical recipe runs weekly. Parallel writes with the live bot rely on `O_APPEND` atomicity for sub-4KB events (see "Parallel writers").
- **`/consolidate` slash command** (optional). Owner-triggered inline for ad-hoc runs.

The bot process itself does not run an internal scheduler — relying on runtime-specific schedulers would break portability.

**First-run recipe:** `--dry-run` → owner reviews proposals → `--apply`. Do not schedule `--apply` in cron without at least one prior dry-run review.

### Secrets and PII

Four layers.

**Layer 1 — path denylist (runtime access control).**
The agent runtime is configured to deny tool access (`Read`, `Bash`, equivalent) to these paths:
`.env*`, `*.pem`, `*.key`, `id_rsa*`, `credentials*`, `~/.ssh/**`, `~/.aws/**`, `~/.config/gcloud/**`, `~/.kube/config`.

Denied reads return a stub (`[REDACTED: path in denylist]`) to the agent. The secret never enters the context, so cannot be leaked via reply or thinking trace.

**Runtime dependency.** Layer 1 requires runtime support for pre-tool interception (e.g., Claude Code `PreToolUse` hook). On runtimes without this capability, Layer 1 degrades to a **convention** — skill authors must avoid reading denylisted paths — and enforcement falls back to Layers 2–4.

**Layer 2 — regex filter on write.**
Applied to every `user` and `assistant` event (including `meta.thinking`) before persistence.

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
Logging is paused until `/nolog off` or process restart. `system` events `{content: "log_paused"}` and `{content: "log_resumed"}` record the window boundaries. Content inside the window is not persisted.

**Manual redaction (escape hatch).**
Append-only is a writer-side discipline, not an immutability guarantee. If a secret or piece of content slipped past Layers 1–4 and must be scrubbed post-hoc:

1. Open the day's log file in a text editor.
2. Replace the `content` (and any leaky `meta` fields) of the offending line with `[REDACTED:manual]`. Preserve the line itself — keep `ts`, `role`, structural envelope — so the timeline stays intact.
3. The scrub does not propagate to backups, sync copies, or version control history.

Manual redaction is expected to be rare. If it becomes frequent, tighten Layers 1–3.

**Deliberately not implemented:**
- **Retroactive rescan of historical logs** — creates a false sense of safety; leaked secrets are already in backups, cloud sync, and git history.
- **ML-based PII detection** — unpredictable signal-to-noise.
- **Whitelist-only writes** — unrealistic for arbitrary conversation.

**Accept the limit.** Regex cannot catch proprietary token formats. For truly sensitive material, use `/nolog` or keep it out of chat entirely.

### Time boundaries

- **Day boundary rolls the file** (UTC). Nothing else does.
- **No session concept.** Topic structure lives in notes, not in the log.
- **Cross-day continuity** goes through notes, not by re-reading old JSONL. Logs are the archive; notes are the working memory.

## Search

Search notes first, logs second.

- Notes: `grep -r <keyword> notes/` plus frontmatter tag queries.
- Logs: `grep -r <keyword> logs/YYYY/` with an explicit date scope.
- A note's `source:` field points to the originating day and time range.
- Reconstruct a time slice: `jq 'select(.ts >= "..." and .ts <= "...")' <file>` (both ends inclusive, matching `source:` convention).

No RAG or embeddings. At realistic volumes (tens of MB per year) direct grep is faster than maintaining a vector index, and the failure modes are human-debuggable.

## Vendor neutrality

The system separates **data** (permanent, neutral) from **code** (agent-specific, replaceable).

### Portable across agents (lives inside the vault)

| Artifact | Portability |
|---|---|
| Data in `logs/` and `notes/` | Any agent that reads text |
| Agent Skills in `skills/` | Native in Claude Code, Junie, OpenCode+oh-my-opencode |
| Subagent definitions in `agents/` | Native in Claude Code, Junie, OpenCode+oh-my-opencode |
| Slash command files | File format portable; invocation context varies |
| Scripts in `_tools/` | Pure Python/Node, no LLM-SDK dependency |
| MCP servers | Protocol supported by multiple agents |

Data in `logs/` and `notes/` is fully portable. Enforcement of secret/PII redaction (Layer 1 especially) depends on the target runtime's hook capability. Migration to a hook-less runtime preserves the data but weakens Layer 1 to a convention.

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
4. Verify Layer 1 enforcement is configured on the new runtime (or accept it as convention-only).
5. Run a smoke interaction before trusting auto-save.

### Naming discipline

- `role` values: strictly `user | assistant | system`.
- `type` values: strictly from the Notes enum.
- Directory names: `logs`, `notes`, `skills`, `agents`, `_tools` — no `claude_*`, `gpt_*`, `anthropic_*`, `openai_*`.
- Filenames: `snake_case.md`, vault-wide.

## Operational conventions

- All timestamps and dates are **UTC**: log `ts`, filenames, frontmatter `created`/`updated`, resolved relative dates. No `OWNER_TZ` configuration.
- If the owner asks a time-scoped question in local terms ("yesterday between 2pm and 6pm Prague time"), the query tool translates local→UTC at query time; the storage layer stays UTC-pure.
- Relative dates in user messages ("yesterday", "next Thursday") are resolved to absolute UTC dates on save.
- Paths in `source:` fields are relative to `chat-memory/`.
- Attachments live alongside their day's log at `logs/YYYY/MM/attachments/`.
- `logs/` is not recommended for version control. If versioned anyway, assume manual redactions leak through history.

## Portable tools (`_tools/`)

CLI utilities with no agent dependency. Invoked from hooks or cron.

| Script | Purpose |
|---|---|
| `redactor.py <infile> > <outfile>` | Applies Layer 2 (regex) + Layer 3 (owner-marked denylist via `--denylist-file`) |
| `consolidate.py [--dry-run \| --apply]` | Scans for duplicate notes by tag/name, proposes merges |
| `search.py <query> [--scope notes\|logs] [--since <date>]` | Unified grep with frontmatter awareness |
| `archive.py --older-than <duration>` | Moves retired projects to `notes/archive/` |

Contract: each script is one file, one language, reads stdin/args, writes stdout. No LLM-SDK dependencies. Portable between environments.

## Changelog from v2

- **Event schema simplified.** `role` enum reduced to `user | assistant | system` — `tool_call` and `tool_result` removed. `content` is always a string; array-of-blocks form dropped. Attachments are referenced inline via `[image: path]` / `[file: path]` / `[audio: path]` markers. Rationale: the log is a natural chat transcript; tool internals are not part of that history.
- **`meta.tool_name` and `meta.tool_call_id` removed** as a consequence. `meta.thinking` kept as optional debug trace.
- **`system` event content format pinned.** `content` is a short snake_case identifier; structured details live in `meta`. Reserved identifiers enumerated.
- **Ordering rule explicit.** File position is authoritative; `ts` is displayed time. Ties break by file order.
- **Timezone simplified to UTC-everywhere.** No `OWNER_TZ` configuration. Local-time interpretation is a query-time concern.
- **`OWNER_ID` enforcement pinned to channel adapter.** Skills do not perform secondary checks. Reference runtime declared (Claude Code); Junie and OpenCode+oh-my-opencode supported; Cursor out of scope.
- **Conflict detection reframed** as agent judgment, not algorithm. Resolution protocol spelled out.
- **Manual redaction escape hatch** added explicitly. Append-only is a writer-side discipline, not an immutability guarantee.
- **Layer 1 reframed** as runtime-level access control (pre-tool hook), with explicit fallback to "convention" on hook-less runtimes.
- **Consolidation scheduling** pinned to system cron / systemd timer (no internal bot scheduler, no runtime-specific schedulers). `/consolidate` slash command optional.
- **Pending review UX** specified: `/review` slash command primary, threshold notification at ≥5 candidates, three actions (confirm / drop / edit), widget channel-specific.
- **`source:` time ranges** declared inclusive on both ends.
- **`snake_case` filenames mandatory** vault-wide (no kebab/snake choice).
- **`bot_stopped` best-effort** semantics documented with crash-detection pattern.

# log_event.py

Write-path hook. Appends one JSONL event per CC hook firing to the chat-memory vault.

## Invocation

Not run manually. Wired from `.claude/settings.json` as four hook commands, one per event:

```
python3 .../log_event.py --event {user|assistant|session-start|session-end}
```

Reads hook JSON from stdin. Writes to `$GINARR_VAULT_ROOT/logs/YYYY/MM/YYYY-MM-DD.jsonl` (UTC, sub-second precision). If `GINARR_VAULT_ROOT` is unset the script prints a message to stderr and exits 0 — the bot runs, but no events are captured.

## Event bodies

| `--event`       | Role         | Content source                                                   |
|-----------------|--------------|------------------------------------------------------------------|
| `user`          | `user`       | `hook_input.prompt`                                              |
| `assistant`     | `assistant`  | `hook_input.last_assistant_message` + walk-back (see below)      |
| `session-start` | `system`     | literal `bot_started`; `meta.session_id`                         |
| `session-end`   | `system`     | literal `bot_stopped`; `meta.session_id` (best-effort)           |

## Assistant extraction logic

At `Stop`-hook time the Claude Code transcript file may not yet contain the final assistant text block (Claude Code flushes lazily on text-only turns). The script combines two sources:

- `hook_input.last_assistant_message` — authoritative final text block.
- Walk-back of the session transcript — earlier text blocks that tool calls have already forced to flush.

`_is_real_user_prompt` is how walk-back decides where to stop: a `type:"user"` record counts as a real user prompt (boundary) only if its content contains a `text` block or is a bare string. `tool_result` records, which also carry `type:"user"`, are skipped.

Concatenation is `flushed + "\n\n" + final`, or just one of them if the other is empty. If `final` is already a suffix of `flushed`, only `flushed` is kept (dedup).

## Redaction

Every emitted event's `content` passes through `redactor.redact()` (Layer 2 + 3). Raw `hook_input` is never persisted.

## Error handling

Any internal exception is caught and emitted as a `system:hook_error` event with `meta.hook`, `meta.error`, `meta.traceback`. The script always exits 0 — the write-path must never block the runtime. If even the hook_error write fails, a single line is emitted to stderr.

## POSIX append

Events are written with `open(path, "ab")`. POSIX `O_APPEND` makes sub-4KB writes atomic, which matters once maintenance scripts (consolidation, archive) run alongside the live bot.

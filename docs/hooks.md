# Claude Code hooks

Wired in `.claude/settings.json`. Two script entry points:

- `log_event.py` — the write-path, one invocation per conversational-lifecycle event.
- `pre_tool_denylist.py` — Layer 1 access control on tool calls; see [scripts/pre_tool_denylist.md](scripts/pre_tool_denylist.md).

Both read hook JSON from stdin.

## Write-path wiring

| Hook event         | `--event`       | Writes                                                       |
|--------------------|-----------------|--------------------------------------------------------------|
| `UserPromptSubmit` | `user`          | `{role:"user", content:<prompt>}`                            |
| `Stop`             | `assistant`     | `{role:"assistant", content:<turn's text>}`                  |
| `SessionStart`     | `session-start` | `{role:"system", content:"bot_started"}` (`meta.session_id`) |
| `SessionEnd`       | `session-end`   | `{role:"system", content:"bot_stopped"}` (`meta.session_id`) |

All writes go to `$GINARR_VAULT_ROOT/logs/YYYY/MM/YYYY-MM-DD.jsonl` (UTC, sub-second precision). Content is passed through `redactor.py` before the event is serialized.

## Access-control wiring

| Hook event    | Script                     | Matcher                             | Effect                                                                 |
|---------------|----------------------------|-------------------------------------|------------------------------------------------------------------------|
| `PreToolUse`  | `pre_tool_denylist.py`     | `Read|Edit|Write|Bash|NotebookEdit` | Denies calls targeting SPEC denylist paths; returns a `[REDACTED: …]` stub. |

## Assistant text extraction

The `Stop` hook must recover the assistant text shown to the user this turn. Two sources are combined:

- **`hook_input.last_assistant_message`** — the final text block. Always authoritative when present.
- **Walk-back of the Claude Code transcript** — text blocks flushed earlier in the same turn (for example, an intro text before a tool call).

Why combined: on text-only turns, Claude Code does not flush the final text block to the session transcript file before firing `Stop`. Walk-back alone would miss it. On turns with tool calls, the tool call itself forces earlier text blocks to be flushed, so walk-back catches them while `last_assistant_message` holds only the final block. Concatenating both with `\n\n` recovers the full turn. If the final block is already a suffix of the walked-back text, the walked-back text is kept alone (dedup).

Walk-back stops at the most recent real user prompt. A `type:"user"` record counts as a real prompt only if its content contains a `text` block or is a bare string; `tool_result` records (which Claude Code also tags `type:"user"`) are skipped.

## Error handling

Any internal exception in `log_event.py` is caught; the script emits a `system:hook_error` event with `meta.hook`, `meta.error`, `meta.traceback`, and always exits 0. The write-path must never block the runtime.

`bot_stopped` is best-effort: written on graceful shutdown, cannot be written on SIGKILL or power loss. A `bot_started` without a preceding `bot_stopped` therefore signals a crash (SPEC.v3 §"`bot_stopped` is best-effort").

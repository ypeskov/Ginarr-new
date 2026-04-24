# log_event.py

Write-path hook. Appends one JSONL event per CC hook firing to the chat-memory vault.

## Invocation

Not run manually. Wired from `.claude/settings.json` as four hook commands, one per event:

```
python3 .../log_event.py --event {user|assistant|session-start|session-end}
```

Reads hook JSON from stdin. Writes to `$GINARR_VAULT_ROOT/logs/YYYY/MM/YYYY-MM-DD.jsonl` (UTC, sub-second precision). If `GINARR_VAULT_ROOT` is unset the script prints a message to stderr and exits 0 — the bot runs, but no events are captured.

A `--self-test` mode (no stdin, no env var required) runs the in-file test battery — channel-tag parsing, attachment copy, pass-through, unresolved markers.

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

## Attachments (user events)

Telegram delivers inbound messages wrapped in an XML tag in `hook_input.prompt`:

```
<channel source="telegram" chat_id="…" user="…" ts="…"
         image_path="/tmp/…" attachment_file_id="…" attachment_kind="voice" …>
inner text
</channel>
```

Before redaction, the user-event branch rewrites each tag to plain text plus SPEC `[image: …]` / `[file: …]` / `[audio: …]` markers.

| Source attribute                               | Handling                                                                                                              |
|------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| `image_path="<local>"`                         | File copied to `logs/YYYY/MM/attachments/YYYY-MM-DD_<sha8>.<ext>`; marker `[image: attachments/…]`. Missing/unreadable source is silently skipped. |
| `attachment_file_id="<id>" attachment_kind=…`  | File not yet materialised at hook time (agent downloads on demand). Marker `[audio: unresolved:<id>]` for `voice`/`audio`, `[file: unresolved:<id>]` otherwise. |
| Inner text                                     | Preserved as-is; markers appended after it separated by a single space. |
| No `<channel>` tag                             | Prompt passes through unchanged (terminal-originated prompts, non-Telegram channels). |

Names of copied files are content-addressed (`sha256[:8]` of the payload), so a repeated upload of the same image is deduped to one file on disk. SPEC §"Attachments" states paths are relative to `logs/YYYY/MM/`.

### Unresolved attachments

For non-image attachments the hook cannot fetch the file — that's the agent's job via `download_attachment`. The `unresolved:<file_id>` marker is a Ginarr extension beyond SPEC's strict `[kind: path]` format. A future phase may backfill the real path once the download completes.

## Redaction

Every emitted event's `content` passes through `redactor.redact(text, denylist)` (Layer 2 + 3). Raw `hook_input` is never persisted. Attachment markers are inserted **before** redaction so pattern-matching runs over the final text.

The Layer 3 `denylist` argument is loaded per-call by `_load_redact_list()` from `.claude/channels/.redact-list`. Missing or unreadable file → empty list (soft-fail; the write-path must never block). Values are appended by the [`/redact`](../skills/redact.md) slash command. On `SessionStart` the file is deleted after `bot_started` is written — Layer 3 is process-lifetime only, per SPEC.

## `/nolog` pause (Layer 4)

Before building the event, the script consults `.claude/channels/.nolog`. If the flag is present, `user` / `assistant` events are skipped. A sidecar `.claude/channels/.nolog.state` records the last observed pause state so the hook can emit `system:log_paused` once at the off→on transition and `system:log_resumed` once at on→off. See [`../skills/nolog.md`](../skills/nolog.md) for the full state table.

On `session-start`, `_reset_channels_on_start()` deletes the nolog flag, its sidecar, **and** the Layer 3 redact list — a crash cannot leave a stuck pause or stale owner-marked values across restarts. `session-start` / `session-end` themselves always pass through the pause check.

## Error handling

Any internal exception is caught and emitted as a `system:hook_error` event with `meta.hook`, `meta.error`, `meta.traceback`. The script always exits 0 — the write-path must never block the runtime. If even the hook_error write fails, a single line is emitted to stderr.

## POSIX append

Events are written with `open(path, "ab")`. POSIX `O_APPEND` makes sub-4KB writes atomic, which matters once maintenance scripts (consolidation, archive) run alongside the live bot.

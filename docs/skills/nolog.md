# `/nolog` — Layer 4 runtime pause

Slash command that pauses the Auto-Wiki write-path for a conversation window. Implements Layer 4 of SPEC.v3's secret-protection stack: when regex redaction can't help and you just need to keep something out of the log entirely.

## Source

- Command template: [`.claude/commands/nolog.md`](../../.claude/commands/nolog.md).
- Runtime wiring: flag-file check inside [`.claude/scripts/log_event.py`](../../.claude/scripts/log_event.py) (`_apply_nolog`, `_reset_nolog_on_start`).

## Usage

- `/nolog on` — pause. `log_event.py` will skip every subsequent `user` / `assistant` event until the flag is cleared.
- `/nolog off` — resume.
- `/nolog` (no argument) — report current state without changing it.

System events (`bot_started`, `bot_stopped`, `hook_error`, `log_paused`, `log_resumed`, etc.) are **always** written — they are structural markers, not conversational content.

## How the state machine works

Two files under `.claude/channels/`:

| File                    | Meaning                                        |
|-------------------------|------------------------------------------------|
| `.nolog`                | Pause flag. Present = paused.                  |
| `.nolog.state`          | Sidecar — the last pause state `log_event.py` observed. Used to detect transitions. |

On every `user` / `assistant` hook firing, `log_event.py` compares the two:

| Flag `.nolog` | Sidecar `.nolog.state` | Action                                                          |
|---------------|------------------------|-----------------------------------------------------------------|
| absent        | absent                 | Pass through. Write the event.                                  |
| **present**   | absent                 | **Transition off→on.** Emit `system:log_paused`, touch sidecar, **skip** this event. |
| present       | present                | Still paused. Skip without emitting.                            |
| absent        | **present**            | **Transition on→off.** Emit `system:log_resumed`, remove sidecar, **write** this event. |

`session-start` and `session-end` events always pass through — the sidecar logic doesn't touch them, and `bot_started` additionally clears both files so a crash can never leave a stuck pause across restarts.

## Caveats

- The flag is process-wide, file-based. Any agent with write access to `.claude/channels/` can set or clear it — that's fine for a single-owner bot.
- Per SPEC: "Content inside the window is not persisted." That includes the assistant's own confirmation to `/nolog on` — it lands after the transition boundary and gets skipped. The log will show the user's `/nolog on` prompt, then `log_paused`, then silence until the next `log_resumed`.
- `log_event.py` never fails if the channels dir doesn't exist — it's created lazily on the first `off→on` transition.

## Related

- [`redact`](redact.md) (planned) — Layer 3 counterpart: redact a specific value instead of pausing everything.
- [`log_event.py`](../scripts/log_event.md) — the write-path hook that enforces the pause.

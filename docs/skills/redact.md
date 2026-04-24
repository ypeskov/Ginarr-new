# `/redact` — Layer 3 owner-marked denylist

Slash command for marking a specific *value* as secret. All subsequent occurrences of that string in `user` / `assistant` log events are replaced with `[REDACTED:user-marked]`. Implements Layer 3 of SPEC.v3's secret-protection stack — the surgical counterpart to `/nolog`'s pause.

## Source

- Command template: [`.claude/commands/redact.md`](../../.claude/commands/redact.md).
- List file: `.claude/channels/.redact-list` (gitignored, one value per line).
- Redaction engine: [`redactor.py`](../scripts/redactor.md) — `redact(text, denylist)`.
- Runtime wiring: [`log_event.py`](../scripts/log_event.md) — `_load_redact_list()` and the `redact(...)` call in the user/assistant branches of `build_event`.

## Usage

- `/redact <value>` — append `<value>` to the denylist.
- `/redact` (no argument) — report the number of values currently on the list, without revealing them.

## When to use `/redact` vs `/nolog`

| Situation                                                         | Reach for       |
|-------------------------------------------------------------------|-----------------|
| One specific string must not appear in logs, rest is fine         | `/redact`       |
| The entire upcoming conversation is sensitive                     | `/nolog on`     |
| You want the pause marker visible in the log for the later reader | `/nolog on`/`off` |

## Lifecycle

Per SPEC: Layer 3 "resets on restart." `log_event.py._reset_channels_on_start()` deletes `.redact-list` right after writing `bot_started` on every `SessionStart` hook. A fresh process starts with an empty Layer 3 denylist.

If you need a durable denylist across restarts, that is out of scope for Layer 3 by design — the intended flow is to re-issue `/redact` for still-sensitive values as needed.

## One-time leak in the invocation itself

The string `/redact Galina` is itself a user prompt, and `UserPromptSubmit` fires **before** Claude reads the command template. That means `Galina` lands in the log once — in the `/redact Galina` prompt — *before* it's added to the denylist. Subsequent mentions get scrubbed.

Two mitigations exist:

1. The slash command is told not to echo the value back in its reply, so the assistant event does not re-leak it.
2. SPEC.v3 also permits an inline `<secret>value</secret>` tag syntax: any text wrapped in that tag would be scrubbed in-place before the write. That inline form is **not yet implemented** in `redactor.py` — it is tracked as a follow-up, not Phase 2.2 scope.

For genuinely critical values, combine `/nolog on` → share → `/redact value` → `/nolog off`. The pause window hides both the secret itself and the `/redact` that marks it.

## File format

One value per line, UTF-8, no escaping. Blank lines and whitespace-only lines are skipped by the loader. Values are matched with a plain `str.replace` — no regex, no case-folding. Case and whitespace inside the value matter.

## Caveats

- **No undo.** To remove a value from the list, edit `.claude/channels/.redact-list` by hand (or just restart the bot).
- **Matches are literal and substring-wide.** Adding `falcon` also redacts the middle of `falconry`. If that's a problem, add the surrounding context as part of the value.
- **Historical logs are not rewritten.** Only events written *after* the value enters the list are scrubbed. Rescanning past logs would create a false sense of safety — backups and sync copies would still hold the plaintext. Manual scrubbing of a past day's JSONL is the documented escape hatch.

# redactor.py

Layer 2 + Layer 3 secret scrubber for the chat-log write path.

## Layers implemented

- **Layer 2** — regex for known token formats: AWS access keys (`AKIA…`, `ASIA…`), GitHub tokens (`ghp_` / `gho_` / `ghs_`), OpenAI-style `sk-…`, Slack `xox[baprs]-…`, Stripe `sk_live_…`, DB connection strings (`postgres|mysql|redis|mongodb://user:pass@host`), PEM private-key blocks, and a generic `(api_key|token|secret|password)…` fallback.
- **Layer 3** — owner-marked denylist: values from `--denylist-file` are replaced with `[REDACTED:user-marked]`.

Matches are replaced with `[REDACTED:<category>]` rather than `***` — preserves debuggability about **what kind** of secret was scrubbed.

## Usage

```bash
# From stdin
cat some.txt | redactor.py

# From a file
redactor.py some.txt

# With a per-process owner denylist
redactor.py some.txt --denylist-file /tmp/denylist.txt

# Run the built-in test suite
redactor.py --self-test    # 16 cases, pass/fail summary to stderr
```

## Invocation inside the bot

Used as a library by `log_event.py` (`from redactor import redact`). Applied to every `user` and `assistant` event's content before the event is serialised. The Layer 3 denylist is read on each call from `.claude/channels/.redact-list` via `log_event._load_redact_list()` — values are appended there by the [`/redact`](../skills/redact.md) slash command and wiped by `_reset_channels_on_start()` on `SessionStart`.

## Contract

Stdlib only, no dependencies. Single file. Deterministic regex substitutions; no I/O beyond stdin/argv/stdout.

## Regex coverage notes

- The PEM pattern matches the full `-----BEGIN … PRIVATE KEY-----` to `-----END … PRIVATE KEY-----` envelope, not just the `-----BEGIN` opener.
- All three GitHub token prefixes (`ghp_`, `gho_`, `ghs_`) carry the same `{36}` suffix; the canonical implementation is one regex family, not three.

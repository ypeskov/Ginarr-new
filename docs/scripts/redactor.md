# redactor.py

Layer 2 + Layer 3 secret scrubber, per SPEC.v3 §"Secrets and PII".

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

## SPEC deviations

- SPEC.v3's PEM pattern stops at `-----END` (literal). Implementation extends it to the full `-----END … PRIVATE KEY-----` footer — treated as a SPEC typo.
- SPEC.v3 lists `ghp_[0-9a-zA-Z]{36}` plus bare `gho_` / `ghs_`. Implementation applies the same `{36}` suffix to all three variants.

Both are pending formalisation in SPEC v4.

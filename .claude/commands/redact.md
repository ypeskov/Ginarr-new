---
description: Mark a specific value as secret. All future occurrences in the chat log are replaced with [REDACTED:user-marked]. Layer 3 of Ginarr's secret-protection stack.
argument-hint: <value> | (empty to report list size)
allowed-tools: Read, Write, Bash(mkdir:*), Bash(wc:*), Bash(test:*), Bash(grep:*)
---

Append one owner-marked value to the Layer 3 denylist at `.claude/channels/.redact-list` (SPEC.v3 §"Layer 3").

Argument: `$ARGUMENTS`

Steps:

1. **Empty or whitespace-only argument** → report current state, do not modify anything:
   - Run `test -f .claude/channels/.redact-list && grep -cve '^[[:space:]]*$' .claude/channels/.redact-list || echo 0`.
   - Reply: `Layer 3 denylist: N values (use /redact <value> to add; cleared on bot restart).` Do **not** list the values — that would defeat the purpose.

2. **Argument contains a newline character** → refuse: reply `Redact values must be single-line. Use /redact multiple times for several values.` and stop.

3. **Otherwise** — add the value (do not echo it back in the response):
   - `mkdir -p .claude/channels` (idempotent).
   - If `.claude/channels/.redact-list` exists: Read it. Split into lines, strip trailing newlines. If the new value is already present (exact match), reply `Already in Layer 3 denylist — no change.` and stop.
   - Build the new file content: existing lines (if any) + the new value + trailing newline. Use the Write tool to write `.claude/channels/.redact-list`. Never pass the value through a shell command — Read/Write tools handle the string literally, bypassing shell-quoting hazards.
   - Reply: `Added to Layer 3 denylist. Future occurrences in user/assistant log writes will be replaced with [REDACTED:user-marked]. Cleared on bot restart.`

Do not reveal the value in any confirmation message. The operator already knows what they typed; echoing it back could leak into logs via the assistant event.

# pre_tool_denylist.py

Layer 1 of SPEC.v3 §"Secrets and PII" — a runtime-level access-control hook. Runs on every `PreToolUse` event and denies the tool call when it targets a path on the denylist. Denied secrets never enter the model context, so they cannot leak via a reply or thinking trace.

## Wiring

`.claude/settings.json`:

```json
"PreToolUse": [
  {"matcher": "Read|Edit|Write|Bash|NotebookEdit",
   "hooks": [{"type": "command", "command": "python3 /home/krokobot/Ginarr/.claude/scripts/pre_tool_denylist.py"}]}
]
```

The matcher scopes the hook to tools that can actually read or write file contents. Other tools (Glob, Grep, WebFetch, …) pass through without this hook.

## Denylist

From SPEC.v3 §"Secrets and PII":

- **Basename patterns:** `.env*`, `*.pem`, `*.key`, `id_rsa*`, `credentials*`.
- **Directory prefixes:** `~/.ssh/`, `~/.aws/`, `~/.config/gcloud/`.
- **Exact file:** `~/.kube/config`.

### `.env.example` exception

`.env.example` is an explicit allowlist override: committed template, no secrets, documented in [`configuration.md`](../configuration.md). All other `.env*` variants are denied.

## Behaviour by tool

| Tool                      | Field checked                              | Notes |
|---------------------------|--------------------------------------------|-------|
| `Read` / `Edit` / `Write` | `tool_input.file_path`                     | Path normalised: `~` expanded, relative paths resolved against `hook_input.cwd`. |
| `NotebookEdit`            | `tool_input.notebook_path` or `file_path`  | Same normalisation. |
| `Bash`                    | `tool_input.command`                       | Token regex scan. Any token that looks like a path (contains `/`, or starts with `~` / `.`) is checked via the same matcher. Pure regex — no shell parsing. Best-effort defense in depth; complex shell constructs like `$(…)` can still slip through. |

## Output

On match, stdout is a single JSON object; exit code stays 0:

```json
{"hookSpecificOutput": {
  "hookEventName": "PreToolUse",
  "permissionDecision": "deny",
  "permissionDecisionReason": "[REDACTED: path in denylist]"
}}
```

Claude Code surfaces `permissionDecisionReason` to the model as the denied result, so the model sees only the stub — never the file contents.

On no match (or any internal exception) the script produces no output and exits 0, letting the runtime continue. Failing closed would break the bot over parsing quirks; failing open is consistent with the hook's "defense in depth" role alongside Layer 2+ redaction.

## Self-test

```
python3 .claude/scripts/pre_tool_denylist.py --self-test
```

Covers 27 cases: basename globs, directory prefixes, the `.env.example` override, unknown tools (pass-through), Bash deny + allow, empty input.

## Degraded fallback

On a runtime without pre-tool interception (migration targets that lack `PreToolUse`), Layer 1 degrades to a convention: skill authors must avoid reading denylisted paths. Enforcement then falls back to Layers 2–4 only. See SPEC.v3 §"Layer 1 — path denylist".

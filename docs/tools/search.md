# search.py

Frontmatter-aware grep across the Ginarr vault. Use when the `recall` skill's scope (one session, one question) is too narrow — e.g. for ad-hoc auditing or feeding external tooling.

## Source

[`tools/search.py`](../../tools/search.py).

## Invocation

```
GINARR_VAULT_ROOT=… python3 tools/search.py <query> \
    [--scope wiki|logs|both] \
    [--since YYYY-MM-DD] \
    [--type user|feedback|project|reference|decision] \
    [--tag <tag>] \
    [--json]
```

Positional `<query>` is a case-insensitive substring (escaped before regex compile — no pattern surprises).

## Filters

| Flag | Applies to | Effect |
|---|---|---|
| `--scope` | both | `wiki` only, `logs` only, or `both` (default). |
| `--since` | logs | Drop log files whose date (from `YYYY-MM-DD.jsonl` filename) is before this date. Wiki scope unaffected — notes don't carry a stable date in the filename. |
| `--type` | wiki | Require frontmatter `type:` to match. |
| `--tag` | wiki | Require the named tag to be in the note's `tags:` list. |
| `--json` | both | Emit machine-readable JSON instead of human output. |

## Output shapes

### Human (default)

```
wiki (3 hits):
  wiki/entities/family/dog_rex.md:5: description: user's dog — a border collie, 4 years old

logs (2 hits):
  logs/2026/04/2026-04-23.jsonl 2026-04-23T14:32:01Z [user]: what was the …
```

### JSON (`--json`)

```json
{
  "wiki": [{"path": "wiki/entities/family/dog_rex.md", "line": 5, "text": "…"}],
  "logs":  [{"path": "logs/…", "ts": "2026-04-23T14:32:01Z", "role": "user", "content": "…"}]
}
```

The `--type` filter still works against frontmatter `type:` values (`user | feedback | project | reference | decision`) but the legacy directory layout it was designed to mirror no longer exists — see [archive.md](archive.md) §"--type" for the same caveat. After the 2026-04-26 entity-page migration, all live notes sit in `wiki/entities/` regardless of `type`.

Log `content` is truncated to 200 chars with `…` appended.

## Relation to `recall`

`recall` is the LLM-driven read path used inside a conversation. `search.py` is the scripted fallback — identical spirit, different audience: one answers a question in chat, the other dumps raw hits for pipelines or humans.

## Limitations

- Substring only — no regex, no fuzzy match.
- Notes: searches raw line text, including frontmatter lines, which is convenient for auditing (`--tag` matches by frontmatter list, not free-text).
- Logs: scans line-by-line JSON — malformed lines are silently skipped.
- No ranking; results are emitted in file/line order.

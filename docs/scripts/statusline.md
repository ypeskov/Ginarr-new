# statusline.sh / statusline.py

Renders the Claude Code status line for this project.

## Output

```
[Ginarr] · ctx:47k/1M (5%) · $0.12
```

- `[Ginarr]` — project label (cyan, bold).
- `ctx:USED/WINDOW (PERCENT)` — token usage vs context window (yellow).
- `$X.XX` — accumulated session cost, from Anthropic (green).

## Sources

All inputs come from the Claude Code `statusLine` JSON on stdin:

- `cost.total_cost_usd` → the dollar figure.
- `model.id` → context window (`1,000,000` when the id contains `[1m]`, else `200,000`).
- `transcript_path` → the script tails the session transcript, finds the most recent `message.usage`, and sums `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`.

## Why two files

`statusline.sh` is a thin `exec python3 "$(dirname …)/statusline.py"` wrapper. An earlier inline-heredoc approach made the heredoc itself become Python's stdin, shadowing the CC JSON; splitting the logic into its own `.py` keeps stdin clean.

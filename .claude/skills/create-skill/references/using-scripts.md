# Using Scripts in Skills

Source: https://agentskills.io/skill-creation/using-scripts

## One-off commands

When an existing package does what you need, reference it directly without a `scripts/` dir:

```bash
uvx ruff@0.8.0 check .          # Python (uv)
npx eslint@9 --fix .            # Node.js
bunx create-vite@6 my-app       # Bun
go run golang.org/x/tools/cmd/goimports@v0.28.0 .  # Go
```

Tips: pin versions, state prerequisites in SKILL.md, move complex commands into scripts.

## Referencing scripts from SKILL.md

Use relative paths from skill root:

```markdown
## Available scripts
- **`scripts/validate.sh`** — Validates configuration
- **`scripts/process.py`** — Processes input data

## Workflow
1. Run validation: `bash scripts/validate.sh "$INPUT_FILE"`
2. Process results: `python3 scripts/process.py --input results.json`
```

## Self-contained scripts

Bundle scripts with inline dependency declarations:

### Python (PEP 723 + uv)

```python
# /// script
# dependencies = ["beautifulsoup4"]
# ///

from bs4 import BeautifulSoup
# ... script code
```

Run: `uv run scripts/extract.py`

### Bun/Deno

Import with version pins directly. No package.json needed:

```typescript
import * as cheerio from "cheerio@1.0.0";
```

Run: `bun run scripts/extract.ts`

## Designing scripts for agentic use

### Hard requirements

- **No interactive prompts** — agents can't respond to TTY input. Accept all input via flags, env vars, or stdin.

### Best practices

- **`--help` output** — primary way agent learns the interface. Include description, flags, examples. Keep concise.

- **Helpful error messages** — say what went wrong, what was expected, what to try:
  ```
  Error: --format must be one of: json, csv, table.
         Received: "xml"
  ```

- **Structured output** — prefer JSON/CSV over free-form text. Send data to stdout, diagnostics to stderr.

- **Idempotency** — agents may retry. "Create if not exists" > "create and fail on duplicate."

- **Dry-run support** — `--dry-run` flag for destructive operations.

- **Meaningful exit codes** — distinct codes for different failure types.

- **Predictable output size** — default to summary/limit, support `--offset` for pagination. Large output gets truncated by agent harnesses (10-30K chars).

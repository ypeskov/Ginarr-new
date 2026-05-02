---
name: create-skill
description: >
  Create, scaffold, or refactor Agent Skills following the agentskills.io
  specification. Use when the user asks to create a new skill, convert existing
  code into a skill, fix a skill's structure, or improve a skill's description.
  Also use when someone says "make a skill for X" or "add a new slash command."
compatibility: Requires Claude Code with skills support
metadata:
  author: openclaw
  version: "1.1"
---

# /create-skill — Create a New Agent Skill

Scaffolds a new skill directory and SKILL.md following the [Agent Skills spec](https://agentskills.io/specification).

## Arguments

- First argument: skill name (lowercase, hyphens only, no consecutive hyphens)
- Remaining: short description of purpose

If no arguments, ask the user for name and purpose.

## Instructions

### 1. Validate the name

- 1–64 chars, only `a-z`, digits, hyphens
- No start/end with `-`, no `--`
- Must match the directory name

If invalid, suggest a corrected name.

### 2. Check for conflicts

Check `.claude/skills/<name>/`. If exists, ask: overwrite or rename?

### 3. Create directory

```
.claude/skills/<name>/
├── SKILL.md
├── scripts/       # only if needed
├── references/    # only if needed
└── assets/        # only if needed
```

Only create optional dirs if the skill requires them.

### 4. Write SKILL.md

Follow the spec strictly. Refer to [references/specification.md](references/specification.md) for full field rules.

Key principles:
- **Frontmatter**: `name` (required), `description` (required, max 1024 chars), optional `compatibility`, `metadata`, `allowed-tools`
- **Description**: use imperative phrasing ("Use when..."), include trigger keywords, describe what it does AND when to use it. See [references/optimizing-descriptions.md](references/optimizing-descriptions.md)
- **Body**: step-by-step instructions, under 500 lines. See [references/best-practices.md](references/best-practices.md)
- **Scripts**: if needed, bundle in `scripts/` with `--help`, structured output, no interactive prompts. See [references/using-scripts.md](references/using-scripts.md)
- **Progressive disclosure**: keep SKILL.md lean, move details to `references/`

### 5. If the skill needs a cron schedule

Create a launcher at `.claude/scripts/<name>.sh` that calls the skill via `claude -p "/<name>"`:

```bash
#!/bin/bash
export HOME=/home/krokobot
export PATH="$HOME/.bun/bin:$HOME/.local/bin:/home/linuxbrew/.linuxbrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

LOG="$HOME/Ginarr/.claude/scripts/logs/<name>.log"
mkdir -p "$(dirname "$LOG")"

echo "=== $(date -u) ===" >> "$LOG"
cd "$HOME/Ginarr"
claude -p "/<name>" \
  --allowedTools '<required tools>' \
  --permission-mode acceptEdits \
  >> "$LOG" 2>&1
echo "exit: $?" >> "$LOG"
```

Make executable, add to crontab.

### 6. Confirm to user

Report: created files, how to invoke (`/<name> [args]`), cron schedule if any.

## References

- [Specification](references/specification.md) — full format rules for SKILL.md
- [Quickstart](references/quickstart.md) — tutorial walkthrough of creating a skill
- [Best practices](references/best-practices.md) — scoping, context budget, calibrating control
- [Optimizing descriptions](references/optimizing-descriptions.md) — trigger accuracy, eval queries
- [Evaluating skills](references/evaluating-skills.md) — test cases, assertions, grading loop
- [Using scripts](references/using-scripts.md) — one-off commands, self-contained scripts, agentic design

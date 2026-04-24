# Quickstart — Create Your First Agent Skill

Source: https://agentskills.io/skill-creation/quickstart

## Minimal skill

A skill is a folder containing a `SKILL.md` file. Create `.claude/skills/<name>/SKILL.md`:

```markdown
---
name: roll-dice
description: Roll dice using a random number generator. Use when asked to roll a die (d6, d20, etc.), roll dice, or generate a random dice roll.
---

To roll a die, use the following command:

```bash
echo $((RANDOM % <sides> + 1))
```

Replace `<sides>` with the number of sides on the die.
```

That's it — one file, under 20 lines.

## Parts of a skill

- **`name`** — Short identifier. Must match folder name.
- **`description`** — Tells the agent when to use this skill. This is how the agent decides whether to activate it.
- **The body** — Instructions the agent follows when activated.

## How it works

1. **Discovery** — Agent scans skill directories, reads only `name` and `description`.
2. **Activation** — User's task matches description → agent loads full SKILL.md.
3. **Execution** — Agent follows instructions, adapting to the specific request.

This is **progressive disclosure** — many skills available without loading all instructions upfront.

## Next steps

- [Best practices](best-practices.md) — scoping and effective instructions
- [Optimizing descriptions](optimizing-descriptions.md) — trigger accuracy
- [Specification](specification.md) — full format reference

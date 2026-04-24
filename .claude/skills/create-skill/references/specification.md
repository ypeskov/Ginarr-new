# Agent Skills Specification

Source: https://agentskills.io/specification

## Directory structure

```
skill-name/
├── SKILL.md          # Required: metadata + instructions
├── scripts/          # Optional: executable code
├── references/       # Optional: documentation
├── assets/           # Optional: templates, resources
```

## SKILL.md format

YAML frontmatter followed by Markdown content.

### Frontmatter fields

| Field           | Required | Constraints                                                                     |
| --------------- | -------- | ------------------------------------------------------------------------------- |
| `name`          | Yes      | Max 64 chars. Lowercase letters, numbers, hyphens. No start/end/consecutive `-` |
| `description`   | Yes      | Max 1024 chars. What it does and when to use it.                                |
| `license`       | No       | License name or reference to bundled file.                                      |
| `compatibility` | No       | Max 500 chars. Environment requirements.                                        |
| `metadata`      | No       | Arbitrary string key-value pairs.                                               |
| `allowed-tools` | No       | Space-delimited list of pre-approved tools. (Experimental)                      |

### Name rules

- 1–64 characters
- Only lowercase `a-z`, digits, hyphens
- No start/end with `-`
- No consecutive `--`
- Must match parent directory name

### Description guidelines

- 1–1024 characters
- Describe both what it does AND when to use it
- Use imperative phrasing: "Use when..."
- Include keywords that help agents match tasks
- Err on the side of being specific about scope

### Body content

No format restrictions. Recommended sections:
- Step-by-step instructions
- Examples of inputs and outputs
- Common edge cases

## Progressive disclosure

1. **Metadata** (~100 tokens): name + description loaded at startup for all skills
2. **Instructions** (< 5000 tokens recommended): full SKILL.md body loaded on activation
3. **Resources** (as needed): files in scripts/, references/, assets/ loaded only when required

Keep SKILL.md under 500 lines. Move details to separate files.

## File references

Use relative paths from skill root:
```markdown
See [the reference guide](references/REFERENCE.md) for details.
Run the script: scripts/extract.py
```

Keep references one level deep. Avoid deeply nested chains.

# Optimizing Skill Descriptions

Source: https://agentskills.io/skill-creation/optimizing-descriptions

The `description` field carries the entire burden of triggering. If it doesn't convey when the skill is useful, the agent won't activate it.

## How triggering works

At startup, agents load only `name` and `description` of each skill. When a user's task matches, the full SKILL.md loads into context. Agents typically only consult skills for tasks requiring knowledge beyond what they handle alone.

## Writing effective descriptions

- **Use imperative phrasing**: "Use this skill when..." not "This skill does..."
- **Focus on user intent**: describe what the user is trying to achieve, not internal mechanics
- **Be pushy**: explicitly list contexts where skill applies, including indirect mentions
- **Keep it concise**: few sentences to a short paragraph, max 1024 chars

### Before/after example

```yaml
# Before
description: Process CSV files.

# After
description: >
  Analyze CSV and tabular data files — compute summary statistics,
  add derived columns, generate charts, and clean messy data. Use when
  the user has a CSV, TSV, or Excel file and wants to explore, transform,
  or visualize the data, even if they don't mention "CSV" or "analysis."
```

## Testing trigger accuracy

Design eval queries — realistic prompts labeled with should/shouldn't trigger:

### Should-trigger queries (8-10)
Vary along: phrasing (formal/casual/typos), explicitness (direct vs indirect), detail level, complexity. Most valuable: queries where skill helps but connection isn't obvious.

### Should-not-trigger queries (8-10)
Use **near-misses** — queries sharing keywords but needing something different. Not "write fibonacci" (too easy), but "write a python script that reads a CSV and uploads to postgres" (involves CSV but task is ETL, not analysis).

## The optimization loop

1. **Evaluate** current description on train + validation sets
2. **Identify failures** in train set only
3. **Revise** — generalize, don't add specific keywords from failed queries
4. **Repeat** until train set passes or improvement plateaus
5. **Select** best iteration by validation pass rate

Five iterations is usually enough. Use train/validation split (~60/40) to avoid overfitting.

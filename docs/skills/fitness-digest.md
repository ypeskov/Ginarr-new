# `/fitness-digest` — analyze weight + calorie data

Reads cached JSON in `wiki/entities/fitness/_data/`, computes weight trend and calorie averages, and produces a short Russian summary plus light, evidence-based recommendations.

## Source

- Skill: [`.claude/skills/fitness-digest/SKILL.md`](../../.claude/skills/fitness-digest/SKILL.md) — authoritative behaviour.
- Analyzer: `.claude/skills/fitness-digest/scripts/analyze.py` — pure stdlib. Picks the newest `*_both.json` from `_data/` (or takes an explicit path), computes weight deltas / min-max / recent rate and per-window calorie + protein + fat means, prints one JSON object on stdout. Single source of truth for the numbers; the skill only formats and adds recommendations.

## Dependencies

- `python3` (stdlib only).
- `pass` entry at `kcal/api-key` (only if the optional refresh runs).
- A populated `wiki/entities/fitness/_data/` directory. If empty, the skill triggers `/fitness-fetch` first; if that also fails, it asks the owner to provision the API key.

## Usage

- `/fitness-digest` — auto-refresh (last 30 days) and analyze.
- `/fitness-digest week` — last 7 days.
- `/fitness-digest month` — last 30 days.
- `/fitness-digest 90d` — last 90 days.
- `--no-refresh` — skip the fetch step and analyze only what's cached.

## Output

Telegram-style block with three sections (any of which may be omitted if the data does not support it):

- weight trend + delta vs week / vs month
- calorie average + best/worst day + macros if present
- two or three short recommendations grounded in the numbers

## Integration notes

- Owner-context (recovery trajectory, bad knee, glycemic-load focus) is baked into the recommendation rules in the SKILL.md and is meant to keep advice from defaulting to generic "eat less, move more" content.
- This skill never writes to entity pages. If a finding is worth persisting, the owner runs `capture` separately.

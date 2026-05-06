# `/fitness-digest` — analyze weight + calorie data

Reads cached JSON in `wiki/entities/fitness/_data/`, computes weight trend and calorie averages, and produces a short Russian summary plus light, evidence-based recommendations.

## Source

- Skill: [`.claude/skills/fitness-digest/SKILL.md`](../../.claude/skills/fitness-digest/SKILL.md) — authoritative behaviour.
- Analyzer: `.claude/skills/fitness-digest/scripts/analyze.py` — pure stdlib. Picks the newest `*_both.json` from `_data/` (or takes an explicit path), computes weight deltas / min-max / recent rate, an `lbm` block (LBM range under 30/35/40% body-fat assumptions), and per-window calorie / protein / fat means. Protein and fat are reported twice per window: `mean_protein_g` (averaged over `macro_days` only — use this) and `mean_protein_g_all_days` (legacy denominator including pre-2025-09-08 days with no macro fields, for sanity checking). Single source of truth for the numbers; the skill only formats and adds recommendations.
- Persistence: every run writes the formatted digest to `wiki/entities/fitness/digests/<latest_date>_<window>.md`. Re-running the same window on the same day overwrites; different windows or different days create new files. Use the directory to compare across periods without re-running the analyzer for old data.

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

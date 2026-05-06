# `/fitness-fetch` — pull weight + food history from kcal.peskov.info

Reads the X-API-Key from `pass`, calls the owner's self-hosted tracker, and dumps the raw JSON into the Auto-Wiki vault for later analysis by `/fitness-digest`.

## Source

- Skill: [`.claude/skills/fitness-fetch/SKILL.md`](../../.claude/skills/fitness-fetch/SKILL.md) — authoritative behaviour.
- Fetcher: `.claude/skills/fitness-fetch/scripts/fetch.py` — pure `urllib`, stdlib only.

## Dependencies

- `python3` (stdlib `urllib` is enough).
- `pass` entry at `kcal/api-key`. Provision once with:
  ```
  pass insert kcal/api-key
  ```
- `GINARR_VAULT_ROOT` env var pointing at the Auto-Wiki vault (already set by Ginarr's normal environment).

## API

- Endpoint: `GET https://kcal.peskov.info/api/v1/data`
- Header: `X-API-Key: <value from pass>`
- Query: `type=weight|food|both`, `from=YYYY-MM-DD`, `to=YYYY-MM-DD`

## Usage

- `/fitness-fetch` — last 30 days, `type=both`.
- `/fitness-fetch 7` — last 7 days, `type=both`.
- `/fitness-fetch 2026-04-01 2026-05-06` — explicit range.
- Pass `--type weight` or `--type food` to narrow.

## Output

Raw JSON written to:

```
$GINARR_VAULT_ROOT/wiki/entities/fitness/_data/<from>_to_<to>_<type>.json
```

Same range + type → file overwrites. The script writes the raw response verbatim. Verified schema (2026-05-06) is documented at the bottom of [`SKILL.md`](../../.claude/skills/fitness-fetch/SKILL.md) — top-level `{"weight": [...], "food": [...]}`, weight entries `{weight, recorded_at}`, food entries `{food, calories, weight, kcal_per_100g, fats?, proteins?, meal_datetime}`. `carbs` is not exposed by the API.

## Integration notes

- The `_data/` folder lives under the `fitness` topic but is excluded from entity-page processing by virtue of its leading underscore — `lint-wiki` and `ingest-and-weave` skip it.
- No cron is wired. The owner runs it ad-hoc, or `/fitness-digest` calls it as a precursor.

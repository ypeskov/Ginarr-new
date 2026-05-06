---
name: fitness-fetch
description: >
  Fetch weight and food history from the owner's self-hosted kcal tracker
  (https://kcal.peskov.info/) into the Auto-Wiki vault under
  `wiki/entities/fitness/_data/`. Use when the user asks to refresh fitness
  data, pull weight/calorie history, or as a precursor to `/fitness-digest`.
compatibility: Requires python3 (urllib stdlib only) and pass (kcal/api-key)
allowed-tools: Bash(python3 *) Bash(pass show *)
metadata:
  author: ginarr
  version: "1.0"
---

# /fitness-fetch — Fitness Data Fetcher

Pulls weight and food entries from `https://kcal.peskov.info/api/v1/data` and writes raw JSON into `$GINARR_VAULT_ROOT/wiki/entities/fitness/_data/`.

## Arguments

- No arguments: last 30 days, `type=both`.
- `<N>`: last N days, `type=both`.
- `<from> <to>`: explicit date range (`YYYY-MM-DD`), `type=both`.
- `--type weight|food|both` may be passed at any position.

## Instructions

### 1. Read the API key from pass

```bash
pass show kcal/api-key
```

Capture the output as `API_KEY`. If pass fails, tell the user the key is missing and stop. The recovery hint is: `pass insert kcal/api-key`.

### 2. Run the fetch script

```bash
python3 scripts/fetch.py --api-key "$API_KEY" --days 30
```

Other forms:

```bash
python3 scripts/fetch.py --api-key "$API_KEY" --from 2026-04-01 --to 2026-05-06
python3 scripts/fetch.py --api-key "$API_KEY" --days 7 --type weight
```

The script:

- calls `GET https://kcal.peskov.info/api/v1/data?type=...&from=...&to=...` with `X-API-Key` header,
- saves the raw JSON response to `$GINARR_VAULT_ROOT/wiki/entities/fitness/_data/<from>_to_<to>_<type>.json` (overwriting if same range+type),
- prints a one-line summary to stdout: file path, byte size, top-level keys.

Exit codes: 0 success, 1 HTTP/network error, 2 invalid arguments.

### 3. Report

Tell the user the file path and the keys observed in the response. Do not paste the file contents — they may be large.

### 4. Error handling

- 401/403 → key probably wrong; tell the user to refresh `pass insert kcal/api-key`.
- Other HTTP errors → report status code and body excerpt.
- DNS/connection errors → report as-is, suggest retry.

## Response schema (verified 2026-05-06)

Top-level: `{"weight": [...], "food": [...]}`.

**weight[]** entries (sorted ascending by date):

```json
{"weight": 146.15, "recorded_at": "2026-05-06T00:00:00Z"}
```

- `weight`: float, kilograms.
- `recorded_at`: ISO 8601 UTC, day-resolution in practice (always `T00:00:00Z`).

**food[]** entries (sorted descending by datetime — newest first):

```json
{
  "food": "Прошуто",
  "calories": 168,
  "weight": 80,
  "kcal_per_100g": 210,
  "fats": 10,
  "proteins": 30,
  "meal_datetime": "2026-05-06T06:05:08.727Z"
}
```

- `food`: string, free-form name (Russian / English mix).
- `calories`: int, total kcal for this serving.
- `weight`: int, grams in the serving (NOT body weight — naming collision with the top-level `weight` key).
- `kcal_per_100g`: int, density.
- `fats`, `proteins`: float (grams). **Optional** — not present on every entry.
- `carbs`: not observed in the API output as of 2026-05-06.
- `meal_datetime`: ISO 8601, may include milliseconds.

When computing daily totals, treat missing macro fields as 0 contribution but flag the per-day macros as a lower bound, since some entries omit them.

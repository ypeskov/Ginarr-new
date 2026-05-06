---
name: fitness-digest
description: >
  Read fitness data cached under `wiki/entities/fitness/_data/`, produce a
  Russian summary of weight trend and calorie balance with light, evidence-
  based recommendations. Use when the user asks for fitness analysis, weight
  trend, calorie review, or "посмотри что там с весом / калориями".
compatibility: Requires python3 and a populated `_data/` (run /fitness-fetch first if empty)
allowed-tools: Bash(python3 *) Bash(pass show *) Bash(ls *) mcp__plugin_telegram_telegram__reply
metadata:
  author: ginarr
  version: "1.1"
---

# /fitness-digest — Fitness Analysis & Recommendations

Reads cached API responses from `$GINARR_VAULT_ROOT/wiki/entities/fitness/_data/` and produces a concise Russian summary plus light recommendations. Numbers come from `scripts/analyze.py` — do **not** compute them inline; the script is the source of truth.

## Arguments

- No arguments: refresh last 30 days, then analyze.
- `week`: refresh last 7 days.
- `month`: refresh last 30 days.
- `90d`: refresh last 90 days.
- `year`: refresh last 365 days.
- `--no-refresh`: skip the fetch step and analyze whatever is cached.

## Instructions

### 1. Refresh data (default)

Unless `--no-refresh` was passed, call the fetch skill first. Pick the range from the argument:

- no argument or `month` → 30 days
- `week` → 7 days
- `90d` → 90 days
- `year` → 365 days

```bash
API_KEY="$(pass show kcal/api-key)"
python3 ../fitness-fetch/scripts/fetch.py --api-key "$API_KEY" --days <N>
```

If pass fails or fetch returns non-zero, fall back to whatever is cached and tell the user the data may be stale.

### 2. Compute statistics

```bash
python3 scripts/analyze.py --auto --days <N>
```

The script picks the newest `*_both.json` from the data dir, computes everything, and prints a JSON object on stdout. Schema:

```json
{
  "source_file": "...",
  "weight_available": true,
  "food_available": true,
  "weight": {
    "latest_kg": 146.15,
    "latest_date": "2026-05-06",
    "entries": 253,
    "vs_7d":   {"ref_date": "...", "ref_kg": 145.6,  "delta_kg":  0.55},
    "vs_30d":  {"ref_date": "...", "ref_kg": 145.15, "delta_kg":  1.0},
    "vs_90d":  {"ref_date": "...", "ref_kg": 151.05, "delta_kg": -4.9},
    "vs_180d": {"...": "..."},
    "vs_365d": {"...": "..."},
    "min": {"date": "2026-04-09", "kg": 144.15},
    "max": {"date": "2025-06-23", "kg": 169.0},
    "recent_kg_per_week": 0.23
  },
  "food": {
    "total_entries": 2637,
    "days_logged_total": 239,
    "earliest_log": "2025-06-22",
    "latest_log": "2026-05-06",
    "windows": {
      "7d":   {"days_logged": ..., "days_in_window": 7,   "mean_kcal": ..., "mean_protein_g": ..., "mean_fat_g": ..., "max_day": {...}, "min_day": {...}},
      "30d":  {"...": "..."},
      "90d":  {"...": "..."},
      "365d": {"...": "..."}
    }
  }
}
```

Some `vs_Nd` keys may be absent if the cached data does not span that far back. `food.windows[Nd]` is absent if no log entries fall in that window. Treat absence as missing data, not as zero.

### 3. Format the digest

Use the script's numbers verbatim — do not recompute, round only for display. Pick the window matching the user's request:

```
🏋️ Fitness — <range label>

⚖️ Вес
• Сейчас: <latest_kg> кг (<latest_date>)
• <vs_Nd.delta_kg with sign> кг за <N>д
• Минимум за период: <min.kg> кг (<min.date>)
• Темп последнего месяца: <recent_kg_per_week with sign> кг/нед

🍽️ Калории — <window label>, лог в <days_logged>/<days_in_window> дней
• Среднее: <mean_kcal> ккал/день
• Белок: ~<mean_protein_g> г/день (нижняя граница, не во всех записях есть макро)
• Макс: <max_day.kcal> (<max_day.date>), мин: <min_day.kcal> (<min_day.date>)

💡 Что вижу
• ...
• ...
```

Omit any line where the underlying field is missing. Do not invent numbers.

### 4. Recommendations

Two or three short bullets, grounded in what the script reported. Useful patterns:

- **Plateau or recent uptick** (e.g. `vs_30d.delta_kg >= 0` while earlier windows are negative) → суggest a small deficit (~300 kcal/day cut), not "eat less". Frame as "current intake looks like maintenance for current mass".
- **Many unlogged days** in the window (`days_logged < days_in_window * 0.8`) → flag the gap; recommendations are guesses without a clean log.
- **Low protein** (`mean_protein_g / latest_kg < 1.0`) → recommend bumping to ~1.2–1.5 g/kg; on a year-long deficit muscle preservation matters.
- **Single big-spike day** in `max_day` → call it out as data, not a moral failing.

Owner context to keep in mind (do not repeat verbatim every time):

- 2023→2026 recovery, current mass ~145 kg, target trajectory is **down but sustainable**.
- Bad knee + polyneuropathy → no high-impact activity recommendations.
- HbA1c history → glycemic load matters, not just total kcal.

If the data does not support a useful recommendation, say so plainly. Don't pad.

### 5. Deliver

- If triggered from Telegram (`<channel source="plugin:telegram:telegram"`), send via `mcp__plugin_telegram_telegram__reply` to the appropriate `chat_id`.
- If running in terminal, print the result.

### 6. Error handling

- `analyze.py` exits non-zero with no `_both.json` in `_data/` → tell the user to run `/fitness-fetch` first and check the API key.
- `pass show kcal/api-key` fails → tell the user to provision: `pass insert kcal/api-key`.

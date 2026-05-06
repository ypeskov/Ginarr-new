---
name: fitness-digest
description: >
  Read fitness data cached under `wiki/entities/fitness/_data/`, produce a
  Russian summary of weight trend and calorie balance with light, evidence-
  based recommendations. Use when the user asks for fitness analysis, weight
  trend, calorie review, or "посмотри что там с весом / калориями".
compatibility: Requires python3 and a populated `_data/` (run /fitness-fetch first if empty)
allowed-tools: Bash(python3 *) Bash(pass show *) Bash(ls *) Write mcp__plugin_telegram_telegram__reply
metadata:
  author: ginarr
  version: "1.2"
---

# /fitness-digest — Fitness Analysis & Recommendations

Reads cached API responses from `$GINARR_VAULT_ROOT/wiki/entities/fitness/_data/`, produces a concise Russian summary plus light recommendations, and persists the result under `wiki/entities/fitness/digests/` for cross-period comparison. Numbers come from `scripts/analyze.py` — do **not** compute them inline; the script is the source of truth.

Before composing the digest, also read `wiki/topics/fitness.md` for the topic-level conventions (binge interpretation, macro-tracking start date, LBM-based protein math). Those rules are normative.

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
    "latest_kg": 146.15, "latest_date": "2026-05-06", "entries": 253,
    "vs_7d":   {"ref_date": "...", "ref_kg": 145.6,  "delta_kg":  0.55},
    "vs_30d":  {"ref_date": "...", "ref_kg": 145.15, "delta_kg":  1.0},
    "vs_90d":  {"ref_date": "...", "ref_kg": 151.05, "delta_kg": -4.9},
    "vs_180d": {"...": "..."},
    "vs_365d": {"...": "..."},
    "min": {"date": "2026-04-09", "kg": 144.15},
    "max": {"date": "2025-06-23", "kg": 169.0},
    "recent_kg_per_week": 0.23
  },
  "lbm": {
    "weight_kg": 146.15,
    "assumed_body_fat_pct": {"low": 30, "mid": 35, "high": 40},
    "lbm_kg": {"at_30pct": 102.3, "at_35pct": 95.0, "at_40pct": 87.7},
    "note": "Use LBM (or target weight at BMI 25) ..."
  },
  "food": {
    "total_entries": 2637,
    "days_logged_total": 239,
    "earliest_log": "2025-06-22",
    "latest_log": "2026-05-06",
    "macro_tracking_started": "2025-09-08",
    "windows": {
      "7d": {
        "days_logged": 8, "days_in_window": 7, "macro_days": 8,
        "mean_kcal": 2392,
        "mean_protein_g": 114.3,           // averaged over macro_days only
        "mean_fat_g": 224.2,               // averaged over macro_days only
        "mean_protein_g_all_days": 114.3,  // averaged over days_logged (legacy / sanity)
        "mean_fat_g_all_days": 224.2,
        "max_day": {...}, "min_day": {...}
      },
      "30d": {"...": "..."},
      "90d": {"...": "..."},
      "365d": {"...": "..."}
    }
  }
}
```

Some `vs_Nd` keys may be absent if cached data does not span that far back. `food.windows[Nd]` is absent if no log entries fall in that window. Treat absence as missing data, not as zero.

**Use `mean_protein_g` (macro-only), not `mean_protein_g_all_days`.** The latter divides by every logged day including pre-2025-09-08 days that have no macro fields, which biases yearly numbers low. The script exposes both for transparency; the digest reports the macro-only one.

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
• Белок: ~<mean_protein_g> г/день (на <macro_days> дней с макро)
• Макс: <max_day.kcal> (<max_day.date>), мин: <min_day.kcal> (<min_day.date>)

💡 Что вижу
• ...
• ...
```

Omit any line where the underlying field is missing. Do not invent numbers.

### 4. Recommendations

Two or three short bullets, grounded in what the script reported and the topic notes in `wiki/topics/fitness.md`. Apply these rules:

- **Recent uptick after a logging gap = a bender, not a plateau.** If `vs_30d.delta_kg >= 0` and `days_logged < days_in_window * 0.85`, look for a multi-day gap in the cached data. Frame the recovery, not a "diet failure" — these unwind in 1-2 weeks.
- **Genuine plateau** (no gap, kcal at maintenance, weight flat ≥ 14d) → suggest a small deficit (~300 kcal/day cut), not "eat less".
- **Protein evaluation uses LBM, never total body weight.** From `lbm.lbm_kg`, pick the mid (35%) bracket as the default and quote the range. Targets: 1.2 g/kg LBM = floor for cutting, 1.6 g/kg LBM = aggressive ceiling. Alternative anchor: target weight at BMI 25 (state assumed height inline). If `mean_protein_g` falls inside the 1.2-1.6 range against LBM, call it adequate, not "low". Below 1.2 g/kg LBM → recommend bumping; above 1.6 g/kg LBM → no need to push higher.
- **Single big-spike day** in `max_day` → call it out as data, not a moral failing.
- **Unlogged days are unlogged days, not zero days.** Don't imply the owner fasted; flag the data gap.

Owner context to keep in mind (do not repeat verbatim every time):

- 2023→2026 recovery, current mass ~145 kg, target trajectory is **down but sustainable**.
- Bad knee + polyneuropathy → no high-impact activity recommendations.
- HbA1c history → glycemic load matters, not just total kcal.

If the data does not support a useful recommendation, say so plainly. Don't pad.

### 5. Persist the digest

After composing the reply text, write it (plus the structured numbers) to:

```
$GINARR_VAULT_ROOT/wiki/entities/fitness/digests/<latest_date>_<window>.md
```

Where `<window>` is one of `week`, `month`, `90d`, `year` — matching the argument used. Overwrite if the same file already exists (re-running the same window on the same day is an update, not a new record).

File format:

```markdown
---
date: <latest_date>
window: <window label, e.g. "year (365 days)">
source: wiki/entities/fitness/_data/<filename>.json
generated_by: fitness-digest
---

# Fitness digest — <latest_date>, окно <window>

## Источник
<one line: the source file path and a quick volume hint>

## Вес
<bulleted weight stats: current, deltas for all available windows, min/max>

## Калории
<table or bullets across the available food windows: kcal mean, macro-only protein/fat, log coverage>

## Что сказал ассистент
<the same bullets that went into the user-facing reply>

## Caveats
<known data quirks or open follow-ups, if any>
```

Use the existing `2026-05-06_year.md` as the reference shape — keep the section order stable so future digests are diff-friendly.

Do **not** persist the digest if `analyze.py` failed; in that case there's nothing trustworthy to record.

### 6. Deliver

- If triggered from Telegram (`<channel source="plugin:telegram:telegram"`), send via `mcp__plugin_telegram_telegram__reply` to the appropriate `chat_id`. Include the saved digest path at the bottom of the message so the owner knows where to find the long form.
- If running in terminal, print the result and the saved file path.

### 7. Error handling

- `analyze.py` exits non-zero with no `_both.json` in `_data/` → tell the user to run `/fitness-fetch` first and check the API key.
- `pass show kcal/api-key` fails → tell the user to provision: `pass insert kcal/api-key`.
- If `GINARR_VAULT_ROOT` is unset, skip the persist step and warn the user — don't silently drop the record.

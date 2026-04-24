---
name: weather
description: >
  Fetch weather forecast for any city and send it to Telegram or display
  in terminal. Uses Open-Meteo API (free, no key). Use when the user asks
  about weather, forecast, temperature, or "what's the weather like."
  Default city is Sofia, default 7 days.
compatibility: Requires python3 with urllib (standard library)
allowed-tools: Bash(python3 *) mcp__plugin_telegram_telegram__reply
metadata:
  author: openclaw
  version: "2.0"
---

# /weather — Weather Forecast

Fetches weather from Open-Meteo API and formats it for Telegram or terminal.

## Arguments

- No arguments: Sofia, 7 days
- One argument: city name, 3 days
- Two arguments: city name, number of days (max 7)

## Instructions

### 1. Run the forecast script

**IMPORTANT: You MUST use the bundled script. Do NOT generate the forecast yourself or call the API directly.**

```bash
python3 scripts/forecast.py --city "CITY" --days N
```

For Sofia (default): `python3 scripts/forecast.py`

The script handles geocoding, API calls, and formatting. It prints the formatted forecast to stdout. On error it prints to stderr and exits non-zero. Send the script's stdout output as-is — do not reformat, summarize, or shorten it.

### 2. Deliver the result

- If triggered from Telegram (`<channel source="plugin:telegram:telegram"`), send via `mcp__plugin_telegram_telegram__reply` to the appropriate `chat_id`.
- If running in terminal, print the result directly.

### 3. Error handling

If the script fails, send: "Не удалось получить прогноз для {city}. Попробуй позже."

---
name: calendar-digest
description: >
  Fetch today's events from all accessible Google Calendars and send a formatted
  summary to Telegram or display in terminal. Use when the user asks about
  today's schedule, calendar, agenda, meetings, or "what's on my calendar."
compatibility: Requires MCP Google Calendar integration
allowed-tools: mcp__claude_ai_Google_Calendar__gcal_list_calendars mcp__claude_ai_Google_Calendar__gcal_list_events mcp__plugin_telegram_telegram__reply
metadata:
  author: openclaw
  version: "1.0"
---

# /calendar-digest — Calendar Digest

Fetches today's events from all Google Calendars and delivers a formatted summary.

## Arguments

- No arguments: today's events
- `tomorrow`: tomorrow's events
- Date in format `YYYY-MM-DD`: events for that specific day

## Instructions

### 1. Determine the target date

- No arguments → today
- `tomorrow` → tomorrow
- Otherwise parse the provided date

All times use **Europe/Sofia** timezone.

### 2. List all calendars

Call `gcal_list_calendars` to get all accessible calendars. Filter to calendars where `accessRole` is `owner`, `writer`, or `reader` (skip `freeBusyReader`).

Split calendars into two groups:
- **Personal** — calendars that are NOT holiday calendars (id does NOT contain `#holiday@group.v.calendar.google.com`)
- **Holidays** — calendars whose id contains `#holiday@group.v.calendar.google.com`

**Deduplication for holidays:** Multiple holiday calendars may cover the same country in different languages (e.g. `uk.ukrainian#holiday`, `ru.ukrainian#holiday`, `en.ukrainian#holiday`). Deduplicate by country — prefer the Russian-language variant (`ru.*`), then Ukrainian (`uk.*`), then English (`en.*`). This avoids showing the same holiday 2-3 times.

### 3. Fetch events for each calendar

For each calendar (after dedup), call `gcal_list_events` with:
- `calendarId`: the calendar's `id`
- `timeMin`: target date at `00:00:00`
- `timeMax`: target date at `23:59:59`
- `timeZone`: `Europe/Sofia`

Make parallel calls when possible.

### 4. Format the summary

Format events in two sections: personal events first, then holidays.

```
📅 Календарь на [дата, например "28 марта, суббота"]

🕐 09:00–11:30 — Стоматолог
   📍 ул. Казбек 57А

🕐 14:00–15:00 — Встреча с командой

—
🎉 Праздники:
🇺🇦 День Конституції
🇧🇬 Ден на Освобождението

—
📊 Всего: X событий, Y праздников
```

Rules:
- Show time as `HH:MM–HH:MM` for timed events
- Show `Весь день` for all-day events (list them first)
- Include `📍 location` only if the event has a location
- Include `📆 calendar name` for personal events only if there are events from multiple personal calendars
- Holidays section: prefix each holiday with a country flag — 🇺🇦 for Ukrainian, 🇧🇬 for Bulgarian holidays
- Always show the header line `📅 Календарь на [дата]` and the footer with stats
- If no personal events: show "Событий нет" in the personal section
- If no holidays: show "Праздников нет" in the holidays section
- This way the user always sees a complete message and knows the skill ran successfully
- All text in Russian

### 5. Deliver

- If triggered from Telegram (`<channel source="plugin:telegram:telegram"`), send via `mcp__plugin_telegram_telegram__reply` to the appropriate `chat_id`.
- If running in terminal, print the result directly.

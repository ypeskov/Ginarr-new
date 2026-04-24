# `/calendar-digest` — Google Calendar agenda

Fetches events from all accessible Google Calendars for a target day (today / tomorrow / a specific date) and renders a Russian summary with personal events plus deduplicated holidays, delivered to Telegram or terminal.

## Source

- Skill: [`.claude/skills/calendar-digest/SKILL.md`](../../.claude/skills/calendar-digest/SKILL.md) — authoritative behaviour.
- No local scripts — all fetching goes through the Google Calendar MCP server.
- Origin: copied from `~/OpenClaw/.claude/skills/calendar-digest/` (2026-04-24).

## Dependencies

- Google Calendar MCP server wired into Claude Code. Required MCP tools: `gcal_list_calendars`, `gcal_list_events`.
- Telegram MCP plugin for chat delivery.

## Usage

- `/calendar-digest` — today.
- `/calendar-digest tomorrow` — next day.
- `/calendar-digest YYYY-MM-DD` — specific date.

## Integration notes

- Timezone is hard-coded to `Europe/Sofia`. Matches the owner's default (`memory/user_default_timezone.md`). If the owner travels and wants per-run overrides, SKILL.md needs editing.
- Holiday dedup order: `ru.*` → `uk.*` → `en.*`. Ukrainian and Bulgarian calendars get flag emojis (🇺🇦 / 🇧🇬); other countries fall back to a generic format.
- No interaction with Ginarr's memory layer.

## Follow-ups

- If a Google Calendar account is added or revoked, no code change is needed — the skill enumerates calendars dynamically each run.

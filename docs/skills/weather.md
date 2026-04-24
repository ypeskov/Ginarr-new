# `/weather` — forecast via Open-Meteo

Fetches a weather forecast for a given city and delivers it to Telegram or terminal. Uses the free Open-Meteo API — no key, no quota concerns.

## Source

- Skill: [`.claude/skills/weather/SKILL.md`](../../.claude/skills/weather/SKILL.md) — authoritative behaviour.
- Fetcher: `.claude/skills/weather/scripts/forecast.py` — pure `urllib`, stdlib only.
- Origin: copied from `~/OpenClaw/.claude/skills/weather/` (2026-04-24).

## Dependencies

- `python3` (stdlib `urllib` is enough).
- Telegram MCP plugin for chat delivery.

## Usage

- `/weather` — default: Sofia, 7 days.
- `/weather <city>` — other city, default 7 days.
- `/weather <city> <days>` — bounded by what Open-Meteo supports.

Full argument contract is in SKILL.md.

## Integration notes

- No memory-layer interaction.
- Open-Meteo is keyless — there is nothing to provision.
- Default "Sofia" matches the owner's base timezone, already recorded in `memory/user_default_timezone.md`.

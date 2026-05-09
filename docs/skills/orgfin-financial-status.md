# `orgfin-financial-status` — read the owner's finances from orgfin.run

Pulls live financial data from the owner's tracker at `https://api.orgfin.run`. Routed for any "balance / spending / upcoming bills / cash flow" question, even when the user doesn't name the tracker.

## Source

- Skill: [`.claude/skills/orgfin-financial-status/SKILL.md`](../../.claude/skills/orgfin-financial-status/SKILL.md) — authoritative behaviour, dispatch rules, presentation conventions.
- Client: `.claude/skills/orgfin-financial-status/scripts/orgfin_client.py` — pure `urllib`, stdlib only, one retry on 429.

## Dependencies

- `python3` (stdlib `urllib` is enough).
- `pass` entry at `orgfin/api-key`. Provision once with:
  ```
  pass insert orgfin/api-key
  ```
- Network reachability to `api.orgfin.run`.

## API surface

Three GET endpoints, all returning JSON:

| Endpoint | Purpose | Notes |
|---|---|---|
| `/export/json?start_date=&end_date=` | Historical transactions | Max range 1096 days |
| `/export/json/balance?date=` | Balances per account on date | Per-account currency + base currency |
| `/export/json/planned?start_date=&end_date=` | Upcoming scheduled txs | `start_date` must be today or future |

Auth: `X-API-Key` header. Rate limits: 60 rpm/IP, 20 rpm/key.

## Usage

The skill reads the key from `pass` at call time and passes it via `--api-key`:

```bash
API_KEY=$(pass show orgfin/api-key)
python3 scripts/orgfin_client.py --api-key "$API_KEY" transactions --start 2026-04-01 --end 2026-05-08
python3 scripts/orgfin_client.py --api-key "$API_KEY" balance --date 2026-05-08
python3 scripts/orgfin_client.py --api-key "$API_KEY" planned --start 2026-05-08 --end 2026-08-08
```

The CLI prints raw JSON to stdout; the assistant parses and summarizes it before replying. Errors land on stderr with a non-zero exit code. The script does not log the key.

## Integration notes

- Read-only: skill never writes to the vault. It's a live API client, not a cache.
- No cron — every call is owner-triggered.
- Key is stored in `pass` (`orgfin/api-key`), not in the script. To rotate: regenerate the key in orgfin.run, then `pass insert orgfin/api-key`. Nothing else changes.

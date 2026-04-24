# `/news-digest` — RSS + HN + portfolio summary

Collects stories from RSS feeds, Hacker News, and an ETF portfolio (yfinance), produces a categorised Russian digest (AI, IT, Ukraine, portfolio), delivers to Telegram or terminal.

## Source

- Skill: [`.claude/skills/news-digest/SKILL.md`](../../.claude/skills/news-digest/SKILL.md) — authoritative behaviour.
- Fetchers:
  - `.claude/skills/news-digest/scripts/fetch_news.py` — RSS + HN ingest.
  - `.claude/skills/news-digest/scripts/fetch_etf.py` — portfolio quotes via `yfinance`.
- Origin: copied from `~/OpenClaw/.claude/skills/news-digest/` (2026-04-24).

## Dependencies

- `python3`, `feedparser`, `yfinance`.
- Telegram MCP plugin for chat delivery.

## Runtime artefact

The skill writes a transient `last_digest.md` inside its own directory. It is regenerated on every run and is gitignored — see [`.gitignore`](../../.gitignore). Do not stage it.

## Integration notes

- Feed list and portfolio tickers live inside the scripts. Swapping feeds means editing `fetch_news.py`; swapping tickers means editing `fetch_etf.py`.
- No interaction with Ginarr's memory layer.

## Follow-ups

- Feed list drift is expected. Note every feed swap in the commit that changes it.

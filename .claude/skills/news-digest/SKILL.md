---
name: news-digest
description: >
  Collect news from RSS feeds, Hacker News, and ETF portfolio data. Summarize
  top stories in AI, IT, Ukraine, and investment portfolio. Send digest to
  Telegram or display in terminal. Use when the user asks about news, digest,
  headlines, what's happening, or "what's new in AI/tech/Ukraine."
compatibility: Requires python3, feedparser, yfinance
allowed-tools: Bash(python3 *) mcp__plugin_telegram_telegram__reply
metadata:
  author: openclaw
  version: "2.0"
---

# /news-digest — News Digest

Fetches news from multiple sources, selects top stories, and produces a categorized digest with summaries in Russian.

## Arguments

- No arguments: all categories (ai, it, ua, etf)
- `ai` — only AI news
- `it` — only IT/tech news
- `ua` — only Ukraine news
- `etf` — only ETF portfolio
- Can combine: `ai it`, `ai ua etf`, etc.

## Instructions

### 1. Fetch news

```bash
python3 scripts/fetch_news.py --categories ai it ua
```

Run `python3 scripts/fetch_news.py --help` for full usage.

Output: JSON with category keys, each containing an array of articles `{title, link, date, summary, source}`.

### 2. Fetch ETF data (if etf category requested)

```bash
python3 scripts/fetch_etf.py
```

Output: JSON array `{ticker, price, change, pct}`.

### 3. Analyze and compose digest

From the raw JSON:
- **Check history first**: Read `$CLAUDE_PROJECT_DIR/.claude/scripts/logs/news-sent-titles.txt` — this file contains titles of previously sent stories. **SKIP any story whose title closely matches** a previously sent one (fuzzy match — same topic counts as duplicate even if wording differs slightly).
- Select **top 5 most interesting NEW stories** per category from the last 24-48 hours
- **AI**: breakthroughs, major releases, partnerships, funding, policy
- **IT**: trending stories, security incidents, product launches, industry shifts
- **Ukraine**: most significant political, military, economic developments
- Write **2-3 sentence summary in Russian** for each story. Include the original link.
- **Deduplicate**: if same story in multiple feeds, merge and pick best source link
- **After composing**: append all sent story titles (one per line) to `$CLAUDE_PROJECT_DIR/.claude/scripts/logs/news-sent-titles.txt`. Keep only last 200 lines to prevent file bloat.
- **ETF**: format as list with price, change %, emoji. Alert if any ETF moves ±3%.

### 4. Format (MarkdownV2 for Telegram)

Use `format: markdownv2` when sending. Escape all special chars (`. - ( ) ! + = | { } > # ~`).

```
📰 ДАЙДЖЕСТ | [date], [time of day Sofia]

━━━━━━━━━━━━━━━━━━

*🤖 ИИ*

1\. *[заголовок]*
   [2-3 предложения саммари]
   🔗 [ссылка](url)

━━━━━━━━━━━━━━━━━━

*💻 IT*
[same format]

━━━━━━━━━━━━━━━━━━

*📈 ПОРТФЕЛЬ ETF*
• VUAA: €XXX\.XX \(+X\.XX%\) 🟢
• IJPA: €XXX\.XX \(-X\.XX%\) 🔴

━━━━━━━━━━━━━━━━━━

*🇺🇦 Украина*
[same format]
```

Time of day (Sofia): morning (07:00) → "утро", evening (18:00) → "вечер".

### 5. Deliver

**Send to BOTH destinations:**
1. Group chat: `chat_id = "-1003801041030"`
2. Personal DM: `chat_id = "353065630"`

Send identical content to both. If one fails, still send to the other.
If running in terminal, print the result.

### 6. Error handling

If a source fails, skip it and continue. Mention failed sources at the bottom.

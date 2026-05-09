---
name: orgfin-financial-status
description: Retrieve the user's personal financial data from their orgfin.run financial tracker via API. Use this skill whenever the user asks about their balance, account balances, net worth, recent transactions, past spending, income, where their money went, upcoming bills, scheduled payments, planned transactions, cash flow, or anything else about their personal finances. Trigger this even for casual or indirect phrasings like "how much do I have", "what did I spend last month", "do I have any bills coming up", "сколько у меня денег", "что у меня по деньгам", or anything similar — the user does not need to mention orgfin or "the tracker" by name. The user only has one financial tracker, so any personal-finance question routes here.
compatibility: Requires python3 (urllib stdlib only) and pass (orgfin/api-key)
allowed-tools: Bash(python3 *) Bash(pass show *)
---

# orgfin Financial Tracker

This skill fetches the user's financial data from their orgfin.run tracker. The user only has one tracker, so every "what's my balance / what did I spend / what's coming up" question is answered through here, not from memory or guessing.

## API basics

- Base URL: `https://api.orgfin.run`
- Auth header: `X-API-Key: <value from pass>`
- Date format: ISO calendar date `YYYY-MM-DD`
- Rate limits: 60 requests/minute per IP, 20 requests/minute per API key (shared across all three endpoints below). One or two calls per question is normal — don't loop hammer the API.

## The three endpoints

### 1. Transaction history — what already happened

```
GET /export/json?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
```

Returns historical transactions. Maximum range is **1096 days** (≈3 years). If the user asks for a longer window, split into multiple calls or tell them the limit.

Use this for: past spending, income, "what did I spend on X", monthly category breakdowns, "where did my money go", anomaly hunting, year-over-year comparisons.

### 2. Balance snapshot — what was in the accounts on a given date

```
GET /export/json/balance?date=YYYY-MM-DD
```

Returns balances per account on that specific date, in both account currency and base currency.

Use this for: "what's my balance" (use today's date), "what did I have at the end of last month", net worth questions, account-by-account breakdowns. For a "current balance" question, pass today's date.

### 3. Planned transactions — what's scheduled to happen

```
GET /export/json/planned?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
```

Returns upcoming scheduled transactions. Recurring rules are expanded into individual occurrences in the range. **`start_date` must be today or in the future** — past dates will fail.

Use this for: upcoming bills, scheduled payments, expected income, "what's due this month", forward cash-flow questions.

## How to call the API

### 1. Read the API key from pass

```bash
pass show orgfin/api-key
```

Capture the output as `API_KEY`. If `pass` fails, tell the user the key is missing and stop. The recovery hint is: `pass insert orgfin/api-key`.

### 2. Run the bundled Python client

The client at `scripts/orgfin_client.py` handles headers, retries, and error formatting. Pass the key via `--api-key`:

```bash
python3 scripts/orgfin_client.py --api-key "$API_KEY" transactions --start 2026-04-01 --end 2026-05-08
python3 scripts/orgfin_client.py --api-key "$API_KEY" balance --date 2026-05-08
python3 scripts/orgfin_client.py --api-key "$API_KEY" planned --start 2026-05-08 --end 2026-08-08
```

The script prints raw JSON to stdout, which you can then parse and summarize. It does not echo the key. If you'd rather call the API directly with `curl` or `requests`, the same `X-API-Key` header value applies.

## Choosing dates

Always resolve "current"/"today"/"now" using the actual current date at runtime, not a hardcoded one.

| User says | Use |
|---|---|
| "current balance" / "right now" / "today" | balance endpoint, date = today |
| "last month" / "past 30 days" | transactions, end = today, start = today − 30 |
| a specific named month ("April", "January 2026") | transactions, calendar boundaries of that month |
| "this year" / "year to date" | transactions, start = Jan 1 of current year, end = today |
| "upcoming" / "coming up" / "what's due" | planned, start = today, end = today + 30 (default) or + 90 for broader |
| "this quarter" / "next quarter" | planned or transactions with quarter boundaries |

If the range is genuinely ambiguous, pick a reasonable default and mention what you used in one short line — don't interrogate the user before answering.

## Presenting results

The user prefers short, chat-style responses without ceremony. Specifically:

- **Lead with the answer.** The actual number first, breakdown after.
- **Use base currency for cross-account totals.** Per-account currencies are fine for individual account lines.
- **Summarize, don't dump.** Never paste raw JSON unless asked. Group transactions by category or merchant when it adds clarity, list flat when it doesn't.
- **Flag real anomalies, don't manufacture them.** A charge meaningfully bigger than the user's usual pattern, an unexpected income, a missed scheduled payment — worth mentioning. Generic "your spending was high this month" filler — skip.
- **Round sensibly.** Whole units of base currency for totals, two decimals only when precision matters.
- **Tone matches the user's.** If they asked casually, answer casually. Dark humor about money is fine when the situation invites it. No corporate-finance lecture voice.

## Error handling

- `401` / `403` → API key was rejected. Tell the user, suggest `pass insert orgfin/api-key`, don't retry.
- `429` → rate limited. The script already retries once after ~5s. If it still fails, tell the user and stop.
- `400` on the planned endpoint → most likely `start_date` is in the past. Reset to today and retry.
- `400` on transactions with a "range too large" type message → window exceeds 1096 days. Either narrow the request or split into chunks.
- Other errors → show the status and message, ask the user how to proceed.

## A few worked examples

**"What's my balance?"**
→ Read key from `pass`, call `balance --date <today>`. Sum balances in base currency for the headline number, then list per-account lines underneath.

**"What did I spend on groceries last month?"**
→ Read key from `pass`, call `transactions --start <first day of last month> --end <last day of last month>`. Filter to grocery category, sum, present as one line with maybe top 3 merchants.

**"Do I have any big bills coming up?"**
→ Read key from `pass`, call `planned --start <today> --end <today + 30>`. Filter to outflows, sort by amount descending, show the top few. If nothing notable, say so plainly.

**"How am I doing financially?"**
→ This needs more than one call. Get current balance + last 30 days of transactions + upcoming 30 days of planned. Synthesize: balance, net cash flow last month, what's coming up, anything unusual. Keep it tight — a few lines, not a report.

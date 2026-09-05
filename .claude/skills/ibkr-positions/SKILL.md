---
name: ibkr-positions
description: >
  Show unrealized profit / loss for every open position in the owner's
  Interactive Brokers account, in EUR and in percent from the average purchase
  price, plus the portfolio total and today's move. Use when the user asks how
  his stocks / positions / portfolio are doing, "как там мои акции", "сколько
  я в плюсе", "покажи позиции", "что по IBKR", "проверь брокера", or wants the
  per-position percentage the IBKR dashboard does not show. Read-only; never
  places orders or moves money.
compatibility: Requires the Interactive Brokers (IBKR) MCP connector on the claude.ai account and python3 (stdlib only)
allowed-tools: mcp__claude_ai_Interactive_Brokers_IBKR__get_account_positions mcp__claude_ai_Interactive_Brokers_IBKR__get_account_balances mcp__claude_ai_Interactive_Brokers_IBKR__get_account_summary Bash(python3 *) Bash(cat *) mcp__plugin_telegram_telegram__reply
metadata:
  author: ginarr
  version: "1.0"
---

# /ibkr-positions — Open positions P&L

Answers "how are my stocks doing" with a per-position and total unrealized
result, in EUR and in percent from the average purchase price. This is the
number the IBKR dashboard does not draw: the dashboard shows time-weighted
return for the whole account over a period, which is a different question.

## Arguments

- No arguments: text summary in Russian.
- `--json`: machine-readable output (used when another skill needs the numbers).

## Instructions

### 1. Fetch the data

Call these two MCP tools in parallel:

- `get_account_positions` — the source of truth. Each row carries `position`
  (quantity), `average_price`, `market_price`, `currency`, `daily_pnl`.
- `get_account_balances` — FX rates for non-EUR positions (`exchange_rate` per
  currency) and the account-level `unrealized_pnl` used as a cross-check.

If the positions tool errors with an auth / connector message, stop and tell
the owner the IBKR connector is unavailable. Do not guess numbers from memory.

### 2. Compute with the bundled script

Write both JSON payloads to the scratchpad directory and run:

```bash
python3 .claude/skills/ibkr-positions/scripts/pnl.py --balances <balances.json> < <positions.json>
```

Add `--json` when the caller asked for JSON. The script prints one line per
position sorted by EUR gain (largest first) and a total line. It does the
arithmetic so you don't: never compute the percentages by hand.

Formula the script uses, for the record:

- cost = quantity × average_price × fx
- value = quantity × market_price × fx
- pnl_eur = value − cost
- pnl_pct = pnl_eur / cost × 100
- total = sums over positions; total_pct = total_pnl / total_cost × 100

Exit code 2 means no open positions; say so and stop.

### 3. Cross-check against the account summary

Compare the script's total `pnl_eur` with `unrealized_pnl` from
`get_account_balances` (the `BASE` row). A gap of a few EUR is normal: the two
endpoints snapshot prices at different moments. Mention the account figure only
if the gap exceeds ~2% of total P&L, and then say which one is which.

### 4. Deliver

Lead with a one-line human read, then paste the script's table verbatim inside
a fenced code block so the columns stay aligned in both terminal and Telegram.
Russian, short, companion register per `CLAUDE.md` Tone. Example shape:

```
Всё в плюсе, тянет ASML.

Бумага  Шт   Покупка    Сейчас    P&L €   P&L %  День €
------  --  --------  --------  -------  ------  ------
ASML     1   1373.35   1469.80   +96.45   +7.0%  +46.40
SAP      2    153.91    184.82   +61.82  +20.1%   -1.52
SU       1    268.90    288.40   +19.50   +7.2%   +1.05
------  --  --------  --------  -------  ------  ------
Итого       1 950.07  2 127.84  +177.77   +9.1%  +45.93
```

Do not restate the totals in prose after the table; the "Итого" row is the
answer. Mention the account-level figure only under the rule in step 3.

- If triggered from Telegram (`<channel source="telegram"`), send via
  `mcp__plugin_telegram_telegram__reply` to that `chat_id`.
- In the terminal, print directly.

### 5. What this skill does not do

- No orders, no transfers, no alerts. Read-only by design.
- No realized P&L or trade history. If the owner asks "how much did I make
  this year", that is `get_account_trades` + `get_pa_performance_all_periods`
  territory, not this skill.
- No time-weighted return. If the owner asks why the dashboard shows a
  different percentage, explain TWR vs. per-position P&L; do not try to
  reconcile them numerically.

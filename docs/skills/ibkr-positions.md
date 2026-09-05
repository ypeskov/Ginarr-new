# `/ibkr-positions` — open positions P&L

Reads the owner's open positions from the Interactive Brokers MCP connector and prints unrealized profit / loss per position and in total, in EUR and in percent from the average purchase price, plus today's move. Read-only.

## Source

- Skill: [`.claude/skills/ibkr-positions/SKILL.md`](../../.claude/skills/ibkr-positions/SKILL.md) — authoritative behaviour.
- Script: [`.claude/skills/ibkr-positions/scripts/pnl.py`](../../.claude/skills/ibkr-positions/scripts/pnl.py) — pure-stdlib Python, takes `get_account_positions` JSON on stdin, optional `--balances <file>` for FX rates, `--json` for machine output. Does all arithmetic so the model never computes percentages by hand.

## Dependencies

- Interactive Brokers (IBKR) MCP connector attached to the owner's claude.ai account. The connector is account-scoped, not instance-scoped: any Claude session under the same account (server, laptop) sees the same tools. Required tools: `get_account_positions`, `get_account_balances`; `get_account_summary` is allowed but optional.
- Telegram MCP plugin for chat delivery.

## Usage

- `/ibkr-positions` — Russian text summary.
- `/ibkr-positions --json` — JSON for other skills.

## Integration notes

- Source of truth is the positions endpoint. The account-level `unrealized_pnl` from balances is a cross-check only; the two endpoints snapshot prices at different moments and differ by a few EUR. The skill mentions the account figure only when the gap exceeds ~2%.
- Base currency is EUR. Non-EUR positions are converted with the `exchange_rate` from balances; the script exits 1 if a rate is missing.
- This answers a different question than the IBKR dashboard's headline percentage, which is time-weighted return over a period. The skill explains the difference on request but does not reconcile them.
- No interaction with Ginarr's memory layer. If the owner's holdings become worth remembering, that is `capture`'s job, not this skill's.

## Follow-ups

- If the owner asks for realized P&L or trade history, that would be a separate skill over `get_account_trades` / `get_pa_performance_all_periods`.

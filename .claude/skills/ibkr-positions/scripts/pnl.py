#!/usr/bin/env python3
"""Compute per-position and total P&L (EUR and %) from IBKR MCP JSON.

Reads the JSON returned by `get_account_positions` on stdin and prints a
Russian-language summary. Optionally accepts `get_account_balances` JSON via
--balances to cross-check the total and to pick up FX rates for non-EUR
positions.

Usage:
    python3 pnl.py < positions.json
    python3 pnl.py --balances balances.json < positions.json
    python3 pnl.py --json < positions.json      # machine-readable output

Exit codes: 0 ok, 1 bad input, 2 no positions.
"""
import argparse
import json
import sys

BASE = "EUR"


def load_rates(balances_path):
    """Return {currency: rate_to_base} from get_account_balances output."""
    if not balances_path:
        return {}
    with open(balances_path, encoding="utf-8") as fh:
        data = json.load(fh)
    rates = {}
    for row in data.get("balances", []):
        cur = row.get("currency")
        rate = row.get("exchange_rate")
        if cur and cur != "BASE" and rate:
            rates[cur] = float(rate)
    return rates


def fmt_num(value):
    return f"{value:,.2f}".replace(",", " ")


def fmt_eur(value):
    sign = "+" if value >= 0 else "-"
    return f"{sign}{abs(value):,.2f}".replace(",", " ")


def fmt_pct(value):
    sign = "+" if value >= 0 else "-"
    return f"{sign}{abs(value):.1f}%"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--balances", help="path to get_account_balances JSON")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args()

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"bad JSON on stdin: {exc}", file=sys.stderr)
        return 1

    positions = payload.get("positions") or []
    if not positions:
        print("Открытых позиций нет.")
        return 2

    rates = load_rates(args.balances)
    rows = []
    total_cost = 0.0
    total_value = 0.0
    total_daily = 0.0
    for pos in positions:
        qty = float(pos.get("position", 0))
        avg = float(pos.get("average_price", 0))
        price = float(pos.get("market_price", 0))
        cur = pos.get("currency", BASE)
        rate = 1.0 if cur == BASE else rates.get(cur)
        if rate is None:
            print(f"no FX rate for {cur}; pass --balances", file=sys.stderr)
            return 1
        cost = qty * avg * rate
        value = qty * price * rate
        pnl = value - cost
        pct = (pnl / cost * 100) if cost else 0.0
        daily = float(pos.get("daily_pnl", 0)) * rate
        ticker = pos.get("contract_description", "?").split("@")[0].strip()
        rows.append({
            "ticker": ticker,
            "qty": qty,
            "avg_price": avg,
            "market_price": price,
            "currency": cur,
            "cost_eur": round(cost, 2),
            "value_eur": round(value, 2),
            "pnl_eur": round(pnl, 2),
            "pnl_pct": round(pct, 2),
            "daily_eur": round(daily, 2),
        })
        total_cost += cost
        total_value += value
        total_daily += daily

    total_pnl = total_value - total_cost
    total_pct = (total_pnl / total_cost * 100) if total_cost else 0.0
    rows.sort(key=lambda r: r["pnl_eur"], reverse=True)

    summary = {
        "positions": rows,
        "total": {
            "cost_eur": round(total_cost, 2),
            "value_eur": round(total_value, 2),
            "pnl_eur": round(total_pnl, 2),
            "pnl_pct": round(total_pct, 2),
            "daily_eur": round(total_daily, 2),
        },
    }

    if args.json:
        json.dump(summary, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0

    header = ("Бумага", "Шт", "Покупка", "Сейчас", "P&L €", "P&L %", "День €")
    body = []
    for r in rows:
        qty = int(r["qty"]) if r["qty"].is_integer() else r["qty"]
        body.append((
            r["ticker"],
            str(qty),
            f"{r['avg_price']:.2f}",
            f"{r['market_price']:.2f}",
            fmt_eur(r["pnl_eur"]),
            fmt_pct(r["pnl_pct"]),
            fmt_eur(r["daily_eur"]),
        ))
    footer = (
        "Итого", "", fmt_num(total_cost), fmt_num(total_value),
        fmt_eur(total_pnl), fmt_pct(total_pct), fmt_eur(total_daily),
    )
    widths = [max(len(row[i]) for row in [header, footer, *body]) for i in range(len(header))]

    def line(row):
        cells = [row[0].ljust(widths[0])] + [row[i].rjust(widths[i]) for i in range(1, len(row))]
        return "  ".join(cells)

    rule = "  ".join("-" * w for w in widths)
    print(line(header))
    print(rule)
    for row in body:
        print(line(row))
    print(rule)
    print(line(footer))
    return 0


if __name__ == "__main__":
    sys.exit(main())

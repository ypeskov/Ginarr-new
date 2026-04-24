#!/usr/bin/env python3
"""Fetch ETF portfolio prices via yfinance and output as JSON.

Usage:
  python3 scripts/fetch_etf.py

Output: JSON array of ETF objects to stdout.
  Each object: {ticker, price, change, pct} or {ticker, error}.
Exit codes: 0 = success, 1 = all tickers failed.
"""

import json
import sys

try:
    import yfinance as yf
except ImportError:
    print("Error: yfinance not installed. Run: pip install yfinance", file=sys.stderr)
    sys.exit(2)

TICKERS = {
    "VUAA.DE": "VUAA",
    "IJPA.AS": "IJPA",
    "MEUD.PA": "MEUD",
    "SXRV.DE": "SXRV",
}


def main():
    etfs = []
    errors = 0
    for yahoo_t, display_t in TICKERS.items():
        try:
            t = yf.Ticker(yahoo_t)
            info = t.fast_info
            price = info.last_price
            prev = info.previous_close
            change = price - prev
            pct = (change / prev) * 100
            etfs.append({
                "ticker": display_t,
                "price": round(price, 2),
                "change": round(change, 2),
                "pct": round(pct, 2),
            })
        except Exception as e:
            errors += 1
            etfs.append({"ticker": display_t, "error": str(e)})

    print(json.dumps(etfs, ensure_ascii=False))
    sys.exit(1 if errors == len(TICKERS) else 0)


if __name__ == "__main__":
    main()

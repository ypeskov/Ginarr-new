#!/usr/bin/env python3
"""orgfin.run API client for the user's financial tracker.

Usage:
    python orgfin_client.py --api-key KEY transactions --start YYYY-MM-DD --end YYYY-MM-DD
    python orgfin_client.py --api-key KEY balance --date YYYY-MM-DD
    python orgfin_client.py --api-key KEY planned --start YYYY-MM-DD --end YYYY-MM-DD

The API key is supplied by the caller (typically read from
`pass show orgfin/api-key` in the SKILL.md instructions). Prints the raw
JSON response to stdout. Errors go to stderr with a non-zero exit code,
so the caller can detect failures cleanly.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://api.orgfin.run"
TIMEOUT = 30


def fetch(api_key: str, path: str, params: dict) -> dict:
    """GET {BASE_URL}{path}?{params} with one retry on 429."""
    qs = urllib.parse.urlencode(params)
    url = f"{BASE_URL}{path}?{qs}"
    req = urllib.request.Request(url, headers={"X-API-Key": api_key})

    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code == 429 and attempt == 1:
                # Rate limited — wait and retry once.
                time.sleep(5)
                continue
            sys.stderr.write(f"HTTP {e.code} from {url}\n{body}\n")
            sys.exit(1)
        except urllib.error.URLError as e:
            sys.stderr.write(f"Network error reaching {url}: {e}\n")
            sys.exit(1)

    # Unreachable, but keeps type-checkers happy.
    sys.exit(1)


def cmd_transactions(args: argparse.Namespace) -> dict:
    return fetch(
        args.api_key,
        "/export/json",
        {"start_date": args.start, "end_date": args.end},
    )


def cmd_balance(args: argparse.Namespace) -> dict:
    return fetch(args.api_key, "/export/json/balance", {"date": args.date})


def cmd_planned(args: argparse.Namespace) -> dict:
    return fetch(
        args.api_key,
        "/export/json/planned",
        {"start_date": args.start, "end_date": args.end},
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="orgfin.run API client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--api-key",
        required=True,
        help="X-API-Key header value (typically `pass show orgfin/api-key`)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("transactions", help="Historical transactions (max 1096 days)")
    t.add_argument("--start", required=True, metavar="YYYY-MM-DD")
    t.add_argument("--end", required=True, metavar="YYYY-MM-DD")
    t.set_defaults(func=cmd_transactions)

    b = sub.add_parser("balance", help="Account balances on a given date")
    b.add_argument("--date", required=True, metavar="YYYY-MM-DD")
    b.set_defaults(func=cmd_balance)

    pl = sub.add_parser("planned", help="Upcoming scheduled transactions")
    pl.add_argument("--start", required=True, metavar="YYYY-MM-DD",
                    help="Must be today or a future date")
    pl.add_argument("--end", required=True, metavar="YYYY-MM-DD")
    pl.set_defaults(func=cmd_planned)

    return p


def main() -> None:
    args = build_parser().parse_args()
    data = args.func(args)
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

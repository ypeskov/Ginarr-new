#!/usr/bin/env python3
"""Fetch weight and food history from kcal.peskov.info into the Auto-Wiki vault.

Writes raw JSON to:
  $GINARR_VAULT_ROOT/wiki/entities/fitness/_data/<from>_to_<to>_<type>.json

Exit codes: 0 success, 1 HTTP/network error, 2 invalid arguments.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import date, timedelta

API_BASE = "https://kcal.peskov.info/api/v1/data"


def parse_args():
    p = argparse.ArgumentParser(description="Fetch fitness history from kcal.peskov.info")
    p.add_argument("--api-key", required=True, help="X-API-Key header value")
    p.add_argument("--type", choices=["weight", "food", "both"], default="both")
    p.add_argument("--from", dest="date_from", help="Start date YYYY-MM-DD")
    p.add_argument("--to", dest="date_to", help="End date YYYY-MM-DD")
    p.add_argument("--days", type=int, help="Last N days (overrides --from/--to if neither given)")
    args = p.parse_args()

    if args.date_from and args.date_to:
        return args.date_from, args.date_to, args.type, args.api_key
    if args.date_from or args.date_to:
        print("error: --from and --to must be provided together", file=sys.stderr)
        sys.exit(2)

    days = args.days if args.days is not None else 30
    if days < 1:
        print("error: --days must be >= 1", file=sys.stderr)
        sys.exit(2)
    today = date.today()
    return (
        (today - timedelta(days=days - 1)).isoformat(),
        today.isoformat(),
        args.type,
        args.api_key,
    )


def vault_data_dir():
    root = os.environ.get("GINARR_VAULT_ROOT")
    if not root:
        print("error: GINARR_VAULT_ROOT is not set", file=sys.stderr)
        sys.exit(2)
    path = os.path.join(root, "wiki", "entities", "fitness", "_data")
    os.makedirs(path, exist_ok=True)
    return path


def fetch(api_key, date_from, date_to, type_):
    qs = f"?type={type_}&from={date_from}&to={date_to}"
    req = urllib.request.Request(API_BASE + qs, headers={"X-API-Key": api_key})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
            return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        return e.code, body
    except urllib.error.URLError as e:
        print(f"error: network failure: {e.reason}", file=sys.stderr)
        sys.exit(1)


def main():
    date_from, date_to, type_, api_key = parse_args()
    status, body = fetch(api_key, date_from, date_to, type_)

    if status >= 400:
        excerpt = body[:500].decode("utf-8", errors="replace")
        print(f"error: HTTP {status}: {excerpt}", file=sys.stderr)
        sys.exit(1)

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as e:
        print(f"error: response is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    out_dir = vault_data_dir()
    out_path = os.path.join(out_dir, f"{date_from}_to_{date_to}_{type_}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)

    if isinstance(parsed, dict):
        keys = sorted(parsed.keys())
        shape = f"dict, keys={keys}"
    elif isinstance(parsed, list):
        shape = f"list, len={len(parsed)}"
    else:
        shape = type(parsed).__name__

    size = os.path.getsize(out_path)
    print(f"ok: {out_path}  ({size} bytes, {shape})")


if __name__ == "__main__":
    main()

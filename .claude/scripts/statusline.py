#!/usr/bin/env python3
"""Ginarr status line. Reads Claude Code statusLine JSON on stdin, prints one line."""
import json, os, sys


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n // 1000}k"
    return str(n)


def fmt_window(n: int) -> str:
    if n >= 1_000_000:
        return f"{n // 1_000_000}M"
    if n >= 1_000:
        return f"{n // 1000}k"
    return str(n)


def last_usage_from_transcript(path: str):
    try:
        with open(path, "rb") as f:
            try:
                f.seek(-200_000, os.SEEK_END)
            except OSError:
                f.seek(0)
            tail = f.read().decode("utf-8", errors="ignore").splitlines()
    except OSError:
        return None
    last = None
    for line in tail:
        if '"usage"' not in line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        u = (d.get("message") or {}).get("usage")
        if u:
            last = u
    return last


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}

    cost = (data.get("cost") or {}).get("total_cost_usd")

    model_id = ((data.get("model") or {}).get("id") or "").lower()
    window = 1_000_000 if "[1m]" in model_id else 200_000

    ctx_used = None
    tpath = data.get("transcript_path")
    if tpath and os.path.isfile(tpath):
        u = last_usage_from_transcript(tpath)
        if u:
            ctx_used = (u.get("input_tokens") or 0) \
                     + (u.get("cache_creation_input_tokens") or 0) \
                     + (u.get("cache_read_input_tokens") or 0)

    CYAN, YEL, GRN, DIM, RST = "\033[01;36m", "\033[01;33m", "\033[01;32m", "\033[02m", "\033[00m"
    parts = [f"{CYAN}[Ginarr]{RST}"]
    if ctx_used is not None:
        pct = ctx_used * 100 / window
        parts.append(f"{YEL}ctx:{fmt_tokens(ctx_used)}/{fmt_window(window)} ({pct:.0f}%){RST}")
    if cost is not None:
        parts.append(f"{GRN}${cost:.2f}{RST}")
    sys.stdout.write(f" {DIM}·{RST} ".join(parts))


if __name__ == "__main__":
    main()

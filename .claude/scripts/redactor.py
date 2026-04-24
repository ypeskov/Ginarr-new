#!/usr/bin/env python3
"""Layer 2 + Layer 3 secret redactor for chat-memory.

Reads text from a file or stdin, applies regex-based redaction for known
secret formats (Layer 2) and an optional owner-marked denylist (Layer 3),
writes the redacted text to stdout.

Usage:
    redactor.py [infile] [--denylist-file PATH]
    redactor.py --self-test

Contract (SPEC.v3 §"Portable tools"): one file, pure Python, stdlib only.
"""
from __future__ import annotations

import argparse
import re
import sys
from typing import Iterable

# SPEC.v3 §"Secrets and PII" — Layer 2 known token formats.
# Note: the PEM pattern here extends SPEC.v3's literal (which ends at "-----END")
# to match the full PEM footer; treating the spec literal as a typo.
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("aws_access_key", re.compile(r"(?:AKIA|ASIA)[0-9A-Z]{16}")),
    ("github_token",   re.compile(r"gh[pos]_[0-9a-zA-Z]{36}")),
    ("openai_key",     re.compile(r"sk-[a-zA-Z0-9]{20,}")),
    ("slack_token",    re.compile(r"xox[baprs]-[0-9a-zA-Z-]+")),
    ("stripe_key",     re.compile(r"sk_live_[0-9a-zA-Z]{24}")),
    ("connection_string", re.compile(
        r"(?:postgres|mysql|redis|mongodb)://[^:\s]+:[^@\s]+@[^\s]+"
    )),
    ("pem_private_key", re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"
    )),
    ("generic_secret", re.compile(
        r"(?i)(?:api[_-]?key|token|secret|password)[\"\s:=]+[^\s\"']{12,}"
    )),
]


def redact(text: str, denylist: Iterable[str] = ()) -> str:
    for category, pat in PATTERNS:
        text = pat.sub(f"[REDACTED:{category}]", text)
    for value in denylist:
        if value:
            text = text.replace(value, "[REDACTED:user-marked]")
    return text


def _load_denylist(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f if line.strip()]


def _run_self_test() -> int:
    cases: list[tuple[str, str, list[str]]] = [
        ("AKIAABCDEFGHIJKLMNOP",                   "[REDACTED:aws_access_key]",      []),
        ("ASIA0123456789ABCDEF",                   "[REDACTED:aws_access_key]",      []),
        ("ghp_" + "a" * 36,                        "[REDACTED:github_token]",        []),
        ("ghs_" + "Z" * 36,                        "[REDACTED:github_token]",        []),
        ("sk-" + "x" * 40,                         "[REDACTED:openai_key]",          []),
        ("xoxb-123-abcDEF",                        "[REDACTED:slack_token]",         []),
        ("sk_live_" + "A" * 24,                    "[REDACTED:stripe_key]",          []),
        ("postgres://u:p@db:5432/x",               "[REDACTED:connection_string]",   []),
        ("mongodb://alice:secret@host/db",         "[REDACTED:connection_string]",   []),
        ("api_key: abcdef1234567890XYZ",           "[REDACTED:generic_secret]",      []),
        ("password=hunter2hunter2hunter",          "[REDACTED:generic_secret]",      []),
        (
            "-----BEGIN RSA PRIVATE KEY-----\nMIIEabc\n-----END RSA PRIVATE KEY-----",
            "[REDACTED:pem_private_key]",
            [],
        ),
        # Layer 3: owner-marked value
        ("my codename is falcon",                  "my codename is [REDACTED:user-marked]", ["falcon"]),
        # Negative: innocuous text must be untouched
        ("this is a token of appreciation",        "this is a token of appreciation", []),
        ("my secret identity",                     "my secret identity",             []),
        # Surrounding context preserved
        (
            "commit by akiaabc\nkey AKIAABCDEFGHIJKLMNOP ok",
            "commit by akiaabc\nkey [REDACTED:aws_access_key] ok",
            [],
        ),
    ]

    fails = 0
    for i, (inp, want, deny) in enumerate(cases, 1):
        got = redact(inp, deny)
        ok = got == want
        if not ok:
            fails += 1
            sys.stderr.write(
                f"FAIL #{i}\n  input:    {inp!r}\n  expected: {want!r}\n  got:      {got!r}\n"
            )
    total = len(cases)
    if fails:
        sys.stderr.write(f"\n{fails}/{total} self-test cases failed\n")
        return 1
    sys.stderr.write(f"self-test: {total}/{total} passed\n")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Redact known secret patterns and owner-marked values."
    )
    p.add_argument("infile", nargs="?", help="Input file (default: stdin)")
    p.add_argument("--denylist-file", help="File with one owner-marked value per line")
    p.add_argument("--self-test", action="store_true", help="Run built-in test cases and exit")
    args = p.parse_args()

    if args.self_test:
        return _run_self_test()

    if args.infile:
        with open(args.infile, encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    denylist = _load_denylist(args.denylist_file) if args.denylist_file else []
    sys.stdout.write(redact(text, denylist))
    return 0


if __name__ == "__main__":
    sys.exit(main())

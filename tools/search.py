#!/usr/bin/env python3
"""Frontmatter-aware search across the Ginarr vault.

Replaces ad-hoc grep with a scope- and type-aware lookup over wiki/ and logs/.
`wiki/` filters by frontmatter type/tag; `logs/` filters by file date.
"""

import argparse
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path


def parse_date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()


def parse_frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}
    fm: dict = {}
    for line in m.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            val = [s.strip() for s in val[1:-1].split(",") if s.strip()]
        fm[key] = val
    return fm


def search_wiki(vault_root: Path, query: str, type_filter: str | None,
                 tag_filter: str | None) -> list[dict]:
    wiki_dir = vault_root / "wiki"
    if not wiki_dir.is_dir():
        return []
    q_re = re.compile(re.escape(query), re.IGNORECASE)
    hits: list[dict] = []
    for p in sorted(wiki_dir.rglob("*.md")):
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        fm = parse_frontmatter(text)
        if type_filter and fm.get("type") != type_filter:
            continue
        if tag_filter:
            tags = fm.get("tags", [])
            if not isinstance(tags, list) or tag_filter not in tags:
                continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if q_re.search(line):
                hits.append({
                    "path": str(p.relative_to(vault_root)),
                    "line": lineno,
                    "text": line.strip(),
                })
    return hits


def search_logs(vault_root: Path, query: str, since: date | None) -> list[dict]:
    logs_dir = vault_root / "logs"
    if not logs_dir.is_dir():
        return []
    q_re = re.compile(re.escape(query), re.IGNORECASE)
    hits: list[dict] = []
    for p in sorted(logs_dir.rglob("*.jsonl")):
        if since:
            try:
                file_date = date.fromisoformat(p.stem)
            except ValueError:
                continue
            if file_date < since:
                continue
        try:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    try:
                        evt = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    content = evt.get("content", "")
                    if not isinstance(content, str) or not q_re.search(content):
                        continue
                    preview = content if len(content) <= 200 else content[:200] + "…"
                    hits.append({
                        "path": str(p.relative_to(vault_root)),
                        "ts": evt.get("ts", ""),
                        "role": evt.get("role", ""),
                        "content": preview,
                    })
        except OSError:
            continue
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Substring (case-insensitive).")
    parser.add_argument("--vault-root", default=os.environ.get("GINARR_VAULT_ROOT"))
    parser.add_argument("--scope", choices=["wiki", "logs", "both"], default="both")
    parser.add_argument("--since", type=parse_date,
                        help="ISO date; restricts log scan to files on/after this date.")
    parser.add_argument("--type", dest="type_filter",
                        help="Filter notes by frontmatter type (user | feedback | project | reference | decision).")
    parser.add_argument("--tag", dest="tag_filter",
                        help="Filter notes by frontmatter tag.")
    parser.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON.")
    args = parser.parse_args()

    if not args.vault_root:
        print("GINARR_VAULT_ROOT is not set and --vault-root was not provided.", file=sys.stderr)
        return 2
    vault_root = Path(args.vault_root).expanduser()

    result = {"wiki": [], "logs": []}
    if args.scope in ("wiki", "both"):
        result["wiki"] = search_wiki(vault_root, args.query, args.type_filter, args.tag_filter)
    if args.scope in ("logs", "both"):
        result["logs"] = search_logs(vault_root, args.query, args.since)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if result["wiki"]:
        print(f"wiki ({len(result['wiki'])} hits):")
        for h in result["wiki"]:
            print(f"  {h['path']}:{h['line']}: {h['text']}")
    if result["logs"]:
        if result["wiki"]:
            print()
        print(f"logs ({len(result['logs'])} hits):")
        for h in result["logs"]:
            print(f"  {h['path']} {h['ts']} [{h['role']}]: {h['content']}")
    if not result["wiki"] and not result["logs"]:
        print(f"No matches for {args.query!r} in {args.scope}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

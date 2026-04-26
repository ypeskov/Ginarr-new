#!/usr/bin/env python3
"""Move retired notes older than a cutoff into wiki/archive/.

A note is a candidate when its frontmatter has `status: retired` (or
`archived`) and `updated:` is older than --older-than. Default target is
the `project` type — retirement is most meaningful for ongoing initiatives
— but --type accepts any capture type.
"""

import argparse
import os
import re
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path


DURATION_RE = re.compile(r"^(\d+)(d|w|mo|y)$")

PLURAL_DIR = {"project": "projects", "decision": "decisions"}


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
        fm[key.strip()] = val.strip()
    return fm


def parse_duration(s: str) -> timedelta:
    m = DURATION_RE.match(s)
    if not m:
        raise argparse.ArgumentTypeError(
            f"Invalid duration {s!r}; expected e.g. 90d, 4w, 6mo, 1y."
        )
    n, unit = int(m.group(1)), m.group(2)
    if unit == "d":
        return timedelta(days=n)
    if unit == "w":
        return timedelta(weeks=n)
    if unit == "mo":
        return timedelta(days=n * 30)
    if unit == "y":
        return timedelta(days=n * 365)
    raise argparse.ArgumentTypeError(f"Unknown unit: {unit}")


def candidates(vault_root: Path, older_than: timedelta, type_name: str) -> list[tuple[Path, date]]:
    cutoff = date.today() - older_than
    subdir_name = PLURAL_DIR.get(type_name, type_name)
    subdir = vault_root / "wiki" / subdir_name
    if not subdir.is_dir():
        return []
    out: list[tuple[Path, date]] = []
    for p in subdir.rglob("*.md"):
        if "archive" in p.parts or p.name.startswith("_"):
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        fm = parse_frontmatter(text)
        if fm.get("status") not in ("retired", "archived"):
            continue
        try:
            updated = date.fromisoformat(fm.get("updated", ""))
        except ValueError:
            continue
        if updated <= cutoff:
            out.append((p, updated))
    return out


def move_to_archive(vault_root: Path, src: Path) -> Path:
    wiki_dir = vault_root / "wiki"
    dst = wiki_dir / "archive" / src.relative_to(wiki_dir)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return dst


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-root", default=os.environ.get("GINARR_VAULT_ROOT"))
    parser.add_argument("--older-than", type=parse_duration, required=True,
                        help="Duration literal: 90d | 4w | 6mo | 1y.")
    parser.add_argument("--type", dest="type_name", default="project",
                        choices=["user", "feedback", "project", "reference", "decision"],
                        help="Note type to scan (default: project).")
    parser.add_argument("--apply", action="store_true",
                        help="Actually move files (default: dry-run).")
    args = parser.parse_args()

    if not args.vault_root:
        print("GINARR_VAULT_ROOT is not set.", file=sys.stderr)
        return 2
    vault_root = Path(args.vault_root).expanduser()

    hits = candidates(vault_root, args.older_than, args.type_name)
    if not hits:
        print("No retired notes older than the cutoff.")
        return 0

    print(f"Found {len(hits)} candidate(s):")
    for p, updated in hits:
        print(f"  - {p.relative_to(vault_root)} (updated {updated})")

    if not args.apply:
        print("\nDry-run. Re-run with --apply to move these into wiki/archive/.")
        return 0

    print("\nMoving…")
    for p, _ in hits:
        dst = move_to_archive(vault_root, p)
        print(f"  {p.relative_to(vault_root)} -> {dst.relative_to(vault_root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

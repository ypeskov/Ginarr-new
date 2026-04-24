#!/usr/bin/env python3
"""Report likely-duplicate notes in the Ginarr vault.

Dry-run only. Prints candidate groups grouped by similarity of filename tokens
or frontmatter tags. Does not modify files. --apply is reserved for a later
iteration — merging is an agent-judgment task better routed through /review.

Wire through system cron (not the bot's own loop), per SPEC.v3 portability rule.
"""

import argparse
import os
import re
import sys
from pathlib import Path


def parse_frontmatter(text: str) -> dict:
    """Parse a leading `---`-delimited frontmatter block.

    Supports `key: value` and `key: [a, b]`. Unknown shapes are silently skipped
    — this is a best-effort reader, not a strict YAML parser.
    """
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


def tokenize(s: str) -> set:
    return {w for w in re.findall(r"[a-zа-я0-9]+", s.lower()) if len(w) >= 2}


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def find_notes(vault_root: Path):
    notes_dir = vault_root / "notes"
    if not notes_dir.is_dir():
        return
    for p in notes_dir.rglob("*.md"):
        if p.name.startswith("_"):
            continue
        if "archive" in p.parts:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        yield p, parse_frontmatter(text)


def group_duplicates(vault_root: Path, threshold: float) -> list[list[Path]]:
    notes = list(find_notes(vault_root))
    seen: set[Path] = set()
    groups: list[list[Path]] = []
    for i, (p1, fm1) in enumerate(notes):
        if p1 in seen:
            continue
        name1 = tokenize(p1.stem)
        tags1 = set(fm1.get("tags", [])) if isinstance(fm1.get("tags"), list) else set()
        type1 = fm1.get("type", "")
        group = [p1]
        for p2, fm2 in notes[i + 1:]:
            if p2 in seen:
                continue
            type2 = fm2.get("type", "")
            if type1 and type2 and type1 != type2:
                continue
            name2 = tokenize(p2.stem)
            tags2 = set(fm2.get("tags", [])) if isinstance(fm2.get("tags"), list) else set()
            name_hit = jaccard(name1, name2) >= threshold
            tag_hit = bool(tags1 and tags2) and jaccard(tags1, tags2) >= 0.5
            if name_hit or tag_hit:
                group.append(p2)
        if len(group) > 1:
            groups.append(group)
            for p in group:
                seen.add(p)
    return groups


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-root", default=os.environ.get("GINARR_VAULT_ROOT"),
                        help="Defaults to $GINARR_VAULT_ROOT.")
    parser.add_argument("--threshold", type=float, default=0.6,
                        help="Jaccard threshold for filename-token similarity (default: 0.6).")
    parser.add_argument("--apply", action="store_true",
                        help="Not implemented — merge proposals should be resolved via /review, not here.")
    args = parser.parse_args()

    if args.apply:
        print("--apply is not implemented; resolve merge candidates via /review.", file=sys.stderr)
        return 2
    if not args.vault_root:
        print("GINARR_VAULT_ROOT is not set and --vault-root was not provided.", file=sys.stderr)
        return 2

    vault_root = Path(args.vault_root).expanduser()
    if not (vault_root / "notes").is_dir():
        print(f"No notes/ directory under {vault_root}", file=sys.stderr)
        return 2

    groups = group_duplicates(vault_root, args.threshold)
    if not groups:
        print("No overlapping notes found.")
        return 0

    print(f"Found {len(groups)} candidate group(s):")
    for i, group in enumerate(groups, 1):
        print(f"\nGroup {i} ({len(group)} files):")
        for p in group:
            print(f"  - {p.relative_to(vault_root)}")
    print("\nReview manually; --apply is not yet implemented.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# archive.py

Move retired notes older than a cutoff into `notes/archive/`, preserving the subdirectory layout. Dry-run by default.

## Source

[`tools/archive.py`](../../tools/archive.py).

## Invocation

```
GINARR_VAULT_ROOT=… python3 tools/archive.py \
    --older-than 6mo \
    [--type project] \
    [--apply]
```

## Required argument

`--older-than <duration>` — `Nd` (days), `Nw` (weeks), `Nmo` (≈30-day months), `Ny` (365-day years). Examples: `90d`, `4w`, `6mo`, `1y`. Compared against frontmatter `updated:` (UTC date).

## What qualifies

Both must hold for a note to be a candidate:

1. Frontmatter `status:` is `retired` or `archived`.
2. Frontmatter `updated:` ≤ today − `--older-than`.

Notes under `notes/archive/` and `_`-prefixed files are skipped.

## `--type`

Defaults to `project`. Accepts any capture type (`user | feedback | project | reference | decision`). The directory mapped follows the capture convention — `project` → `notes/projects/`, `decision` → `notes/decisions/`, others map 1:1.

## Move semantics

Destination: `notes/archive/<original-relative-path>`. For example, `notes/projects/marathon_2026.md` → `notes/archive/projects/marathon_2026.md`. Parent directories are created as needed. The frontmatter is not rewritten.

## Scheduling

Run via system cron. `--apply` is destructive — prefer running dry-run first and committing to `--apply` interactively, at least initially.

## Limitations

- Does not rewrite the archived file's frontmatter (no `archived_at:` timestamp inserted). If provenance is needed later, git history on the vault (if any) or a follow-up hook can handle it.
- No undo built in; recover with `git mv` or manual move back out of `archive/`.

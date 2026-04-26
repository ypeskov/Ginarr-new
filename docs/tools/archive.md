# archive.py

Move retired notes older than a cutoff into `wiki/archive/`, preserving the subdirectory layout. Dry-run by default.

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

Notes under `wiki/archive/` and `_`-prefixed files are skipped.

## `--type`

Historical. The flag still exists and accepts the SPEC.v3 capture types (`user | feedback | project | reference | decision`), but those directories no longer exist in the active vault — they were collapsed into `wiki/entities/` on 2026-04-26 (auto-wiki roadmap step 3.4) and the originals moved to `wiki/archive/migration-2026-04-26/`. The flag is therefore only useful for trimming the archived migration tree, not the live vault.

A follow-up will rewrite this tool against the entity-page model (status-based archival of individual `wiki/entities/<slug>.md` pages). Tracked as a known gap, not yet on the roadmap.

## Move semantics

Destination: `wiki/archive/<original-relative-path>`. For example, `wiki/projects/marathon_2026.md` → `wiki/archive/projects/marathon_2026.md` (under the active layout this only applies to files already inside `wiki/archive/migration-2026-04-26/`). Parent directories are created as needed. The frontmatter is not rewritten.

## Scheduling

Run via system cron. `--apply` is destructive — prefer running dry-run first and committing to `--apply` interactively, at least initially.

## Limitations

- Does not rewrite the archived file's frontmatter (no `archived_at:` timestamp inserted). If provenance is needed later, git history on the vault (if any) or a follow-up hook can handle it.
- No undo built in; recover with `git mv` or manual move back out of `archive/`.

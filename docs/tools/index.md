# Maintenance tools

Standalone CLI scripts that maintain the vault: dedup reports, search, archival. No LLM-SDK dependencies, pure Python stdlib — they run from cron or by hand regardless of the agent runtime.

## Location

Scripts live in [`tools/`](../../tools/) at the repo root (version-controlled). SPEC.v3 originally placed them at `$GINARR_VAULT_ROOT/_tools/` for portability; keeping them under `tools/` in-repo preserves that portability (they are runtime-neutral — nothing in `.claude/` imports them) while gaining git tracking. If the operator wants them visible inside the vault, a symlink suffices:

```
ln -s /path/to/repo/tools "$GINARR_VAULT_ROOT/_tools"
```

The split (behavior in `~/Ginarr/`, data in `$GINARR_VAULT_ROOT`) is the active design — see [`../architecture.md`](../architecture.md) §"Data / behavior split". No further SPEC revisions are planned; CLAUDE.md treats `SPEC.v3.md` and earlier as historical artefacts.

## Scripts

- [`consolidate.md`](consolidate.md) — report likely-duplicate notes by filename-token / tag similarity. Dry-run only for now.
- [`search.md`](search.md) — frontmatter-aware grep across `wiki/` and `logs/` with scope / type / tag / since filters.
- [`archive.md`](archive.md) — move retired notes older than a cutoff into `wiki/archive/`.

## Invariants

- All three read `$GINARR_VAULT_ROOT` from the environment (or `--vault-root`).
- All three are safe-by-default (dry-run); destructive actions require `--apply`.
- Single-file, stdlib-only — no pip installs.
- Output is human-readable by default; pass `--json` where the script supports it for pipelines.

## Scheduling

Per CLAUDE.md §"Anti-patterns", do not put these inside the bot's event loop. Use a system cron or a systemd timer. Example crontab:

```
# Weekly dup report, mailed to $MAILTO
30 6 * * 1  GINARR_VAULT_ROOT=$HOME/obsidian-vaul/Auto-Wiki python3 /path/to/repo/tools/consolidate.py
```

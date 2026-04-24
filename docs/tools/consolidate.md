# consolidate.py

Report likely-duplicate notes in the vault. Dry-run only in this iteration — merging is deferred to an explicit owner review flow.

## Source

[`tools/consolidate.py`](../../tools/consolidate.py).

## Invocation

```
GINARR_VAULT_ROOT=… python3 tools/consolidate.py [--threshold 0.6]
```

Exits `0` on success (whether or not groups were found), `2` on config errors.

## What it does

1. Walks `$GINARR_VAULT_ROOT/notes/**/*.md`, skipping names starting with `_` (pending / proposal scratchpads) and anything under `archive/`.
2. Parses each note's frontmatter (best-effort — understands `key: value` and `key: [a, b]`).
3. Groups notes that share a `type` and are judged similar by either:
   - **filename-token Jaccard** ≥ `--threshold` (default `0.6`) — treats `dog_rex.md` and `rex_dog.md` as similar, but not `dog_rex.md` vs `marathon_plan.md`.
   - **tag Jaccard** ≥ 0.5 (when both files carry tags).
4. Prints groups with ≥2 members. Each file listed relative to `$GINARR_VAULT_ROOT`.

## Why dry-run only

Auto-merging loses information silently. The SPEC-aligned path is to surface candidates and let the owner resolve them through `/review` or by editing in Obsidian — `--apply` is reserved for a future iteration that writes proposals to a queue rather than mutating notes directly.

`--apply` currently exits `2` with a pointer to roadmap §4.1.

## Tuning the threshold

- `0.8` — only very close filename overlaps (strict).
- `0.6` (default) — catches common-word overlap like `dog_rex` / `rex_the_dog`.
- `0.4` — noisy; surfaces "projects with one common word".

## Scheduling

Add to system cron. Does not need the Ginarr bot running; reads the filesystem directly.

## Limitations

- Frontmatter parser does not handle nested YAML (block scalars, indented maps) — acceptable given capture's fixed frontmatter shape.
- No content-similarity metric. A future iteration could add a word-shingle Jaccard over bodies; out of scope now.
- `--apply` is a stub.

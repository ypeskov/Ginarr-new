# Architecture

Ginarr is a single-owner, always-on Telegram assistant. Claude Code is the agent runtime; a portable Auto-Wiki vault on the filesystem is the long-term memory.

## Processes

- **`ginarr` tmux session** — the live Claude Code process, launched by `.claude/scripts/ginarr-bot.sh`. Runs with `--continue` so the conversation survives restarts.
- **Telegram plugin** — loaded via `--channels plugin:telegram@claude-plugins-official`. Receives messages from the owner and hands them to Claude Code as prompts.
- **Watchdog** — `.claude/scripts/ginarr-watchdog.sh` is invoked every minute by cron. Verifies the tmux session, the bun plugin subprocess, and the Telegram API; restarts the session after 3 consecutive failures.

## Data / behavior split

The bot repo and the memory vault are **separate** directories with independent lifecycles.

| Path                              | Purpose                                                  | Lifecycle                                                  |
|-----------------------------------|----------------------------------------------------------|------------------------------------------------------------|
| `~/Ginarr/` (this repo)           | Behavior: scripts, hooks, skills, configuration.         | Replaceable. Can migrate to Junie or OpenCode by rewiring. |
| `~/obsidian-vaul/Auto-Wiki/`    | Data: logs, notes. Portable Markdown + JSONL.            | Must survive years and runtime migrations.                 |

`GINARR_VAULT_ROOT` in `.claude/.env` (gitignored) points the bot at its vault. `ginarr-bot.sh` sources this file before exec'ing Claude, so the variable is inherited by all hook processes.

Rationale for the split: data is format-portable, behavior is runtime-specific; keeping them apart avoids accidentally coupling a multi-year memory store to a single agent runtime. The vendor-neutrality argument was first laid out in `SPEC.v3.md` §"Vendor neutrality" (kept as a historical artefact, not edited going forward).

## Vault layout

```
$GINARR_VAULT_ROOT/
├── logs/
│   ├── YYYY/MM/YYYY-MM-DD.jsonl    ← raw event log (one line per turn)
│   └── summaries/YYYY/MM/<date>.md ← daily roll-ups (built nightly)
└── wiki/
    ├── entities/
    │   ├── _owner.md                ← consolidated owner-meta page (root)
    │   ├── _about.md / index.md     ← folder metadata
    │   ├── dating/<slug>.md         ← per-topic entity pages
    │   ├── work/<slug>.md
    │   ├── tech/<slug>.md
    │   ├── health/<slug>.md
    │   ├── finance/<slug>.md
    │   ├── immigration/<slug>.md
    │   ├── owner/<slug>.md
    │   └── family/<slug>.md
    ├── topics/
    │   └── <topic>.md               ← per-topic manifests for /load-topic
    ├── _pending.md                  ← low-confidence captures awaiting /review
    ├── _health/<date>.md            ← lint-wiki audit reports
    └── archive/migration-2026-04-26/ ← pre-entity-model originals (read-only)
```

Each entity page carries a `topics: [<primary>, <secondary>, ...]` frontmatter field. The first element dictates the folder; secondary entries enable cross-cutting membership (e.g. `boo.md` lives in `dating/` but is tagged `[dating, tech]`). The flat layout in use until 2026-05-02 was reorganised into topic folders the same day; entity pages, the `_owner.md` root page, and `_about.md` / `index.md` files are the only contents at the entities root.

Idea inspiration: Karpathy's [LLM-managed wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). The `logs/` slot is "raw chat", `logs/summaries/` is the daily index, `wiki/entities/` is the curated knowledge layer.

## Write-path A: log events (hook-driven)

Every conversational turn flows through Claude Code hooks into the vault as one JSONL event.

1. Owner sends a Telegram message → plugin delivers it as a prompt to the Claude session.
2. Claude Code fires `UserPromptSubmit` → `log_event.py --event user` writes `{role:"user", content:"…"}` to `$GINARR_VAULT_ROOT/logs/YYYY/MM/YYYY-MM-DD.jsonl`.
3. Assistant composes reply (possibly using tools).
4. Claude Code fires `Stop` at end of turn → `log_event.py --event assistant` writes the turn's outgoing assistant text.
5. Session lifecycle events (`SessionStart`, `SessionEnd`) produce `{role:"system", content:"bot_started"|"bot_stopped"}`.

All content is passed through `redactor.py` (Layer 2 regex + Layer 3 owner denylist) before persistence.

See [hooks.md](hooks.md) for the extraction details and [scripts/log_event.md](scripts/log_event.md) for the implementation.

## Write-path B: entity pages (skill-driven)

The hook-driven log is raw material. The curated layer — `wiki/entities/` — is built by two skills that share the same write target:

- [`capture`](skills/capture.md) — owner-action-driven. Triages an in-conversation statement and either writes directly to `wiki/entities/<topic>/<slug>.md` (or `_owner.md` for owner-meta), or queues it in `wiki/_pending.md` for `/review`. Fires whenever the owner states a fact, preference, or decision. Resolves the primary topic when creating a new entity (asks the owner if ambiguous).
- [`ingest-and-weave`](skills/ingest-and-weave.md) — cron-driven. Reads each new daily summary (built by `summarize-day`) and weaves the mentioned entities into `wiki/entities/<topic>/<slug>.md` pages. Never writes to `_owner.md` (that page is owner-action territory). Idempotent: facts already on a page are not duplicated; contradictions get a `## Conflicts` marker. Resolves primary topic via co-mention tally + type defaults; logs uncertainty for owner review when no signal dominates.

Both skills append, never overwrite. Conflicts surface as a marker plus a question to the owner; resolved through `/review` or by direct edit in Obsidian.

The previous SPEC.v3 layout used per-type folders (`wiki/{decisions,feedback,projects,reference,user}/`). On 2026-04-26 (auto-wiki roadmap step 3.4) those collapsed into the entity-page model and the originals moved to `wiki/archive/migration-2026-04-26/`. On 2026-05-02 the flat entity layout was reorganised into topic folders (`dating/`, `work/`, `tech/`, `health/`, `finance/`, `immigration/`, `owner/`, `family/`) with a mandatory `topics:` frontmatter field for cross-cutting membership.

## Read-path index

The raw JSONL is authoritative but expensive to grep. A daily roll-up and the entity pages sit next to it as homemade indexes.

- **`wiki/entities/`** — primary read source. The [`recall`](skills/recall.md) skill greps it first; if an entity page covers the question, the answer is quoted from there.
- **`logs/summaries/YYYY/MM/<date>.md`** — built by [`summarize-day`](skills/summarize-day.md) at 00:15 UTC each night. One file per UTC date, ~1KB, dry bullet list of topics, people, decisions, paths.
- **`logs/YYYY/MM/<date>.jsonl`** — raw event log, opened only on the days the summary flagged.
- **`wiki/_pending.md`** — unconfirmed candidates, consulted on demand.
- **Today's UTC date** has no summary (still being written). `recall` falls through to today's JSONL directly.

The `summaries/` subtree is parallel to the per-month log folders, never nested inside them, so a `grep -r` over only `summaries/` ignores the heavy raw logs.

## Daily cron chain

| When (UTC)      | Script                                                                   | Skill / purpose                                                            |
|-----------------|--------------------------------------------------------------------------|----------------------------------------------------------------------------|
| `* * * * *`     | [`ginarr-watchdog.sh`](scripts/ginarr-watchdog.md)                       | Keep the bot tmux session and Telegram plugin alive.                       |
| `15 0 * * *`    | [`summarize-day.sh`](scripts/summarize-day.md)                           | Roll up yesterday's `logs/<date>.jsonl` into `logs/summaries/`.            |
| `25 0 * * *`    | [`ingest-and-weave.sh`](scripts/ingest-and-weave.md)                     | Weave entities from the new daily summary into `wiki/entities/`. Chained ten minutes after `summarize-day` to give it time to finish. |
| `0 9 * * 0`     | [`lint-wiki-reminder.sh`](scripts/lint-wiki-reminder.md)                 | Weekly Telegram nudge to run `/lint-wiki` manually. Does NOT auto-run the lint. |

The chain is intentionally sequential (`summarize-day` → `ingest-and-weave`) but uncoupled (separate cron lines, not a single wrapper) so a failure in one does not block the other.

## Topic system (working memory)

A separate layer on top of the entity model that solves "load this topic's full state into the current session" without coupling to runtime-specific session mechanisms.

- **Manifests** at `wiki/topics/<name>.md` curate the entity pages and main-vault paths relevant to each topic, plus topic-specific notes for the assistant.
- [`load-topic`](skills/load-topic.md) — reads a manifest, walks `wiki/entities/<name>/`, finds cross-tagged entities (`topics:` includes `<name>`), reads listed main-vault paths, prints a structured ready-state. Auto-discovery fallback when no manifest exists. Read-only.
- [`edit-topic`](skills/edit-topic.md) — list / show / create / add / remove / rename operations on `wiki/topics/<name>.md`. Validates referenced paths.

Per-topic context loading lives at the **skill** layer, not at the runtime-session layer — vendor-neutral by design (works the same on Claude Code, Junie, OpenCode + oh-my-opencode). New session + `/load-topic <name>` is the canonical pattern; no UUID maps, no `claude --resume` wrappers.

## Auxiliary skills

Not part of the write/read path itself, but maintain navigability:

- [`lint-indexes`](skills/lint-indexes.md) — ensures every directory in the vault (and optionally the main Obsidian vault) has an `index.md` listing its contents. Read-only by default; `--apply` writes.
- [`lint-wiki`](skills/lint-wiki.md) — health check on `wiki/entities/`: contradictions, orphans, missing cross-references, `topics:` field validity, frontmatter consistency. Writes a report to `wiki/_health/<date>.md`. Manual; the cron above only nudges.
- [`cross-link`](skills/cross-link.md) — proposes `[[wikilink]]` insertions between the main Obsidian vault and `wiki/entities/`. Manual, dry-run by default; `--apply` writes only on owner confirmation.

## What is NOT here yet

- **Consolidation tool** — `tools/consolidate.py` exists as a dry-run dup-detector, but a `consolidate` skill that wraps it (review queue → apply) is not yet built.
- **Attachment materialisation for non-image Telegram content** — `voice`, `audio`, `document` and similar kinds produce `[kind: unresolved:<file_id>]` markers because the agent, not the hook, downloads them. A backfill mechanism that promotes `unresolved:<id>` to a real path once the download lands is not yet wired.

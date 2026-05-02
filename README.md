# Ginarr — Auto-Wiki

A vendor-neutral long-term memory system for a single-user, always-on LLM personal assistant. The reference deployment is a Telegram bot running as a long-lived process on a server, with one owner as the only user. Memory survives process restarts, runtime migrations, and years of use — stored as plain Markdown and JSONL on the filesystem, readable by any agent runtime.

No embeddings. No vector DB. No vendor-specific storage. `grep` is the search mechanism.

## Project shape

The bot's behaviour and the memory it produces live in **separate** directories with independent lifecycles. The split is deliberate: data is format-portable and long-lived, behaviour is runtime-specific and replaceable.

| Path                         | Purpose                                                  | Lifecycle                                                  |
|------------------------------|----------------------------------------------------------|------------------------------------------------------------|
| `~/Ginarr/` (this repo)      | Behaviour: scripts, hooks, skills, configuration.        | Replaceable. Migrate to Junie or OpenCode by rewiring.    |
| `~/obsidian-vaul/Auto-Wiki/` | Data: logs, notes. Portable Markdown + JSONL.            | Must survive years and runtime migrations.                |

`GINARR_VAULT_ROOT` in `.claude/.env` (gitignored) points the bot at its vault. See [`docs/configuration.md`](docs/configuration.md) for the full bootstrap.

## Vault layout

```
$GINARR_VAULT_ROOT/
├── logs/
│   ├── YYYY/MM/YYYY-MM-DD.jsonl    ← raw event log (one line per turn)
│   └── summaries/YYYY/MM/<date>.md ← daily roll-ups (built nightly)
└── wiki/
    ├── entities/
    │   ├── _owner.md               ← consolidated owner-meta page
    │   └── <topic>/<slug>.md       ← one page per person/project/place/tech/org/event,
    │                                 grouped under eight topic folders (dating, work,
    │                                 tech, health, finance, immigration, owner, family)
    ├── topics/<name>.md            ← per-topic manifests for /load-topic and /edit-topic
    ├── _pending.md                 ← low-confidence captures awaiting /review
    ├── _health/<date>.md           ← lint-wiki audit reports
    └── archive/migration-2026-04-26/ ← pre-entity-model originals (read-only)
```

A `topics:` frontmatter field on every entity (`topics: [primary, ...secondary]`) lets a single page surface under multiple topics without duplication; the first element dictates the folder.

Inspired by Karpathy's [LLM-managed wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). `logs/` is raw chat, `logs/summaries/` is the daily index, `wiki/entities/` is the curated knowledge layer.

## How memory flows

**Write path A — log events** (hook-driven). Every conversational turn is captured by `log_event.py` from Claude Code's `UserPromptSubmit` and `Stop` hooks and appended to `logs/<date>.jsonl`. Content is scrubbed by `redactor.py` before persistence (regex layer + owner-marked denylist).

**Write path B — entity pages** (skill-driven). The raw log is the firehose; the curated layer is `wiki/entities/`, built by two skills sharing the same target:

- `capture` — owner-action-driven. Triages an in-conversation statement and either writes directly to an entity page (`wiki/entities/<topic>/<slug>.md`), or queues it in `_pending.md` for `/review`.
- `ingest-and-weave` — cron-driven. Reads each new daily summary and weaves the mentioned entities into the same per-topic entity pages.

Both append rather than overwrite; contradictions surface as a `## Conflicts` marker rather than silently mutating.

**Read path.** The `recall` skill answers retrospective questions by greping in this order: `wiki/entities/` (curated, recursive across topic folders), `logs/summaries/` (daily index), then a specific day's raw `logs/<date>.jsonl` only on the days the summaries flag. For topic-scoped sessions, `/load-topic <name>` reads a manifest plus the topic folder up-front, so the rest of the conversation runs with that topic's full state in context.

## Daily cron chain

| When (UTC)     | Script                            | Purpose                                                                |
|----------------|-----------------------------------|------------------------------------------------------------------------|
| `* * * * *`    | `ginarr-watchdog.sh`              | Keep the bot tmux session and Telegram plugin alive.                  |
| `15 0 * * *`   | `summarize-day.sh`                | Roll up yesterday's `logs/<date>.jsonl` into `logs/summaries/`.       |
| `25 0 * * *`   | `ingest-and-weave.sh`             | Weave entities from the new summary into `wiki/entities/`.            |
| `0 */6 * * *`  | `lint-indexes.sh`                 | Sync every folder's `index.md` in the manual Obsidian vault.          |
| `0 9 * * 0`    | `lint-wiki-reminder.sh`           | Weekly Telegram nudge to run `/lint-wiki` manually.                   |

The chain is sequential by design (`summarize-day` → `ingest-and-weave`) but uncoupled (separate cron lines) so a failure in one does not block the other.

## Skills

Skills sit on top of the vault, in three buckets:

- **Memory layer** — `capture`, `recall`, `summarize-day`, `ingest-and-weave`, `lint-wiki`, `lint-indexes`, `cross-link`, `review-pending`, `load-topic`, `edit-topic`.
- **Repo workflow** — `save-to-repo` (commit / push), `create-skill` (scaffold), `obsidian-structure` (vault routing rules).
- **Daily drivers** — `/email-digest`, `/news-digest`, `/weather`, `/calendar-digest`, `/obsidian`.

Plus three slash commands wired through `.claude/commands/`: `/nolog` (pause the write log), `/redact` (extend the denylist), `/review` (walk `_pending.md`). Each skill lives under `.claude/skills/<name>/SKILL.md` — that's the authoritative source.

See [`docs/skills/index.md`](docs/skills/index.md) for the full list with one-line descriptions.

## Runtime support

- **Reference runtime:** Claude Code.
- **Supported migration targets** (same skill / agent format): Junie, OpenCode with the `oh-my-opencode` plugin.
- **Out of scope:** Cursor (different skill model), multi-user / group-chat extensions.

## Repository layout

```
~/Ginarr/
├── .claude/
│   ├── scripts/      ← cron wrappers, hooks (log_event.py, redactor.py, …)
│   ├── skills/       ← Agent Skills, one folder per skill
│   ├── commands/     ← slash-command templates (/nolog, /redact, /review)
│   └── settings.json ← Claude Code hook wiring
├── tools/            ← standalone CLIs (search, archive, consolidate)
├── docs/             ← operator documentation (start here)
├── CLAUDE.md         ← stable project conventions and invariants
├── SPEC.md / SPEC.v2.md / SPEC.v3.md ← historical artefacts (do not edit)
└── README.md
```

## Documentation

Operator-level docs live under [`docs/`](docs/index.md) — co-edited with the code they describe. Every directory there carries an `index.md` listing its contents.

- [`docs/architecture.md`](docs/architecture.md) — the big picture: bot process, vault layout, hook-driven write path.
- [`docs/configuration.md`](docs/configuration.md) — environment variables, `.env` locations, bootstrap recipe.
- [`docs/hooks.md`](docs/hooks.md) — Claude Code hooks wired in `settings.json`.
- [`docs/scripts/`](docs/scripts/index.md) — one file per `.claude/scripts/*` utility.
- [`docs/skills/`](docs/skills/index.md) — installed Agent Skills, with pointers to authoritative `SKILL.md`.
- [`docs/tools/`](docs/tools/index.md) — standalone maintenance CLIs.
- [`docs/roadmap/`](docs/roadmap/index.md) — active and closed implementation plans (in Russian, with checkboxes).

## Anti-patterns

The spec rejects, by design:

- RAG / embeddings / vector indexes — `grep` is the search mechanism.
- ML-based PII detection — regex layers only.
- Retroactive rescan of historical logs for secrets — creates a false sense of safety.
- Versioning `logs/` in git — manual redactions leak through history.
- An internal bot scheduler for consolidation — breaks portability. Use system cron / systemd timers.

If a contribution proposes one of these, the answer is no.

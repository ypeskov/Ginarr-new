# Implementation roadmap

Sequenced plan for bringing Ginarr to feature-parity with SPEC.v3. Phases are ordered by dependency: earlier phases unblock later ones.

This file is the persistent plan across sessions. When a phase lands, strike it through and link the PR/commit so future sessions can see what remains.

See also:
- [`TODO.md`](../TODO.md) — deferred features not yet scheduled.
- [`architecture.md`](architecture.md) §"What is NOT here yet" — current gaps at a glance.

## Baseline (already built)

- Write-path via hooks: `log_event.py` wired to `UserPromptSubmit` / `Stop` / `SessionStart` / `SessionEnd`, writing `logs/YYYY/MM/YYYY-MM-DD.jsonl`.
- `redactor.py` — Layer 2 (regex) + Layer 3 (denylist file). Layer 3 is **not yet wired** into the hook invocation.
- `create-skill` skill (scaffolding helper copied from OpenClaw).
- Telegram attachments currently land in the log as raw `<channel …>` tags — not SPEC-compliant.

## Phase 1 — Safety and log fidelity

### 1.1 Layer 1 — PreToolUse denylist

- New hook script `pre_tool_denylist.py`, registered in `settings.json` under `PreToolUse` (matcher: `Read|Bash|Edit|Write`).
- Denylist from SPEC §"Secrets and PII": `.env*`, `*.pem`, `*.key`, `id_rsa*`, `credentials*`, `~/.ssh/**`, `~/.aws/**`, `~/.config/gcloud/**`, `~/.kube/config`.
- On match: deny the tool call with `[REDACTED: path in denylist]` in `permissionDecisionReason`.
- Docs: update `docs/hooks.md`, add `docs/scripts/pre_tool_denylist.md`.

### 1.2 Attachment markers

- In `log_event.py` for `user` events: parse `<channel>` tags, find `image_path` / `attachment_file_id`, copy the file to `$VAULT_ROOT/logs/YYYY/MM/attachments/YYYY-MM-DD_<sha8>.<ext>`, replace the tag in content with `[image: attachments/…]` / `[file: …]` / `[audio: …]`.
- Docs: update `docs/hooks.md` and `docs/scripts/log_event.md`.

## Phase 2 — Write-path runtime controls

### 2.1 `/nolog` — Layer 4

- Slash command in `.claude/commands/nolog.md`, accepts `on | off`.
- State stored in `.claude/channels/.nolog` (flag file, cleared on `bot_started`).
- `log_event.py` checks the flag on entry. When set: skip writes for `user` / `assistant`; on state transitions, emit `system:log_paused` / `log_resumed`.
- Docs: `docs/skills/nolog.md`.

### 2.2 `/redact` — Layer 3 wiring

- Slash command in `.claude/commands/redact.md`: `/redact <value>` appends `value` to `.claude/channels/.redact-list`.
- `log_event.py` passes that file's path into `redactor.py` when calling `redact()`.
- File is cleared on `bot_started` (handled inside `log_event.py --event session-start`).
- Docs: `docs/skills/redact.md`.

## Phase 3 — Memory skills (capture / recall / review)

### 3.1 `capture` skill

- `.claude/skills/capture/SKILL.md` encoding SPEC §"Capture rules": high / medium / low confidence, always-ask-immediately triggers, never-save list.
- Agent deduplicates via grep over `$VAULT_ROOT/notes/`, writes or updates `notes/<type>/<snake_case>.md` with YAML frontmatter.
- Low-confidence candidates go to `notes/_pending.md`.
- Docs: `docs/skills/capture.md`.

### 3.2 `recall` skill

- `.claude/skills/recall/SKILL.md`: before answering retrospective questions ("what did I say / decide / …"), grep `notes/` first, then `logs/YYYY/` with an explicit date scope.
- Helper for local→UTC conversion for questions like "yesterday around 2pm".
- Docs: `docs/skills/recall.md`.

### 3.3 `/review` skill

- Slash command + skill: walks `notes/_pending.md` one candidate at a time — confirm / drop / edit.
- Telegram MVP: plain text prompt "yes / no / edit". Inline keyboard later.
- Threshold-notification (≥5 candidates) is a follow-up substep.
- Docs: `docs/skills/review.md`.

## Phase 4 — Maintenance tools (`_tools/`)

Live under `$VAULT_ROOT/_tools/` (portable, not in `.claude/`), no LLM-SDK dependencies.

### 4.1 `consolidate.py`

- `--dry-run` / `--apply`; finds duplicates by topic / tags, proposes merges.
- First run is dry-run only. Scheduling via system cron.

### 4.2 `search.py`

- Grep wrapper with frontmatter awareness: `--scope notes|logs --since <date>`.

### 4.3 `archive.py`

- `--older-than <duration>` moves retired projects into `notes/archive/`.

## Deferred

- Multi-vault support — see [`TODO.md`](../TODO.md).
- Threshold notification for `/review` (after the base review flow lands).
- Migration validation on Junie / OpenCode+oh-my-opencode.

## Invariants for every phase

- One commit bundles: code + the matching `docs/<topic>.md` + its parent `docs/*/index.md` update.
- Everything committed to the repo is in English (CLAUDE.md Ground rules).
- Skill / command filenames are `snake_case`. Role enum stays `user | assistant | system`. UTC everywhere. Writes are append-only.

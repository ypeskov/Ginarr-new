---
description: Walk wiki/_pending.md candidates one by one — save, drop, skip, or edit.
argument-hint: (empty) | save | drop | skip | edit
allowed-tools: Read, Write, Edit, Bash(grep:*), Bash(ls:*), Bash(mkdir:*), Bash(test:*), mcp__plugin_telegram_telegram__react, mcp__plugin_telegram_telegram__reply
---

Trigger for the `review-pending` skill (SPEC.v3 §"Review flow").

Action: `$ARGUMENTS` (case-insensitive, accepts Russian or English).

- **empty** → Read `$GINARR_VAULT_ROOT/wiki/_pending.md`, present the top candidate (body + proposed path), and prompt with: `ответь /review save | /review drop | /review skip | /review edit`. If the queue is empty, reply one line: `В очереди ничего нет.` (Russian) or `Queue is empty.` (English) — match the owner's last message language.
- **`save` / `сохрани` / `да`** → Promote the top candidate to a real note per the skill's promote-to-note flow, then show the next.
- **`drop` / `удали` / `нет`** → Remove the top block, show the next.
- **`skip` / `пропусти` / `потом`** → Move the top block to the end of the queue, show the next.
- **`edit` / `правь`** → Enter the edit sub-flow per the skill.

Parsing, dedup, frontmatter shape, and Telegram feedback details: see [`.claude/skills/review-pending/SKILL.md`](../skills/review-pending/SKILL.md).

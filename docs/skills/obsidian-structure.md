# `obsidian-structure` — vault taxonomy and routing

Companion to [`obsidian`](obsidian.md). Encodes the folder taxonomy and "what goes where" routing rules for the vault at `~/obsidian-vaul/`. The `obsidian` skill is expected to consult this before creating or searching notes.

## Source

- Skill: [`.claude/skills/obsidian-structure/SKILL.md`](../../.claude/skills/obsidian-structure/SKILL.md) — authoritative taxonomy.
- Origin: copied from `~/OpenClaw/.claude/skills/obsidian-structure/` (2026-04-24).

## Structure at a glance

16 top-level folders covering work (`RingCentral`), life in Bulgaria (`BG`, `BG/Авто`, `BG/Здоровье`), technical notes (`Dev Notes`), personal (`General`), investments (`Investments`), personal projects (`Krokobot`, `Orgfin.run`), creative (`Poems`), career (`Resume`), family (`Slava`), immigration (`US Green Card`), cooking (`Еда`), analytical reports (`Analysis/YYYY-MM-DD/`), and a landing page (`_Dashboard`).

Attachments live inside `_attachments/` sub-folders; analytical reports are dated.

## Routing rules (short form)

Each rule maps a topic cluster to a target folder. See SKILL.md for the full 15-item list. Summary of the high-traffic ones:

| Topic | Target |
|---|---|
| Work, 1:1s, RingCentral projects | `RingCentral` |
| Health — doctors, meds, tests | `BG/Здоровье` |
| Car — service, fines, customs | `BG/Авто` |
| Investments, ETFs, planned purchases | `Investments` |
| Tech cheatsheets (CLI, DevOps) | `Dev Notes` |
| Catch-all personal | `General` |

## Why this is a separate skill

Split out to keep the active `obsidian` skill short; this one loads only when the routing decision needs justification or when the owner asks "where would this go?"

## Known gaps

- **Divergence with `obsidian` skill**: the standalone `obsidian` SKILL.md lists 12 folders and omits `Krokobot`, `Еда`, and `Analysis`. `obsidian-structure` is the newer, more accurate source. A follow-up will collapse the two into a single source of truth.

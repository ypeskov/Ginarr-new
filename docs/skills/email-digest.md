# `/email-digest` — IMAP inbox summary

Fetches unread emails from three IMAP mailboxes, categorises them by priority, and renders a Russian-language summary to Telegram or terminal.

## Source

- Skill: [`.claude/skills/email-digest/SKILL.md`](../../.claude/skills/email-digest/SKILL.md) — authoritative behaviour.
- Fetcher: `.claude/skills/email-digest/scripts/fetch_emails.py` — pure IMAP over `imaplib`, no SDK dependency.
- Origin: copied from `~/OpenClaw/.claude/skills/email-digest/` (2026-04-24). No Ginarr-specific modifications yet.

## Dependencies

- `python3` with `imaplib` (stdlib).
- `pass` (password manager) — IMAP credentials read via `pass show <entry>`. Entry names are inside the fetch script.
- Telegram MCP plugin, if delivering to chat.

## Usage

- `/email-digest` — fetch unread and send digest to the current channel (Telegram) or stdout (terminal).
- Arguments beyond the default are documented in SKILL.md.

## Integration notes

- **Credentials:** the skill expects a working `pass` store. Ginarr does not provision it — set it up out-of-band before first run.
- **Mailbox list is hard-coded** in the fetch script. Adjusting it is a script edit, not a skill arg.
- No interaction with Ginarr's memory layer — this is a read-only convenience skill.

## Follow-ups

- When fetch targets change (new mailbox, dropped one), update the script and note the change in a commit message. No parallel YAML config yet.

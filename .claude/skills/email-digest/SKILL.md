---
name: email-digest
description: >
  Fetch unread emails from 3 IMAP mailboxes, categorize by priority, and send
  a formatted summary in Russian to Telegram or terminal. Use when the user
  asks about email, unread messages, inbox, mail digest, or "check my email."
compatibility: Requires python3, pass (password manager)
allowed-tools: Bash(python3 *) Bash(pass show *) mcp__plugin_telegram_telegram__reply
metadata:
  author: openclaw
  version: "2.0"
---

# /email-digest — Email Digest

Fetches unread emails from multiple IMAP mailboxes, categorizes by priority, and delivers a summary.

## Arguments

- No arguments: fetch only unread (UNSEEN) emails
- Numeric argument: fetch all emails from the last N hours
- Example: `/email-digest 12` — last 12 hours, `/email-digest` — unread only

## Instructions

### 1. Get passwords from pass

```bash
pass show email/yura@peskov.in.ua
pass show email/yuriy.peskov@ukr.net
pass show email/yuriy.peskov@gmail.com
```

### 2. Run the fetch script

```bash
python3 scripts/fetch_emails.py --passwords "PASS1" "PASS2" "PASS3" --mode unread
```

For hours mode: `python3 scripts/fetch_emails.py --passwords "PASS1" "PASS2" "PASS3" --mode hours --hours 12`

Run `python3 scripts/fetch_emails.py --help` for full usage.

The script outputs a JSON array to stdout with email objects: `{account, from, subject, date, body}`.

### 3. Categorize emails

Analyze the JSON and categorize each email:

- **🔴 Важное** — personal emails, urgent requests, deadlines, financial, security alerts
- **🟡 Средний приоритет** — work notifications, service updates, thread replies
- **🟢 Низкий приоритет** — newsletters, marketing, social media, automated reports

### 4. Format the summary

```
📬 Непрочитанная почта

🔴 Важное:
— [sender] → [account]: [subject]
  [1-2 sentence summary in Russian]

🟡 Средний приоритет:
— [sender] → [account]: [subject]
  [summary]

🟢 Низкий приоритет:
— [sender] → [account]: [subject]
  [summary]

📊 Итого: X писем (Y важных, Z средних, W низких)
```

Omit empty categories. If no emails at all, send: "📬 Непрочитанных писем нет!"

### 5. Deliver

- If triggered from Telegram, send via `mcp__plugin_telegram_telegram__reply` to the appropriate `chat_id`.
- If running in terminal, print the result.

### 6. Error handling

If a mailbox fails, include the error in output but continue with others.

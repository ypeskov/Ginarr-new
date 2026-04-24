#!/usr/bin/env python3
"""Fetch emails from multiple IMAP mailboxes and output as JSON.

Usage:
  python3 scripts/fetch_emails.py --passwords PASS1 PASS2 PASS3 [--mode unread|hours] [--hours N]

Modes:
  unread  — only UNSEEN emails (default)
  hours   — all emails from the last N hours

Output: JSON array of email objects to stdout.
  Each object: {account, from, subject, date, body} or {account, error}.
Exit codes: 0 = success, 1 = all mailboxes failed, 2 = invalid arguments.
"""

import imaplib
import email
from email.header import decode_header
from datetime import datetime, timezone, timedelta
import json
import sys
import argparse
import re

ACCOUNTS = [
    {"email": "yura@peskov.in.ua", "server": "box.peskov.in.ua"},
    {"email": "yuriy.peskov@ukr.net", "server": "imap.ukr.net"},
    {"email": "yuriy.peskov@gmail.com", "server": "imap.gmail.com"},
]


def decode_str(s):
    if s is None:
        return ""
    parts = decode_header(s)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def get_body(msg, max_len=500):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
                    break
            elif ct == "text/html" and not body:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            body = payload.decode(charset, errors="replace")
    body = re.sub(r"<[^>]+>", " ", body)
    body = re.sub(r"\s+", " ", body).strip()
    return body[:max_len]


def fetch_mailbox(acc, password, mode, hours):
    results = []
    try:
        m = imaplib.IMAP4_SSL(acc["server"], 993)
        m.login(acc["email"], password)
        m.select("INBOX", readonly=True)
        if mode == "unread":
            status, data = m.search(None, "UNSEEN")
        else:
            since = datetime.now(timezone.utc) - timedelta(hours=hours)
            since_imap = since.strftime("%d-%b-%Y")
            status, data = m.search(None, f"(SINCE {since_imap})")
        if status == "OK" and data[0]:
            ids = data[0].split()
            for mid in ids[-50:]:
                status2, msg_data = m.fetch(mid, "(BODY.PEEK[])")
                if status2 == "OK":
                    msg = email.message_from_bytes(msg_data[0][1])
                    results.append({
                        "account": acc["email"],
                        "from": decode_str(msg.get("From", "")),
                        "subject": decode_str(msg.get("Subject", "")),
                        "date": msg.get("Date", ""),
                        "body": get_body(msg),
                    })
        m.logout()
    except Exception as e:
        results.append({"account": acc["email"], "error": str(e)})
    return results


def main():
    parser = argparse.ArgumentParser(description="Fetch emails from IMAP mailboxes")
    parser.add_argument("--passwords", nargs=3, required=True,
                        help="Passwords for the 3 mailboxes in order")
    parser.add_argument("--mode", choices=["unread", "hours"], default="unread",
                        help="Fetch mode (default: unread)")
    parser.add_argument("--hours", type=int, default=24,
                        help="Hours to look back when mode=hours (default: 24)")
    args = parser.parse_args()

    all_emails = []
    errors = 0
    for i, acc in enumerate(ACCOUNTS):
        result = fetch_mailbox(acc, args.passwords[i], args.mode, args.hours)
        if result and "error" in result[0]:
            errors += 1
        all_emails.extend(result)

    print(json.dumps(all_emails, ensure_ascii=False, indent=2))
    sys.exit(1 if errors == len(ACCOUNTS) else 0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Write-path hook for Ginarr chat-memory.

Reads Claude Code hook JSON on stdin, appends one JSONL event to
$GINARR_VAULT_ROOT/logs/YYYY/MM/YYYY-MM-DD.jsonl in UTC.

Usage:
    log_event.py --event {user,assistant,session-start,session-end}

On any internal failure emits a `system:{content:"hook_error"}` event
with details in `meta`. Always exits 0 so the runtime is never blocked
by a write-path problem.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from redactor import redact  # noqa: E402


def now_utc_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def log_path(vault_root: Path, dt: datetime) -> Path:
    p = vault_root / "logs" / f"{dt.year:04d}" / f"{dt.month:02d}" / f"{dt.strftime('%Y-%m-%d')}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def append_event(vault_root: Path, event: dict) -> None:
    dt = datetime.now(timezone.utc)
    path = log_path(vault_root, dt)
    line = json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
    # O_APPEND — writes <4 KB are atomic on POSIX (SPEC §"Parallel writers").
    with open(path, "ab") as f:
        f.write(line.encode("utf-8"))


def read_hook_input() -> dict:
    try:
        data = sys.stdin.read()
    except Exception:
        return {}
    if not data.strip():
        return {}
    try:
        return json.loads(data)
    except Exception:
        return {}


def _is_real_user_prompt(record: dict) -> bool:
    """True iff a `type:"user"` record is an actual human prompt rather than
    a tool_result carried back to the assistant."""
    content = (record.get("message") or {}).get("content")
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                return True
    return False


def extract_last_assistant_text(transcript_path: str) -> str:
    """Walk the CC transcript backwards collecting assistant text blocks;
    stop at the most recent real user prompt (skipping tool_result records
    that also carry `type:"user"`)."""
    with open(transcript_path, "rb") as f:
        data = f.read().decode("utf-8", errors="ignore")
    lines = data.splitlines()

    collected: list[str] = []
    for line in reversed(lines):
        try:
            d = json.loads(line)
        except Exception:
            continue
        t = d.get("type")
        if t == "assistant":
            content = (d.get("message") or {}).get("content")
            local: list[str] = []
            if isinstance(content, str):
                local.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        local.append(block.get("text") or "")
            if local:
                collected.insert(0, "".join(local))
        elif t == "user" and _is_real_user_prompt(d):
            break
    return "".join(collected)


def build_event(event_kind: str, hook_input: dict) -> dict:
    ts = now_utc_iso()

    if event_kind == "user":
        prompt = hook_input.get("prompt")
        if not isinstance(prompt, str):
            prompt = "" if prompt is None else str(prompt)
        return {"ts": ts, "role": "user", "content": redact(prompt)}

    if event_kind == "assistant":
        # CC provides the final text block in `last_assistant_message`. Any
        # earlier text blocks from the same turn (before a tool call) live in
        # the transcript and are recovered via walk-back. They're usually not
        # flushed for text-only turns, but tool calls force the flush.
        final_text = hook_input.get("last_assistant_message") or ""
        if not isinstance(final_text, str):
            final_text = ""
        tpath = hook_input.get("transcript_path")
        flushed_text = ""
        if tpath and os.path.isfile(tpath):
            flushed_text = extract_last_assistant_text(tpath)
        if final_text and flushed_text.endswith(final_text):
            text = flushed_text
        elif flushed_text and final_text:
            text = flushed_text + "\n\n" + final_text
        else:
            text = flushed_text or final_text
        return {"ts": ts, "role": "assistant", "content": redact(text)}

    if event_kind == "session-start":
        sid = hook_input.get("session_id") or ""
        return {"ts": ts, "role": "system", "content": "bot_started",
                "meta": {"session_id": sid}}

    if event_kind == "session-end":
        sid = hook_input.get("session_id") or ""
        return {"ts": ts, "role": "system", "content": "bot_stopped",
                "meta": {"session_id": sid}}

    raise ValueError(f"unknown event: {event_kind!r}")


def main() -> int:
    p = argparse.ArgumentParser(description="Ginarr write-path hook — appends JSONL events.")
    p.add_argument(
        "--event",
        required=True,
        choices=["user", "assistant", "session-start", "session-end"],
    )
    args = p.parse_args()

    hook_input = read_hook_input()

    vault_root = os.environ.get("GINARR_VAULT_ROOT")
    if not vault_root:
        sys.stderr.write("log_event: GINARR_VAULT_ROOT not set; skipping.\n")
        return 0
    vault_root_path = Path(vault_root)

    try:
        event = build_event(args.event, hook_input)
        append_event(vault_root_path, event)
    except Exception as e:
        err_event = {
            "ts": now_utc_iso(),
            "role": "system",
            "content": "hook_error",
            "meta": {
                "hook": args.event,
                "error": str(e),
                "traceback": traceback.format_exc(),
            },
        }
        try:
            append_event(vault_root_path, err_event)
        except Exception:
            sys.stderr.write(f"log_event: failed to write hook_error:\n{traceback.format_exc()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

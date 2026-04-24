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
import hashlib
import json
import os
import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from redactor import redact  # noqa: E402

# Layer 4 — /nolog runtime pause.
# Flag file exists → write-path is paused. Sidecar records the last state that
# log_event.py observed, so transitions (off→on, on→off) can be detected and
# the matching `system:log_paused` / `log_resumed` events emitted once each.
#
# Layer 3 — /redact owner-marked denylist.
# One value per line. `redact()` replaces occurrences with [REDACTED:user-marked]
# on every user/assistant write. Process-lifetime only — cleared on bot_started.
CHANNELS_DIR = SCRIPT_DIR.parent / "channels"
NOLOG_FLAG = CHANNELS_DIR / ".nolog"
NOLOG_STATE = CHANNELS_DIR / ".nolog.state"
REDACT_LIST = CHANNELS_DIR / ".redact-list"


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


def _emit_system(vault_root: Path, content: str) -> None:
    event = {"ts": now_utc_iso(), "role": "system", "content": content}
    append_event(vault_root, event)


def _apply_nolog(vault_root: Path, event_kind: str) -> bool:
    """Check the /nolog flag against the last-seen state. Emit log_paused /
    log_resumed on transitions. Return True when the caller should skip the
    current user/assistant event (i.e. the pause window is active *after*
    this tick's transition handling)."""
    if event_kind not in ("user", "assistant"):
        return False

    flag_on = NOLOG_FLAG.exists()
    state_on = NOLOG_STATE.exists()

    if flag_on and not state_on:
        _emit_system(vault_root, "log_paused")
        CHANNELS_DIR.mkdir(parents=True, exist_ok=True)
        NOLOG_STATE.touch()
        return True

    if not flag_on and state_on:
        _emit_system(vault_root, "log_resumed")
        try:
            NOLOG_STATE.unlink()
        except FileNotFoundError:
            pass
        return False

    return flag_on


def _reset_channels_on_start() -> None:
    """Wipe runtime-only channel state so a restart starts clean:
    no stuck pause, no leftover owner-marked redactions."""
    for p in (NOLOG_FLAG, NOLOG_STATE, REDACT_LIST):
        try:
            p.unlink()
        except FileNotFoundError:
            pass


def _load_redact_list() -> list[str]:
    """Return the Layer 3 owner-marked denylist values, one per non-blank
    line. Missing or unreadable file → empty list (soft-fail; the write-path
    must never block)."""
    try:
        with open(REDACT_LIST, encoding="utf-8") as f:
            return [line.rstrip("\n") for line in f if line.strip()]
    except (FileNotFoundError, OSError):
        return []


# ---------------------------------------------------------------------------
# Channel-tag parsing (SPEC.v3 §"Attachments")
#
# The Telegram plugin delivers messages as an XML tag in the prompt:
#     <channel source="telegram" chat_id="…" user="…" ts="…"
#              image_path="/tmp/…" attachment_file_id="…" attachment_kind="voice" …>
#     text content
#     </channel>
#
# For logging we rewrite each tag into plain text plus SPEC attachment
# markers. `image_path` is a concrete local file so we copy it alongside
# the day's log and emit `[image: attachments/…]`. `attachment_file_id`
# is not yet downloaded at hook time — the agent fetches it on demand —
# so we emit `[<kind>: unresolved:<file_id>]` as a Ginarr extension. A
# future write-path phase may backfill the real path once the download
# lands.
# ---------------------------------------------------------------------------

_CHANNEL_RE = re.compile(r"<channel\b([^>]*)>(.*?)</channel>", re.DOTALL)
_ATTR_RE = re.compile(r'(\w+)="([^"]*)"')

_AUDIO_KINDS = {"voice", "audio"}


def copy_attachment(src: str, vault_root: Path, dt: datetime) -> str | None:
    """Copy src into logs/YYYY/MM/attachments/ under a content-addressed
    name. Returns the path relative to logs/YYYY/MM/, or None on failure."""
    try:
        with open(src, "rb") as f:
            payload = f.read()
    except Exception:
        return None
    digest = hashlib.sha256(payload).hexdigest()[:8]
    ext = Path(src).suffix
    name = f"{dt.strftime('%Y-%m-%d')}_{digest}{ext}"
    dest_dir = (
        vault_root / "logs" / f"{dt.year:04d}" / f"{dt.month:02d}" / "attachments"
    )
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / name
    if not dest.exists():
        try:
            with open(dest, "wb") as f:
                f.write(payload)
        except Exception:
            return None
    return f"attachments/{name}"


def _attachment_marker_kind(attr_kind: str) -> str:
    return "audio" if attr_kind in _AUDIO_KINDS else "file"


def parse_channel_tags(prompt: str, vault_root: Path, dt: datetime) -> str:
    """Replace <channel …>…</channel> blocks with plain text plus SPEC
    attachment markers. Prompts without the tag pass through unchanged."""
    def replace(m: re.Match) -> str:
        attrs = dict(_ATTR_RE.findall(m.group(1)))
        inner = m.group(2).strip()
        parts: list[str] = []
        if inner:
            parts.append(inner)

        image_path = attrs.get("image_path")
        if image_path:
            rel = copy_attachment(image_path, vault_root, dt)
            if rel:
                parts.append(f"[image: {rel}]")

        file_id = attrs.get("attachment_file_id")
        if file_id:
            kind = _attachment_marker_kind(attrs.get("attachment_kind", ""))
            parts.append(f"[{kind}: unresolved:{file_id}]")

        return " ".join(parts) if parts else ""

    return _CHANNEL_RE.sub(replace, prompt)


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


def build_event(event_kind: str, hook_input: dict, vault_root: Path) -> dict:
    dt = datetime.now(timezone.utc)
    ts = (
        dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    )

    if event_kind == "user":
        prompt = hook_input.get("prompt")
        if not isinstance(prompt, str):
            prompt = "" if prompt is None else str(prompt)
        prompt = parse_channel_tags(prompt, vault_root, dt)
        return {"ts": ts, "role": "user", "content": redact(prompt, _load_redact_list())}

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
        return {"ts": ts, "role": "assistant", "content": redact(text, _load_redact_list())}

    if event_kind == "session-start":
        sid = hook_input.get("session_id") or ""
        return {"ts": ts, "role": "system", "content": "bot_started",
                "meta": {"session_id": sid}}

    if event_kind == "session-end":
        sid = hook_input.get("session_id") or ""
        return {"ts": ts, "role": "system", "content": "bot_stopped",
                "meta": {"session_id": sid}}

    raise ValueError(f"unknown event: {event_kind!r}")


def _run_self_test() -> int:
    import tempfile

    fails = 0
    total = 0

    def fail(label: str, msg: str) -> None:
        nonlocal fails
        fails += 1
        sys.stderr.write(f"FAIL [{label}]\n  {msg}\n")

    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp) / "vault"
        (vault / "logs").mkdir(parents=True)

        # Build a source image to copy
        src = Path(tmp) / "pic.jpg"
        src.write_bytes(b"\xff\xd8fakejpeg\xff\xd9")

        dt = datetime(2026, 4, 24, 12, 0, 0, tzinfo=timezone.utc)

        # 1) Pass-through: plain prompt without any channel tag
        total += 1
        out = parse_channel_tags("hello world", vault, dt)
        if out != "hello world":
            fail("pass-through", f"got: {out!r}")

        # 2) Image attachment: inner text + image_path → text + [image: …]
        total += 1
        prompt = (
            f'<channel source="telegram" chat_id="1" user="u" ts="x" '
            f'image_path="{src}">look at this</channel>'
        )
        out = parse_channel_tags(prompt, vault, dt)
        if not out.startswith("look at this [image: attachments/2026-04-24_"):
            fail("image marker prefix", f"got: {out!r}")
        if not out.endswith(".jpg]"):
            fail("image marker suffix", f"got: {out!r}")
        # and the file must actually exist in the vault
        total += 1
        copied = list((vault / "logs" / "2026" / "04" / "attachments").glob("*.jpg"))
        if len(copied) != 1:
            fail("image copy", f"copied files: {copied}")

        # 3) Image-only (no inner text)
        total += 1
        prompt = f'<channel source="telegram" image_path="{src}"></channel>'
        out = parse_channel_tags(prompt, vault, dt)
        if not out.startswith("[image: attachments/"):
            fail("image-only marker", f"got: {out!r}")

        # 4) Voice message: attachment_kind=voice → [audio: unresolved:<id>]
        total += 1
        prompt = (
            '<channel source="telegram" attachment_file_id="FID123" '
            'attachment_kind="voice">transcript unavailable</channel>'
        )
        out = parse_channel_tags(prompt, vault, dt)
        if out != "transcript unavailable [audio: unresolved:FID123]":
            fail("voice marker", f"got: {out!r}")

        # 5) Document: attachment_kind=document → [file: unresolved:<id>]
        total += 1
        prompt = (
            '<channel source="telegram" attachment_file_id="DOC9" '
            'attachment_kind="document">a file</channel>'
        )
        out = parse_channel_tags(prompt, vault, dt)
        if out != "a file [file: unresolved:DOC9]":
            fail("file marker", f"got: {out!r}")

        # 6) No attachment_kind → defaults to file
        total += 1
        prompt = '<channel source="telegram" attachment_file_id="X">q</channel>'
        out = parse_channel_tags(prompt, vault, dt)
        if out != "q [file: unresolved:X]":
            fail("unknown-kind → file", f"got: {out!r}")

        # 7) Multiple channel tags in one prompt
        total += 1
        prompt = (
            '<channel source="telegram">first</channel>\n'
            '<channel source="telegram">second</channel>'
        )
        out = parse_channel_tags(prompt, vault, dt)
        if out != "first\nsecond":
            fail("multi-tag", f"got: {out!r}")

        # 8) Missing image file → marker is skipped
        total += 1
        prompt = (
            '<channel source="telegram" image_path="/no/such/file.jpg">'
            'broken</channel>'
        )
        out = parse_channel_tags(prompt, vault, dt)
        if out != "broken":
            fail("missing image → no marker", f"got: {out!r}")

        # 9) Empty tag (no attrs, no text)
        total += 1
        prompt = "<channel></channel>"
        out = parse_channel_tags(prompt, vault, dt)
        if out != "":
            fail("empty tag", f"got: {out!r}")

        # 10) Idempotent second copy: hash matches → no duplicate, same marker
        total += 1
        out2 = parse_channel_tags(
            f'<channel image_path="{src}">again</channel>', vault, dt
        )
        if "[image: attachments/" not in out2:
            fail("idempotent second run", f"got: {out2!r}")
        copied2 = list((vault / "logs" / "2026" / "04" / "attachments").glob("*.jpg"))
        if len(copied2) != 1:
            fail("idempotent no dup", f"files: {copied2}")

        # ------------------------------------------------------------------
        # /nolog state-machine tests. Redirect module-level nolog paths into
        # a temp channels dir so we can drive transitions without touching
        # the real runtime files.
        global CHANNELS_DIR, NOLOG_FLAG, NOLOG_STATE  # noqa: PLW0603
        orig_nolog = (CHANNELS_DIR, NOLOG_FLAG, NOLOG_STATE)
        try:
            tmp_channels = Path(tmp) / "channels"
            tmp_channels.mkdir(parents=True, exist_ok=True)
            CHANNELS_DIR = tmp_channels
            NOLOG_FLAG = tmp_channels / ".nolog"
            NOLOG_STATE = tmp_channels / ".nolog.state"

            vault2 = Path(tmp) / "vault_nolog"
            (vault2 / "logs").mkdir(parents=True)

            def day_log():
                now = datetime.now(timezone.utc)
                p = (
                    vault2 / "logs" / f"{now.year:04d}" / f"{now.month:02d}"
                    / f"{now.strftime('%Y-%m-%d')}.jsonl"
                )
                if not p.exists():
                    return []
                return [
                    json.loads(line)
                    for line in p.read_text().splitlines()
                    if line.strip()
                ]

            # 11) No flag → don't skip, don't emit
            total += 1
            skip = _apply_nolog(vault2, "user")
            if skip or day_log():
                fail("nolog off → no skip, no emit",
                     f"skip={skip} events={day_log()}")

            # 12) Transition off→on: skip, emit log_paused, sidecar appears
            total += 1
            NOLOG_FLAG.touch()
            skip = _apply_nolog(vault2, "user")
            events = day_log()
            if (not skip or not NOLOG_STATE.exists() or len(events) != 1
                    or events[0]["content"] != "log_paused"):
                fail(
                    "pause transition",
                    f"skip={skip} state={NOLOG_STATE.exists()} events={events}",
                )

            # 13) Steady paused: skip, no new emission
            total += 1
            skip = _apply_nolog(vault2, "assistant")
            events = day_log()
            if not skip or len(events) != 1:
                fail("paused steady-state", f"skip={skip} events={events}")

            # 14) Transition on→off: don't skip, emit log_resumed, sidecar gone
            total += 1
            NOLOG_FLAG.unlink()
            skip = _apply_nolog(vault2, "user")
            events = day_log()
            if (skip or NOLOG_STATE.exists() or len(events) != 2
                    or events[1]["content"] != "log_resumed"):
                fail(
                    "resume transition",
                    f"skip={skip} state={NOLOG_STATE.exists()} events={events}",
                )

            # 15) Steady resumed: don't skip, no new emission
            total += 1
            skip = _apply_nolog(vault2, "user")
            events = day_log()
            if skip or len(events) != 2:
                fail("resumed steady-state", f"skip={skip} events={events}")

            # 16) session-start / session-end always pass through nolog
            total += 1
            NOLOG_FLAG.touch()
            s1 = _apply_nolog(vault2, "session-start")
            s2 = _apply_nolog(vault2, "session-end")
            if s1 or s2:
                fail("session events pass through nolog",
                     f"start={s1} end={s2}")
            NOLOG_FLAG.unlink()

            # 17) _reset_channels_on_start clears nolog flag and state
            total += 1
            NOLOG_FLAG.touch()
            NOLOG_STATE.touch()
            _reset_channels_on_start()
            if NOLOG_FLAG.exists() or NOLOG_STATE.exists():
                fail(
                    "reset on start",
                    f"flag={NOLOG_FLAG.exists()} state={NOLOG_STATE.exists()}",
                )
        finally:
            CHANNELS_DIR, NOLOG_FLAG, NOLOG_STATE = orig_nolog

        # ------------------------------------------------------------------
        # /redact Layer 3 denylist. Redirect the list file into a temp dir
        # and exercise the loader + session-start reset.
        global REDACT_LIST  # noqa: PLW0603
        orig_redact = REDACT_LIST
        try:
            tmp_ch = Path(tmp) / "channels_redact"
            tmp_ch.mkdir(parents=True, exist_ok=True)
            REDACT_LIST = tmp_ch / ".redact-list"

            # 18) Missing file → empty list
            total += 1
            if _load_redact_list():
                fail("redact list missing → empty",
                     f"got {_load_redact_list()}")

            # 19) Single value
            total += 1
            REDACT_LIST.write_text("falcon\n", encoding="utf-8")
            if _load_redact_list() != ["falcon"]:
                fail("redact list single", f"got {_load_redact_list()}")

            # 20) Skips blank / whitespace-only lines
            total += 1
            REDACT_LIST.write_text(
                "alpha\n\n  \nbeta\ngamma\n", encoding="utf-8"
            )
            if _load_redact_list() != ["alpha", "beta", "gamma"]:
                fail("redact list skip blanks",
                     f"got {_load_redact_list()}")

            # 21) End-to-end: build_event uses the list to scrub content
            total += 1
            vault3 = Path(tmp) / "vault_redact"
            (vault3 / "logs").mkdir(parents=True)
            REDACT_LIST.write_text("Galina\n", encoding="utf-8")
            ev = build_event("user", {"prompt": "hi Galina"}, vault3)
            if ev["content"] != "hi [REDACTED:user-marked]":
                fail("build_event applies redact list",
                     f"got {ev['content']!r}")

            # 22) _reset_channels_on_start wipes the redact list too
            total += 1
            _reset_channels_on_start()
            if REDACT_LIST.exists():
                fail("reset clears redact list", "file still exists")
        finally:
            REDACT_LIST = orig_redact

    if fails:
        sys.stderr.write(f"\n{fails}/{total} self-test cases failed\n")
        return 1
    sys.stderr.write(f"self-test: {total}/{total} passed\n")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Ginarr write-path hook — appends JSONL events.")
    p.add_argument(
        "--event",
        choices=["user", "assistant", "session-start", "session-end"],
    )
    p.add_argument("--self-test", action="store_true", help="Run built-in test cases and exit")
    args = p.parse_args()

    if args.self_test:
        return _run_self_test()
    if not args.event:
        p.error("--event is required unless --self-test is set")

    hook_input = read_hook_input()

    vault_root = os.environ.get("GINARR_VAULT_ROOT")
    if not vault_root:
        sys.stderr.write("log_event: GINARR_VAULT_ROOT not set; skipping.\n")
        return 0
    vault_root_path = Path(vault_root)

    try:
        if _apply_nolog(vault_root_path, args.event):
            return 0
        event = build_event(args.event, hook_input, vault_root_path)
        append_event(vault_root_path, event)
        if args.event == "session-start":
            _reset_channels_on_start()
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

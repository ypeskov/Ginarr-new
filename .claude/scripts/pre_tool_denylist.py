#!/usr/bin/env python3
"""Layer 1 — PreToolUse access-control hook.

Reads Claude Code PreToolUse JSON on stdin; if the call targets a path
on the denylist (SPEC.v3 §"Secrets and PII"), emits a `deny` decision
and exits 0. Non-matching calls exit 0 silently with no output, letting
the runtime continue.

Denylist (from SPEC):
    .env*            (except .env.example — committed template, no secrets)
    *.pem, *.key
    id_rsa*, credentials*
    ~/.ssh/**, ~/.aws/**, ~/.config/gcloud/**
    ~/.kube/config

Coverage:
    Read / Edit / Write / NotebookEdit  — `tool_input.file_path` (or
        `notebook_path`) is checked.
    Bash                                — `tool_input.command` is scanned
        token-by-token. Best-effort: pure shell-parser-free regex.
    Other tools                         — pass through.

Contract: one file, stdlib only, never blocks the runtime on its own
exceptions (exits 0 on parse failures).
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

HOME = Path.home()

DENY_ENV_GLOB = ".env*"
ENV_ALLOW_BASENAME = ".env.example"

DENY_BASENAME_GLOBS = ["*.pem", "*.key", "id_rsa*", "credentials*"]

DENY_DIR_PREFIXES = [
    HOME / ".ssh",
    HOME / ".aws",
    HOME / ".config" / "gcloud",
]

DENY_FILE_EXACT = [
    HOME / ".kube" / "config",
]


def _resolve(p: Path) -> Path:
    try:
        return p.resolve(strict=False)
    except Exception:
        return p


def _normalize(path_str: str, cwd: str | None = None) -> Path:
    expanded = os.path.expanduser(path_str)
    p = Path(expanded)
    if not p.is_absolute() and cwd:
        p = Path(cwd) / p
    return _resolve(p)


def path_is_denied(path_str: str, cwd: str | None = None) -> bool:
    if not path_str:
        return False
    p = _normalize(path_str, cwd)
    basename = p.name

    for exact in DENY_FILE_EXACT:
        if p == _resolve(exact):
            return True

    for prefix in DENY_DIR_PREFIXES:
        prefix_r = _resolve(prefix)
        try:
            p.relative_to(prefix_r)
            return True
        except ValueError:
            pass

    if fnmatch.fnmatchcase(basename, DENY_ENV_GLOB) and basename != ENV_ALLOW_BASENAME:
        return True

    for glob in DENY_BASENAME_GLOBS:
        if fnmatch.fnmatchcase(basename, glob):
            return True

    return False


# Token shape: keep only things that look like paths (contain `/`, start with
# `~`, start with `.`, or end with a denylist-relevant extension). Pure
# regex, no shell parsing — best-effort defense in depth.
_BASH_TOKEN_RE = re.compile(r"[\w./~\-]+")


def bash_first_denied(command: str, cwd: str | None = None) -> str | None:
    for m in _BASH_TOKEN_RE.finditer(command):
        tok = m.group(0)
        if "/" not in tok and not tok.startswith("~") and not tok.startswith("."):
            continue
        if path_is_denied(tok, cwd=cwd):
            return tok
    return None


def decide(hook_input: dict) -> tuple[bool, str]:
    tool = hook_input.get("tool_name") or ""
    ti = hook_input.get("tool_input") or {}
    cwd = hook_input.get("cwd")

    if tool in ("Read", "Edit", "Write"):
        fp = ti.get("file_path") or ""
        if isinstance(fp, str) and path_is_denied(fp, cwd=cwd):
            return True, "[REDACTED: path in denylist]"
        return False, ""

    if tool == "NotebookEdit":
        fp = ti.get("notebook_path") or ti.get("file_path") or ""
        if isinstance(fp, str) and path_is_denied(fp, cwd=cwd):
            return True, "[REDACTED: path in denylist]"
        return False, ""

    if tool == "Bash":
        cmd = ti.get("command") or ""
        if isinstance(cmd, str) and bash_first_denied(cmd, cwd=cwd):
            return True, "[REDACTED: path in denylist]"
        return False, ""

    return False, ""


def _emit_deny(reason: str) -> None:
    sys.stdout.write(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


def _run_self_test() -> int:
    cases: list[tuple[dict, bool, str]] = [
        # Read — allow
        ({"tool_name": "Read", "tool_input": {"file_path": "/tmp/foo.txt"}}, False, "plain tmp file"),
        ({"tool_name": "Read", "tool_input": {"file_path": str(HOME / "Ginarr" / "README.md")}}, False, "repo file"),
        # Read — deny
        ({"tool_name": "Read", "tool_input": {"file_path": str(HOME / ".ssh" / "id_rsa")}}, True, "~/.ssh/id_rsa"),
        ({"tool_name": "Read", "tool_input": {"file_path": str(HOME / ".aws" / "credentials")}}, True, "aws creds"),
        ({"tool_name": "Read", "tool_input": {"file_path": str(HOME / ".config" / "gcloud" / "anything")}}, True, "gcloud dir"),
        ({"tool_name": "Read", "tool_input": {"file_path": str(HOME / ".kube" / "config")}}, True, "kube config"),
        ({"tool_name": "Read", "tool_input": {"file_path": "/tmp/my.pem"}}, True, "pem extension"),
        ({"tool_name": "Read", "tool_input": {"file_path": "/tmp/host.key"}}, True, "key extension"),
        ({"tool_name": "Read", "tool_input": {"file_path": "/tmp/id_rsa_backup"}}, True, "id_rsa prefix"),
        ({"tool_name": "Read", "tool_input": {"file_path": "/tmp/credentials.json"}}, True, "credentials prefix"),
        ({"tool_name": "Read", "tool_input": {"file_path": "/tmp/.env"}}, True, "plain .env"),
        ({"tool_name": "Read", "tool_input": {"file_path": "/tmp/.env.prod"}}, True, ".env.prod"),
        # .env.example allowlist
        ({"tool_name": "Read", "tool_input": {"file_path": "/tmp/.env.example"}}, False, ".env.example is template"),
        # Negative: path contains 'env' but not as prefix
        ({"tool_name": "Read", "tool_input": {"file_path": "/tmp/environment.py"}}, False, "environment.py"),
        ({"tool_name": "Read", "tool_input": {"file_path": "/tmp/foo.env"}}, False, "basename starts with foo"),
        # Write / Edit — same matcher
        ({"tool_name": "Write", "tool_input": {"file_path": str(HOME / ".ssh" / "authorized_keys")}}, True, "write to ssh"),
        ({"tool_name": "Edit", "tool_input": {"file_path": "/tmp/keyed.txt"}}, False, "keyed.txt not *.key"),
        ({"tool_name": "Edit", "tool_input": {"file_path": "/tmp/tls.key"}}, True, "tls.key"),
        # Bash — deny
        ({"tool_name": "Bash", "tool_input": {"command": "cat ~/.ssh/id_rsa"}}, True, "cat ssh key"),
        ({"tool_name": "Bash", "tool_input": {"command": "ls ~/.aws"}}, True, "ls aws dir"),
        ({"tool_name": "Bash", "tool_input": {"command": "cat /tmp/foo.pem"}}, True, "cat pem"),
        # Bash — allow
        ({"tool_name": "Bash", "tool_input": {"command": "ls /tmp"}}, False, "ls tmp"),
        ({"tool_name": "Bash", "tool_input": {"command": "echo api_token_is_nice"}}, False, "token in word"),
        ({"tool_name": "Bash", "tool_input": {"command": "cat .env.example"}}, False, "bash .env.example"),
        # Unknown tool — pass through
        ({"tool_name": "Glob", "tool_input": {"path": str(HOME / ".ssh")}}, False, "glob pass-through"),
        # Missing tool_input
        ({"tool_name": "Read", "tool_input": {}}, False, "no file_path"),
        ({}, False, "empty input"),
    ]

    fails = 0
    for i, (hi, expect_deny, label) in enumerate(cases, 1):
        got_deny, _ = decide(hi)
        if got_deny != expect_deny:
            fails += 1
            sys.stderr.write(
                f"FAIL #{i} [{label}]\n  input:    {hi!r}\n  expected: deny={expect_deny}\n  got:      deny={got_deny}\n"
            )

    total = len(cases)
    if fails:
        sys.stderr.write(f"\n{fails}/{total} self-test cases failed\n")
        return 1
    sys.stderr.write(f"self-test: {total}/{total} passed\n")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Layer 1 PreToolUse denylist hook.")
    p.add_argument("--self-test", action="store_true", help="Run built-in test cases and exit")
    args = p.parse_args()

    if args.self_test:
        return _run_self_test()

    try:
        data = sys.stdin.read()
        hook_input = json.loads(data) if data.strip() else {}
    except Exception:
        return 0

    try:
        deny, reason = decide(hook_input)
    except Exception:
        return 0

    if deny:
        _emit_deny(reason)
    return 0


if __name__ == "__main__":
    sys.exit(main())

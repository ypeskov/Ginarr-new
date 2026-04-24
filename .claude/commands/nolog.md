---
description: Pause or resume the write-path log. /nolog on opens a pause window, /nolog off closes it. Layer 4 of Ginarr's secret-protection stack.
argument-hint: on | off
allowed-tools: Bash(mkdir:*), Bash(touch:*), Bash(rm:*), Bash(test:*), Bash(ls:*)
---

Toggle Ginarr's write-path pause (SPEC.v3 §"Layer 4").

Argument: `$ARGUMENTS`

Interpret the argument (case-insensitive):

- **`on`** — create the pause flag. Run `mkdir -p .claude/channels && touch .claude/channels/.nolog`. Reply: `Logging paused — user/assistant events will be skipped until /nolog off or bot restart.`
- **`off`** — clear the pause flag. Run `rm -f .claude/channels/.nolog`. Reply: `Logging resumed.`
- **empty or anything else** — do not change any files. Check whether `.claude/channels/.nolog` currently exists (e.g. `test -f .claude/channels/.nolog && echo on || echo off`) and reply with the current state plus the two accepted arguments.

Do not emit any `log_paused` / `log_resumed` events yourself. `log_event.py` detects the flag transition on its next firing and writes the system event automatically.

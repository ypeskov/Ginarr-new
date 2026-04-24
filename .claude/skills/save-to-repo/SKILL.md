---
name: save-to-repo
description: >
  Commit (and optionally push) local changes for the Ginarr repo following
  project conventions. Use whenever the user asks to commit, save changes,
  push, "закоммить", "коммить", "пушни", or "сохрани в репу". Enforces
  English-only messages, no AI co-author footer, bundled docs/roadmap
  updates, inline git identity, and a workaround for the Layer 1 denylist
  trap.
metadata:
  project: Ginarr
  version: "1.0"
---

# save-to-repo

Runs the commit (and optional push) workflow for this repository. The rules below are project-specific — they layer on top of general git hygiene, they don't replace it.

## Must

1. **No AI co-author footer.** Never add `Co-Authored-By: Claude …` (or any AI identity) to commit messages. Attribution goes to the human author only.

2. **Messages are in English.** Subject and body are always English per CLAUDE.md Ground rules, regardless of the conversation language.

3. **One commit bundles code + matching docs + parent `index.md`.** If a commit touches a script, hook, or skill under `.claude/`, the matching `docs/<…>.md` and its parent `docs/*/index.md` go in the **same commit**. If the change lands a roadmap item, tick its checkbox in `docs/roadmap.md` in the **same commit**.

4. **Git identity is inline.** This repo has no configured `user.name` / `user.email`. Inject them per-commit:
   ```
   git -c user.name="Yuriy Peskov" -c user.email="yuriy.peskov@gmail.com" commit -F /tmp/ginarr_commit_msg.txt
   ```

5. **Stage by filename, never `-A` / `.`**. Spell each path. Guards against accidentally staging `.env`, credentials, or editor noise.

6. **Work around the Layer 1 denylist trap.** The `PreToolUse` hook (`pre_tool_denylist.py`) scans every Bash command's *text* for denylisted path tokens — including the body of a `-m "..."` commit message. If your subject or body mentions paths like `.env`, `.ssh/`, `.pem`, `.key`, `id_rsa`, `credentials`, `~/.aws`, `~/.config/gcloud`, or `~/.kube`, the commit will be blocked. Write the message to `/tmp/ginarr_commit_msg.txt` via the Write tool first, then commit with `-F /tmp/ginarr_commit_msg.txt`. Remove the tmp file after the push.

7. **Push only when explicitly asked.** Pushing is a shared-state action. Default behaviour after a commit is to stop and wait for confirmation. When the user says "push" / "пуш" / "закоммить и запушь", plain `git push` (upstream is already set on `main`).

## Workflow

1. `git status` (no `-uall`) and `git diff` — see what's changing. If any untracked file looks like a secret, tmp, or editor artefact, call it out before staging.
2. Stage the specific files by path.
3. Draft commit subject ≤ 72 chars, imperative mood ("Add X", "Fix Y", "Rewrite Z"). Body explains the *why*, not the *what*.
4. Write the full message to `/tmp/ginarr_commit_msg.txt`.
5. Commit with inline identity and `-F`:
   ```
   git -c user.name="Yuriy Peskov" -c user.email="yuriy.peskov@gmail.com" \
       commit -F /tmp/ginarr_commit_msg.txt
   ```
6. `git status` — confirm clean tree (the commit landed).
7. If the user asked to push: `git push`, report the range (`<old>..<new>`).
8. `rm /tmp/ginarr_commit_msg.txt`.

## Don't

- Don't `git commit --amend` anything already pushed. Correct with a new commit on top.
- Don't `--no-verify` / `--no-gpg-sign` / otherwise skip hooks. If a hook fails, diagnose — don't bypass. (Exception: the user explicitly asks.)
- Don't force-push. Never to `main`, period, without an explicit request.
- Don't commit `.env`, `.claude/settings.local.json`, `__pycache__/`, or anything under `logs/` — all gitignored, but double-check with `git status`.
- Don't include lines like `🤖 Generated with Claude Code` or similar in the message. Same reason as rule 1.

## Repo context

- Remote: `git@github.com:ypeskov/Ginarr-new.git` (SSH via `~/.ssh/id_ed25519`).
- Default branch: `main`.
- Pre-existing trap: `settings.json` wires `pre_tool_denylist.py` as a `PreToolUse` hook. That's the script causing rule 6.

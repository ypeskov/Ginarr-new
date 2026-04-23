#!/bin/bash
# Ginarr Claude Code bot launcher — runs in tmux under the ginarr session.
# Points the Telegram plugin at the project-local state dir so Ginarr and
# OpenClaw can coexist with separate bot tokens.

export HOME=/home/krokobot
export PATH="$HOME/.bun/bin:$HOME/.local/bin:/home/linuxbrew/.linuxbrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export TELEGRAM_STATE_DIR="$HOME/Ginarr/.claude/channels/telegram"

cd "$HOME/Ginarr"

# --continue: resume last session context from ~/.claude/projects/<proj>/
# --channels: enable Telegram channel; plugin reads TELEGRAM_STATE_DIR
# --remote-control: allow controlling this session from claude.ai/mobile
exec claude --permission-mode bypassPermissions --dangerously-skip-permissions \
            --continue --channels plugin:telegram@claude-plugins-official --remote-control

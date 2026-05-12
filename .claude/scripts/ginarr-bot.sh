#!/bin/bash
# Ginarr Claude Code bot launcher — runs in tmux under the ginarr session.
# Points the Telegram plugin at the project-local state dir so Ginarr and
# OpenClaw can coexist with separate bot tokens.
#
# Linux + Telegram + claude.ai-subscription infra. Not used on macOS forks
# without a Telegram bridge or under API-key-only billing (remote-control
# requires claude.ai OAuth).

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
: "${HOME:=$(eval echo "~$(whoami)")}"

export PATH="$HOME/.bun/bin:$HOME/.local/bin:/home/linuxbrew/.linuxbrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export TELEGRAM_STATE_DIR="$REPO_ROOT/.claude/channels/telegram"

ENV_FILE="$REPO_ROOT/.claude/.env"
if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

cd "$REPO_ROOT"

# --continue: resume last session context from ~/.claude/projects/<proj>/
# --channels: enable Telegram channel; plugin reads TELEGRAM_STATE_DIR
# --remote-control: allow controlling this session from claude.ai/mobile
exec claude --permission-mode bypassPermissions --dangerously-skip-permissions \
            --continue --channels plugin:telegram@claude-plugins-official --remote-control

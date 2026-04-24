#!/bin/bash
# Thin wrapper — the real logic lives in statusline.py so stdin is not shadowed
# by a heredoc.
exec python3 "$(dirname "$0")/statusline.py"

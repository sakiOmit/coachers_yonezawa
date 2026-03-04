#!/bin/bash
# start-chrome-debug.sh
#
# プロジェクト用ラッパー。
# 汎用版 chrome-debug.sh が ~/windows-dotfiles にあればそちらを使い、
# なければ内蔵ロジックで実行する。
#
# Usage:
#   bash .claude/skills/figma-prepare/scripts/start-chrome-debug.sh [figma-url]

set -euo pipefail

GENERIC_SCRIPT="$HOME/windows-dotfiles/scripts/chrome-debug.sh"

if [ -x "${GENERIC_SCRIPT}" ]; then
  exec bash "${GENERIC_SCRIPT}" "$@"
fi

# ─── フォールバック: 汎用版がない場合 ───
PORT=9222
WIN_USER="${WIN_USER:-utgit}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_wsl}"
WIN_IP=$(ip route show default | awk '{print $3}')
URL="${1:-}"

echo "=== Chrome Debug Setup (embedded) ==="

# トンネル
if ! lsof -i ":${PORT}" &>/dev/null; then
  ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
      -i "${SSH_KEY}" -L "${PORT}:127.0.0.1:${PORT}" \
      -N "${WIN_USER}@${WIN_IP}" &
  sleep 2
fi

# Chrome
if ! curl -s --max-time 3 "http://localhost:${PORT}/json/version" &>/dev/null; then
  LAUNCH="\"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe\" --remote-debugging-port=${PORT} --user-data-dir=\"C:\\Users\\${WIN_USER}\\.chrome-debug\""
  [ -n "${URL}" ] && LAUNCH="${LAUNCH} \"${URL}\""
  cmd.exe /c "start \"\" ${LAUNCH}" 2>/dev/null
  sleep 5
fi

# 確認
if curl -s --max-time 3 "http://localhost:${PORT}/json/version" &>/dev/null; then
  echo "=== Ready ==="
else
  echo "ERROR: Cannot connect to Chrome"
  exit 1
fi

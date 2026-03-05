#!/bin/bash
# start-chrome-debug.sh
#
# WSL2 上のローカル Chrome をデバッグモードで起動する。
# SSH トンネル不要。
#
# Usage:
#   bash .claude/skills/figma-prepare/scripts/start-chrome-debug.sh [figma-url]

set -euo pipefail

PORT=9222
URL="${1:-}"
CHROME_BIN="${CHROME_BIN:-google-chrome-stable}"
USER_DATA_DIR="${HOME}/.chrome-debug"

echo "=== Chrome Debug Setup (local WSL2) ==="

# 既に接続可能か確認
if curl -s --max-time 3 "http://localhost:${PORT}/json/version" &>/dev/null; then
  echo "Chrome already running on port ${PORT}"
  curl -s "http://localhost:${PORT}/json/version" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  Browser: {d.get(\"Browser\",\"?\")}')" 2>/dev/null || true
  echo "=== Ready ==="
  exit 0
fi

# Chrome をヘッドレスではなく通常モードで起動（Figma 操作に必要）
echo "Starting Chrome on port ${PORT}..."
CHROME_ARGS=(
  "--remote-debugging-port=${PORT}"
  "--user-data-dir=${USER_DATA_DIR}"
  "--no-first-run"
  "--no-default-browser-check"
)

[ -n "${URL}" ] && CHROME_ARGS+=("${URL}")

# バックグラウンドで起動（出力を抑制）
"${CHROME_BIN}" "${CHROME_ARGS[@]}" &>/dev/null &
CHROME_PID=$!

# 起動待機（最大 10 秒）
for i in $(seq 1 10); do
  if curl -s --max-time 2 "http://localhost:${PORT}/json/version" &>/dev/null; then
    echo "Chrome started (PID: ${CHROME_PID})"
    curl -s "http://localhost:${PORT}/json/version" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  Browser: {d.get(\"Browser\",\"?\")}')" 2>/dev/null || true
    echo "=== Ready ==="
    exit 0
  fi
  sleep 1
done

echo "ERROR: Chrome failed to start within 10 seconds"
echo "  Tried: ${CHROME_BIN} --remote-debugging-port=${PORT}"
echo "  Check: Is DISPLAY set? (current: ${DISPLAY:-unset})"
exit 1

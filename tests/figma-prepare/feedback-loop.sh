#!/usr/bin/env bash
# /figma-prepare フィードバックループ
#
# QAチェック → テスト → 結果判定を繰り返し、
# 全クリーンになるまでループする。
#
# Usage:
#   bash feedback-loop.sh              # 通常実行
#   bash feedback-loop.sh --max-rounds 5  # 最大5ラウンド
#
# Exit codes:
#   0 = All clean (QA + tests passed)
#   1 = Issues remain after max rounds
#   2 = Test failure (regression)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MAX_ROUNDS=10
ROUND=0

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --max-rounds) MAX_ROUNDS="$2"; shift 2 ;;
    *) shift ;;
  esac
done

green() { printf "\033[32m%s\033[0m\n" "$1"; }
red()   { printf "\033[31m%s\033[0m\n" "$1"; }
yellow(){ printf "\033[33m%s\033[0m\n" "$1"; }
bold()  { printf "\033[1m%s\033[0m\n" "$1"; }

echo ""
bold "╔══════════════════════════════════════════════════╗"
bold "║     figma-prepare Feedback Loop                  ║"
bold "║     Max rounds: $MAX_ROUNDS                               ║"
bold "╚══════════════════════════════════════════════════╝"

while [[ $ROUND -lt $MAX_ROUNDS ]]; do
  ((ROUND++)) || true
  echo ""
  bold "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  bold "  Round $ROUND / $MAX_ROUNDS"
  bold "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  # Step 1: QA Check
  echo ""
  bold "  [Step 1] QA Check..."
  QA_OK=true
  if bash "$SCRIPT_DIR/qa-check.sh" 2>&1; then
    green "  QA: PASS"
  else
    red "  QA: ISSUES FOUND"
    QA_OK=false
  fi

  # Step 2: Test Suite
  echo ""
  bold "  [Step 2] Test Suite..."
  TEST_OK=true
  TEST_OUTPUT=$(bash "$SCRIPT_DIR/run-tests.sh" 2>&1) || TEST_OK=false

  # Extract results line
  RESULTS_LINE=$(echo "$TEST_OUTPUT" | grep "Results:" | head -1 || echo "")
  if [[ -n "$RESULTS_LINE" ]]; then
    echo "  $RESULTS_LINE"
  fi

  if $TEST_OK; then
    green "  Tests: PASS"
  else
    red "  Tests: FAIL"
    echo "$TEST_OUTPUT" | grep "FAIL:" || true
  fi

  # Step 3: Verdict
  echo ""
  if $QA_OK && $TEST_OK; then
    if [[ $ROUND -eq 1 ]]; then
      # 初回クリーン → 確認のためもう1ラウンド
      yellow "  Round $ROUND: Clean — running verification round..."
      continue
    fi

    bold "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    green "  FEEDBACK LOOP COMPLETE"
    green "  All clean after $ROUND rounds (including verification)"
    bold "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 0
  fi

  if ! $TEST_OK; then
    red "  REGRESSION DETECTED — stopping loop"
    echo "$TEST_OUTPUT" | tail -20
    exit 2
  fi

  # QA issues found but tests pass → report for Claude to fix
  echo ""
  yellow "  Round $ROUND: QA issues found. Claude should fix and re-run."
  yellow "  Re-running loop..."
done

echo ""
red "  MAX ROUNDS ($MAX_ROUNDS) reached — issues may remain"
exit 1

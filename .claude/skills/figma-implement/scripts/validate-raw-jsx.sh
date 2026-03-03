#!/bin/bash
# =============================================================================
# validate-raw-jsx.sh
#
# raw_jsx フィールドが正しく保存されているか検証する
# 保存後に必ず実行すること
#
# Usage: validate-raw-jsx.sh <file> <node_id>
# =============================================================================

set -e

FILE=$1
NODE_ID=$2

if [ -z "$FILE" ] || [ -z "$NODE_ID" ]; then
  echo "Usage: validate-raw-jsx.sh <file> <node_id>"
  exit 1
fi

# Check 1: File exists
if [ ! -f "$FILE" ]; then
  echo "❌ FAIL: File not found: $FILE"
  exit 1
fi

# Check 2: raw_jsx field exists and has content
RAW_JSX=$(jq -r '.raw_jsx // empty' "$FILE" 2>/dev/null)
if [ -z "$RAW_JSX" ]; then
  echo "❌ FAIL: raw_jsx is empty or missing in $FILE"
  exit 1
fi

# Check 3: Length >= 500 (abstracted summaries are typically shorter)
LENGTH=${#RAW_JSX}
if [ "$LENGTH" -lt 500 ]; then
  echo "❌ FAIL: raw_jsx too short ($LENGTH chars, min: 500)"
  echo "   This usually means the content was abstracted/summarized."
  exit 1
fi

# Check 4: Contains required patterns (JSX structure indicators)
REQUIRED_PATTERNS=(
  "export default function"
  "return ("
  "className="
  "data-node-id="
)

MISSING_PATTERNS=()
for pattern in "${REQUIRED_PATTERNS[@]}"; do
  if [[ "$RAW_JSX" != *"$pattern"* ]]; then
    MISSING_PATTERNS+=("$pattern")
  fi
done

if [ ${#MISSING_PATTERNS[@]} -gt 2 ]; then
  echo "❌ FAIL: Missing multiple required patterns: ${MISSING_PATTERNS[*]}"
  echo "   The raw_jsx must contain actual JSX code, not comments."
  exit 1
fi

# Check 5: No abstraction comments (forbidden patterns)
FORBIDDEN_PATTERNS=(
  "// Large JSX content"
  "// Section heading"
  "// Cards"
  "// Contains"
  "// Key styles:"
  "/* Abstracted */"
  "// ... (省略)"
  "// [省略]"
  "// 以下省略"
)

for pattern in "${FORBIDDEN_PATTERNS[@]}"; do
  if [[ "$RAW_JSX" == *"$pattern"* ]]; then
    echo "❌ FAIL: Contains abstraction comment: '$pattern'"
    echo "   raw_jsx must contain the ACTUAL JSX, not summarized comments."
    exit 1
  fi
done

# Check 6: Has actual HTML/JSX tags
TAG_COUNT=$(echo "$RAW_JSX" | grep -oE '<[a-zA-Z][^>]*>' | wc -l)
if [ "$TAG_COUNT" -lt 5 ]; then
  echo "❌ FAIL: Too few JSX tags ($TAG_COUNT found, min: 5)"
  echo "   raw_jsx should contain actual markup."
  exit 1
fi

echo "✅ PASS: raw_jsx validated for $NODE_ID ($LENGTH chars, $TAG_COUNT tags)"
exit 0

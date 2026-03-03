#!/bin/bash
# Automated Review - Mechanical code review
# Usage: bash automated-review.sh [scss|php|js|all]

set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
REVIEW_DIR="${PROJECT_ROOT}/.claude/reviews"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
REVIEW_TYPE="${1:-all}"

mkdir -p "$REVIEW_DIR"

ISSUES=()
ISSUE_COUNT=0

add_issue() {
  local type="$1" severity="$2" priority="$3" file="$4" rule="$5" desc="$6"
  ISSUE_COUNT=$((ISSUE_COUNT + 1))
  local id="${type}-$(printf '%03d' $ISSUE_COUNT)"
  ISSUES+=("{\"id\":\"${id}\",\"type\":\"${type}\",\"severity\":\"${severity}\",\"priority\":\"${priority}\",\"file\":\"${file}\",\"rule\":\"${rule}\",\"description\":\"${desc}\"}")
}

# SCSS Review
review_scss() {
  echo "📋 SCSS Review..."

  # 1. &- nest detection (BEM violation)
  while IFS=: read -r file line content; do
    [[ -n "$file" ]] && add_issue "scss" "safe" "high" "$file" "BEM: &- ネスト禁止" "Line ${line}: ${content}"
  done < <(grep -rn '&-[a-z]' "$PROJECT_ROOT/src/" --include="*.scss" 2>/dev/null | head -20 || true)

  # 2. Base style duplication
  while IFS=: read -r file line content; do
    [[ -n "$file" ]] && add_issue "scss" "safe" "medium" "$file" "Base style 重複" "Line ${line}: ${content}"
  done < <(grep -rn 'font-size:\s*rv(16)\|line-height:\s*1\.6\|font-family:\s*var(--font' "$PROJECT_ROOT/src/" --include="*.scss" 2>/dev/null | head -20 || true)

  # 3. Magic numbers (px values without rv/svw)
  while IFS=: read -r file line content; do
    [[ -n "$file" ]] && add_issue "scss" "safe" "medium" "$file" "マジックナンバー" "Line ${line}: ${content}"
  done < <(grep -rn '[0-9]\+px' "$PROJECT_ROOT/src/" --include="*.scss" | grep -v '//\|/\*\|1px\|0px' 2>/dev/null | head -20 || true)

  # 4. Deep nesting (4+ levels)
  while IFS=: read -r file line content; do
    [[ -n "$file" ]] && add_issue "scss" "risky" "medium" "$file" "深いネスト (4+)" "Line ${line}"
  done < <(grep -rn '^\s\{12,\}&' "$PROJECT_ROOT/src/" --include="*.scss" 2>/dev/null | head -10 || true)

  echo "  Found $(echo "${ISSUES[@]}" | grep -c '"type":"scss"' 2>/dev/null || echo 0) SCSS issues"
}

# PHP Review
review_php() {
  echo "📋 PHP Review..."

  # 1. the_field() usage (forbidden)
  while IFS=: read -r file line content; do
    [[ -n "$file" ]] && add_issue "php" "safe" "critical" "$file" "the_field() 使用禁止" "Line ${line}: get_field() を使用してください"
  done < <(grep -rn 'the_field(' "$PROJECT_ROOT/themes/" --include="*.php" 2>/dev/null | head -20 || true)

  # 2. Unescaped echo
  while IFS=: read -r file line content; do
    [[ -n "$file" ]] && add_issue "php" "risky" "critical" "$file" "エスケープ漏れ (XSS)" "Line ${line}: esc_html/esc_attr/esc_url を使用してください"
  done < <(grep -rn 'echo \$\|echo \$' "$PROJECT_ROOT/themes/" --include="*.php" | grep -v 'esc_\|wp_kses' 2>/dev/null | head -20 || true)

  # 3. var_dump / print_r
  while IFS=: read -r file line content; do
    [[ -n "$file" ]] && add_issue "php" "safe" "high" "$file" "デバッグコード残留" "Line ${line}: ${content}"
  done < <(grep -rn 'var_dump\|print_r\|error_log' "$PROJECT_ROOT/themes/" --include="*.php" 2>/dev/null | head -10 || true)

  echo "  Found $(echo "${ISSUES[@]}" | grep -c '"type":"php"' 2>/dev/null || echo 0) PHP issues"
}

# JS Review
review_js() {
  echo "📋 JS Review..."

  # 1. console.log
  while IFS=: read -r file line content; do
    [[ -n "$file" ]] && add_issue "js" "safe" "high" "$file" "console.log 残留" "Line ${line}"
  done < <(grep -rn 'console\.log\|console\.debug' "$PROJECT_ROOT/src/" --include="*.js" 2>/dev/null | head -10 || true)

  # 2. debugger
  while IFS=: read -r file line content; do
    [[ -n "$file" ]] && add_issue "js" "safe" "critical" "$file" "debugger 残留" "Line ${line}"
  done < <(grep -rn '^\s*debugger' "$PROJECT_ROOT/src/" --include="*.js" 2>/dev/null | head -10 || true)

  echo "  Found $(echo "${ISSUES[@]}" | grep -c '"type":"js"' 2>/dev/null || echo 0) JS issues"
}

# Run reviews
echo "🔍 Automated Review (${REVIEW_TYPE})"
echo "=============================="
[[ "$REVIEW_TYPE" == "all" || "$REVIEW_TYPE" == "scss" ]] && review_scss
[[ "$REVIEW_TYPE" == "all" || "$REVIEW_TYPE" == "php" ]] && review_php
[[ "$REVIEW_TYPE" == "all" || "$REVIEW_TYPE" == "js" ]] && review_js

# Count by severity
SAFE_COUNT=$(printf '%s\n' "${ISSUES[@]}" 2>/dev/null | grep -c '"severity":"safe"' || echo 0)
RISKY_COUNT=$(printf '%s\n' "${ISSUES[@]}" 2>/dev/null | grep -c '"severity":"risky"' || echo 0)
CRITICAL_COUNT=$(printf '%s\n' "${ISSUES[@]}" 2>/dev/null | grep -c '"priority":"critical"' || echo 0)

# Generate JSON
ISSUES_JSON=$(printf '%s\n' "${ISSUES[@]}" 2>/dev/null | paste -sd, - || echo "")
cat > "${REVIEW_DIR}/automated-${REVIEW_TYPE}-${TIMESTAMP}.json" << EOF
{
  "review_date": "$(date +%Y-%m-%d)",
  "type": "${REVIEW_TYPE}",
  "total": ${ISSUE_COUNT},
  "safe_count": ${SAFE_COUNT},
  "risky_count": ${RISKY_COUNT},
  "critical_count": ${CRITICAL_COUNT},
  "issues": [${ISSUES_JSON}],
  "verdict": "$([ $CRITICAL_COUNT -eq 0 ] && [ $ISSUE_COUNT -lt 5 ] && echo "PASS" || echo "NEEDS_REVIEW")"
}
EOF

echo ""
echo "=============================="
echo "📊 Total: ${ISSUE_COUNT} issues (Safe: ${SAFE_COUNT}, Risky: ${RISKY_COUNT}, Critical: ${CRITICAL_COUNT})"
echo "📄 Report: ${REVIEW_DIR}/automated-${REVIEW_TYPE}-${TIMESTAMP}.json"
echo ""
echo "💡 Next: Run /review for human-level review of design quality, naming, and architecture"

exit $([ $CRITICAL_COUNT -eq 0 ] && echo 0 || echo 1)

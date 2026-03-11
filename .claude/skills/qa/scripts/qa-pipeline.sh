#!/bin/bash
# QA Pipeline - Automated check & fix
# Usage: bash qa-pipeline.sh [--fix]

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
REPORT_DIR="${PROJECT_ROOT}/reports"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
REPORT_FILE="${REPORT_DIR}/qa-spec-${TIMESTAMP}.json"
FIX_MODE=false

# Parse args
[[ "${1:-}" == "--fix" ]] && FIX_MODE=true

mkdir -p "$REPORT_DIR"

echo "🔍 Phase 1: Mechanical Check"
echo "=============================="

ERRORS=0
WARNINGS=0
RESULTS=()

# 1. SCSS Lint
echo ""
echo "📋 [1/6] SCSS Lint..."
if SCSS_OUTPUT=$(cd "$PROJECT_ROOT" && npx stylelint "src/**/*.scss" 2>&1); then
  echo "  ✅ SCSS Lint: PASS"
  RESULTS+=('{"check": "scss-lint", "status": "pass", "issues": 0}')
else
  SCSS_ISSUES=$(echo "$SCSS_OUTPUT" | grep -c "✖\|⚠" || true)
  echo "  ❌ SCSS Lint: ${SCSS_ISSUES} issues"
  RESULTS+=("{\"check\": \"scss-lint\", \"status\": \"fail\", \"issues\": ${SCSS_ISSUES}}")
  ERRORS=$((ERRORS + SCSS_ISSUES))
fi

# 2. JS Lint
echo ""
echo "📋 [2/6] JS Lint..."
if JS_OUTPUT=$(cd "$PROJECT_ROOT" && npx eslint "src/**/*.js" 2>&1); then
  echo "  ✅ JS Lint: PASS"
  RESULTS+=('{"check": "js-lint", "status": "pass", "issues": 0}')
else
  JS_ISSUES=$(echo "$JS_OUTPUT" | grep -c "error\|warning" || true)
  echo "  ❌ JS Lint: ${JS_ISSUES} issues"
  RESULTS+=("{\"check\": \"js-lint\", \"status\": \"fail\", \"issues\": ${JS_ISSUES}}")
  ERRORS=$((ERRORS + JS_ISSUES))
fi

# 3. PHP Syntax Check
echo ""
echo "📋 [3/6] PHP Syntax..."
PHP_ERRORS=0
while IFS= read -r -d '' phpfile; do
  if ! php -l "$phpfile" > /dev/null 2>&1; then
    echo "  ❌ Syntax error: $phpfile"
    PHP_ERRORS=$((PHP_ERRORS + 1))
  fi
done < <(find "$PROJECT_ROOT/themes" -name "*.php" -print0 2>/dev/null || true)
if [[ $PHP_ERRORS -eq 0 ]]; then
  echo "  ✅ PHP Syntax: PASS"
  RESULTS+=('{"check": "php-syntax", "status": "pass", "issues": 0}')
else
  echo "  ❌ PHP Syntax: ${PHP_ERRORS} errors"
  RESULTS+=("{\"check\": \"php-syntax\", \"status\": \"fail\", \"issues\": ${PHP_ERRORS}}")
  ERRORS=$((ERRORS + PHP_ERRORS))
fi

# 4. Unused Code Detection
echo ""
echo "📋 [4/6] Unused Code Detection..."
if UNUSED_OUTPUT=$(cd "$PROJECT_ROOT" && node scripts/detect-unused-code.js 2>&1); then
  echo "  ✅ Unused Code: PASS"
  RESULTS+=('{"check": "unused-code", "status": "pass", "issues": 0}')
else
  UNUSED_ISSUES=$(echo "$UNUSED_OUTPUT" | grep -c "\[WARNING\]" || true)
  echo "  ⚠️  Unused Code: ${UNUSED_ISSUES} warnings"
  RESULTS+=("{\"check\": \"unused-code\", \"status\": \"warn\", \"issues\": ${UNUSED_ISSUES}}")
  WARNINGS=$((WARNINGS + UNUSED_ISSUES))
fi

# 5. Redundant Comments Detection
echo ""
echo "📋 [5/6] Redundant Comments Detection..."
if COMMENTS_OUTPUT=$(cd "$PROJECT_ROOT" && node scripts/detect-redundant-comments.js 2>&1); then
  echo "  ✅ Redundant Comments: PASS"
  RESULTS+=('{"check": "redundant-comments", "status": "pass", "issues": 0}')
else
  COMMENTS_ISSUES=$(echo "$COMMENTS_OUTPUT" | grep -c "\[WARNING\]" || true)
  echo "  ⚠️  Redundant Comments: ${COMMENTS_ISSUES} warnings"
  RESULTS+=("{\"check\": \"redundant-comments\", \"status\": \"warn\", \"issues\": ${COMMENTS_ISSUES}}")
  WARNINGS=$((WARNINGS + COMMENTS_ISSUES))
fi

# 6. Build Check
echo ""
echo "📋 [6/6] Build..."
if (cd "$PROJECT_ROOT" && npm run build > /dev/null 2>&1); then
  echo "  ✅ Build: PASS"
  RESULTS+=('{"check": "build", "status": "pass", "issues": 0}')
else
  echo "  ❌ Build: FAIL"
  RESULTS+=('{"check": "build", "status": "fail", "issues": 1}')
  ERRORS=$((ERRORS + 1))
fi

# Fix mode
if [[ "$FIX_MODE" == true && $ERRORS -gt 0 ]]; then
  echo ""
  echo "🔧 Phase 2: Auto-fix"
  echo "====================="

  echo "  Running stylelint --fix..."
  (cd "$PROJECT_ROOT" && npx stylelint "src/**/*.scss" --fix 2>&1) || true

  echo "  Running eslint --fix..."
  (cd "$PROJECT_ROOT" && npx eslint "src/**/*.js" --fix 2>&1) || true

  echo ""
  echo "🔍 Re-checking after fix..."
  # Re-check counts
  FIXED_SCSS=$(cd "$PROJECT_ROOT" && npx stylelint "src/**/*.scss" 2>&1 | grep -c "✖\|⚠" || echo "0")
  FIXED_JS=$(cd "$PROJECT_ROOT" && npx eslint "src/**/*.js" 2>&1 | grep -c "error\|warning" || echo "0")
  echo "  SCSS remaining: ${FIXED_SCSS}, JS remaining: ${FIXED_JS}"
fi

# Generate JSON report
RESULTS_JSON=$(printf '%s\n' "${RESULTS[@]}" | paste -sd, -)
cat > "$REPORT_FILE" << EOF
{
  "timestamp": "${TIMESTAMP}",
  "fix_mode": ${FIX_MODE},
  "total_errors": ${ERRORS},
  "total_warnings": ${WARNINGS},
  "checks": [${RESULTS_JSON}],
  "verdict": "$([ $ERRORS -eq 0 ] && echo "PASS" || echo "FAIL")"
}
EOF

echo ""
echo "=============================="
echo "📊 Result: $([ $ERRORS -eq 0 ] && echo "✅ PASS" || echo "❌ FAIL (${ERRORS} issues)")"
echo "📄 Report: ${REPORT_FILE}"

exit $([ $ERRORS -eq 0 ] && echo 0 || echo 1)

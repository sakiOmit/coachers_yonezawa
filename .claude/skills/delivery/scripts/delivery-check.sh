#!/bin/bash
# Delivery Check - Automated delivery quality verification
# Usage: bash delivery-check.sh [--url http://localhost:3000]

set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
REPORT_DIR="${PROJECT_ROOT}/reports"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
SITE_URL="${2:-http://localhost:3000}"

mkdir -p "$REPORT_DIR"

CHECKS=()
PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

add_check() {
  local name="$1" status="$2" detail="$3"
  CHECKS+=("{\"name\":\"${name}\",\"status\":\"${status}\",\"detail\":\"${detail}\"}")
  case "$status" in
    pass) PASS_COUNT=$((PASS_COUNT + 1)) ;;
    fail) FAIL_COUNT=$((FAIL_COUNT + 1)) ;;
    warn) WARN_COUNT=$((WARN_COUNT + 1)) ;;
  esac
}

echo "🔍 Delivery Quality Check"
echo "=============================="

# 1. Code Quality (lint)
echo ""
echo "📋 [1/6] Code Quality..."
if (cd "$PROJECT_ROOT" && npm run build > /dev/null 2>&1); then
  add_check "build" "pass" "Build succeeded"
  echo "  ✅ Build: PASS"
else
  add_check "build" "fail" "Build failed"
  echo "  ❌ Build: FAIL"
fi

SCSS_OK=true
if ! (cd "$PROJECT_ROOT" && npx stylelint "src/**/*.scss" > /dev/null 2>&1); then
  SCSS_OK=false
fi
if [[ "$SCSS_OK" == true ]]; then
  add_check "scss-lint" "pass" "No SCSS lint errors"
  echo "  ✅ SCSS Lint: PASS"
else
  add_check "scss-lint" "warn" "SCSS lint warnings found"
  echo "  ⚠️  SCSS Lint: WARNINGS"
fi

# 2. Image Verification
echo ""
echo "📋 [2/6] Image Check..."
LARGE_IMAGES=$(find "$PROJECT_ROOT/themes" "$PROJECT_ROOT/src" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.gif" \) -size +500k 2>/dev/null | wc -l || echo 0)
if [[ $LARGE_IMAGES -eq 0 ]]; then
  add_check "image-size" "pass" "No oversized images (>500KB)"
  echo "  ✅ Image Size: PASS"
else
  add_check "image-size" "warn" "${LARGE_IMAGES} images over 500KB"
  echo "  ⚠️  Image Size: ${LARGE_IMAGES} large images"
fi

# 3. SEO Basic Check
echo ""
echo "📋 [3/6] SEO Check..."
MISSING_ALT=$(grep -rn '<img' "$PROJECT_ROOT/themes/" --include="*.php" 2>/dev/null | grep -v 'alt=' | wc -l || echo 0)
if [[ $MISSING_ALT -eq 0 ]]; then
  add_check "img-alt" "pass" "All images have alt attributes"
  echo "  ✅ Image Alt: PASS"
else
  add_check "img-alt" "fail" "${MISSING_ALT} images missing alt attribute"
  echo "  ❌ Image Alt: ${MISSING_ALT} missing"
fi

# 4. Security Check
echo ""
echo "📋 [4/6] Security..."
THE_FIELD_COUNT=$(grep -rn 'the_field(' "$PROJECT_ROOT/themes/" --include="*.php" 2>/dev/null | wc -l || echo 0)
UNESCAPED=$(grep -rn 'echo \$' "$PROJECT_ROOT/themes/" --include="*.php" 2>/dev/null | grep -v 'esc_\|wp_kses' | wc -l || echo 0)
DEBUG_CODE=$(grep -rn 'var_dump\|print_r\|console\.log\|debugger' "$PROJECT_ROOT/themes/" "$PROJECT_ROOT/src/" --include="*.php" --include="*.js" 2>/dev/null | wc -l || echo 0)

if [[ $THE_FIELD_COUNT -eq 0 && $UNESCAPED -eq 0 ]]; then
  add_check "security" "pass" "No security issues found"
  echo "  ✅ Security: PASS"
else
  add_check "security" "fail" "the_field: ${THE_FIELD_COUNT}, unescaped: ${UNESCAPED}"
  echo "  ❌ Security: the_field(${THE_FIELD_COUNT}), unescaped echo(${UNESCAPED})"
fi

if [[ $DEBUG_CODE -eq 0 ]]; then
  add_check "debug-code" "pass" "No debug code found"
  echo "  ✅ Debug Code: PASS"
else
  add_check "debug-code" "warn" "${DEBUG_CODE} debug statements found"
  echo "  ⚠️  Debug Code: ${DEBUG_CODE} statements"
fi

# 5. File Structure
echo ""
echo "📋 [5/6] Structure..."
EMPTY_FILES=$(find "$PROJECT_ROOT/themes" "$PROJECT_ROOT/src" -type f -empty 2>/dev/null | wc -l || echo 0)
if [[ $EMPTY_FILES -eq 0 ]]; then
  add_check "empty-files" "pass" "No empty files"
  echo "  ✅ Empty Files: PASS"
else
  add_check "empty-files" "warn" "${EMPTY_FILES} empty files found"
  echo "  ⚠️  Empty Files: ${EMPTY_FILES}"
fi

# 6. PHP Syntax
echo ""
echo "📋 [6/6] PHP Syntax..."
PHP_ERRORS=0
while IFS= read -r -d '' f; do
  if ! php -l "$f" > /dev/null 2>&1; then
    PHP_ERRORS=$((PHP_ERRORS + 1))
  fi
done < <(find "$PROJECT_ROOT/themes" -name "*.php" -print0 2>/dev/null || true)
if [[ $PHP_ERRORS -eq 0 ]]; then
  add_check "php-syntax" "pass" "All PHP files valid"
  echo "  ✅ PHP Syntax: PASS"
else
  add_check "php-syntax" "fail" "${PHP_ERRORS} PHP syntax errors"
  echo "  ❌ PHP Syntax: ${PHP_ERRORS} errors"
fi

# Generate JSON report
CHECKS_JSON=$(printf '%s\n' "${CHECKS[@]}" | paste -sd, -)
VERDICT="READY"
[[ $FAIL_COUNT -gt 0 ]] && VERDICT="NOT_READY"
[[ $WARN_COUNT -gt 2 ]] && VERDICT="NEEDS_REVIEW"

cat > "${REPORT_DIR}/delivery-auto-${TIMESTAMP}.json" << EOF
{
  "timestamp": "${TIMESTAMP}",
  "pass": ${PASS_COUNT},
  "fail": ${FAIL_COUNT},
  "warn": ${WARN_COUNT},
  "checks": [${CHECKS_JSON}],
  "verdict": "${VERDICT}",
  "manual_check_required": [
    "クロスブラウザテスト (Chrome, Safari, Firefox, Edge)",
    "フォーム送信テスト",
    "アニメーション動作確認",
    "コンテンツ最終確認",
    "レスポンシブ表示確認 (375px, 768px, 1440px)"
  ]
}
EOF

echo ""
echo "=============================="
echo "📊 Result: Pass(${PASS_COUNT}) Fail(${FAIL_COUNT}) Warn(${WARN_COUNT}) → ${VERDICT}"
echo "📄 Report: ${REPORT_DIR}/delivery-auto-${TIMESTAMP}.json"
echo ""
echo "📋 Manual check items are listed in the report"

exit $([ $FAIL_COUNT -eq 0 ] && echo 0 || echo 1)

#!/bin/bash
# =============================================================================
# quality-check.sh
#
# 実装後の品質チェック（Step 8 で使用）
#
# Usage: quality-check.sh <scss_file> <php_file>
# =============================================================================

set -e

SCSS_FILE=$1
PHP_FILE=$2

if [ -z "$SCSS_FILE" ] || [ -z "$PHP_FILE" ]; then
  echo "Usage: quality-check.sh <scss_file> <php_file>"
  exit 1
fi

ERRORS=0
WARNINGS=0

echo "=== Quality Check ==="
echo ""

# ----- SCSS Checks -----
echo "--- SCSS Checks: $SCSS_FILE ---"

if [ ! -f "$SCSS_FILE" ]; then
  echo "❌ FAIL: SCSS file not found: $SCSS_FILE"
  ERRORS=$((ERRORS + 1))
else
  # Check 1: BEM naming (kebab-case)
  CAMEL_CASE=$(grep -oE '\.[a-z]+[A-Z][a-zA-Z]*' "$SCSS_FILE" 2>/dev/null || true)
  if [ -n "$CAMEL_CASE" ]; then
    echo "❌ FAIL: camelCase found in class names (use kebab-case):"
    echo "$CAMEL_CASE" | head -5
    ERRORS=$((ERRORS + 1))
  else
    echo "✅ BEM naming: kebab-case"
  fi

  # Check 2: &__ nesting
  WRONG_NESTING=$(grep -E '^\s+&-[a-z]' "$SCSS_FILE" 2>/dev/null || true)
  if [ -n "$WRONG_NESTING" ]; then
    echo "⚠️ WARN: &- nesting found (prefer &__ for BEM elements)"
    WARNINGS=$((WARNINGS + 1))
  else
    echo "✅ BEM nesting: &__ style"
  fi

  # Check 3: @include hover
  DIRECT_HOVER=$(grep -E '&:hover\s*\{' "$SCSS_FILE" 2>/dev/null || true)
  if [ -n "$DIRECT_HOVER" ]; then
    echo "❌ FAIL: Direct :hover found (use @include hover)"
    ERRORS=$((ERRORS + 1))
  else
    echo "✅ Hover: @include hover"
  fi

  # Check 4: Container rule
  CONTAINER_VIOLATION=$(grep -A5 'container' "$SCSS_FILE" 2>/dev/null | grep -E '^\s+(display|flex|padding|margin)' || true)
  if [ -n "$CONTAINER_VIOLATION" ]; then
    echo "⚠️ WARN: Container class may have extra properties"
    WARNINGS=$((WARNINGS + 1))
  fi

  # Check 5: rv() / svw() usage
  RV_COUNT=$(grep -oE 'rv\([0-9]+\)' "$SCSS_FILE" 2>/dev/null | wc -l || echo "0")
  SVW_COUNT=$(grep -oE 'svw\([0-9]+\)' "$SCSS_FILE" 2>/dev/null | wc -l || echo "0")
  echo "✅ Size functions: rv()=$RV_COUNT, svw()=$SVW_COUNT"
fi

echo ""

# ----- PHP Checks -----
echo "--- PHP Checks: $PHP_FILE ---"

if [ ! -f "$PHP_FILE" ]; then
  echo "❌ FAIL: PHP file not found: $PHP_FILE"
  ERRORS=$((ERRORS + 1))
else
  # Check 1: Template Name comment
  TEMPLATE_NAME=$(grep -E 'Template Name:' "$PHP_FILE" 2>/dev/null || true)
  if [ -z "$TEMPLATE_NAME" ]; then
    echo "❌ FAIL: Missing 'Template Name:' comment"
    ERRORS=$((ERRORS + 1))
  else
    echo "✅ Template Name: defined"
  fi

  # Check 2: render_responsive_image usage
  DIRECT_IMG=$(grep -E '<img\s' "$PHP_FILE" 2>/dev/null | grep -v 'render_responsive_image' || true)
  if [ -n "$DIRECT_IMG" ]; then
    echo "⚠️ WARN: Direct <img> tag found (prefer render_responsive_image())"
    WARNINGS=$((WARNINGS + 1))
  else
    echo "✅ Images: using render_responsive_image()"
  fi

  # Check 3: Output escaping
  UNESCAPED=$(grep -E 'echo\s+\$|echo\s+get_field' "$PHP_FILE" 2>/dev/null | grep -v 'esc_' | grep -v 'wp_kses' || true)
  if [ -n "$UNESCAPED" ]; then
    echo "⚠️ WARN: Possible unescaped output found"
    WARNINGS=$((WARNINGS + 1))
  else
    echo "✅ Escaping: esc_html/esc_url/wp_kses_post"
  fi

  # Check 4: ACF field null check
  ACF_WITHOUT_CHECK=$(grep -E 'get_field\(' "$PHP_FILE" 2>/dev/null | grep -v 'if\s*(' | grep -v '\$.*=' || true)
  if [ -n "$ACF_WITHOUT_CHECK" ]; then
    echo "⚠️ WARN: ACF fields may lack null checks"
    WARNINGS=$((WARNINGS + 1))
  fi

  # Check 5: Debug code
  DEBUG_CODE=$(grep -E 'var_dump|print_r|dd\(' "$PHP_FILE" 2>/dev/null || true)
  if [ -n "$DEBUG_CODE" ]; then
    echo "❌ FAIL: Debug code found"
    ERRORS=$((ERRORS + 1))
  fi
fi

echo ""

# ----- Summary -----
echo "=== Summary ==="
if [ $ERRORS -gt 0 ]; then
  echo "❌ FAIL: $ERRORS error(s), $WARNINGS warning(s)"
  exit 1
elif [ $WARNINGS -gt 0 ]; then
  echo "⚠️ PASS with warnings: $WARNINGS warning(s)"
  exit 0
else
  echo "✅ PASS: All checks passed"
  exit 0
fi

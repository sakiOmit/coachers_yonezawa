#!/bin/bash
# =============================================================================
# quality-check.sh
#
# 実装後の品質チェック（Step 8 で使用）
#
# Usage: quality-check.sh <scss_file> <astro_file>
# =============================================================================

set -e

SCSS_FILE=$1
ASTRO_FILE=$2

if [ -z "$SCSS_FILE" ] || [ -z "$ASTRO_FILE" ]; then
  echo "Usage: quality-check.sh <scss_file> <astro_file>"
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

# ----- Astro Checks -----
echo "--- Astro Checks: $ASTRO_FILE ---"

if [ ! -f "$ASTRO_FILE" ]; then
  echo "❌ FAIL: Astro file not found: $ASTRO_FILE"
  ERRORS=$((ERRORS + 1))
else
  # Check 1: Direct <img> tag (should use <ResponsiveImage />)
  DIRECT_IMG=$(grep -n '<img\s' "$ASTRO_FILE" 2>/dev/null | grep -v 'ResponsiveImage' || true)
  if [ -n "$DIRECT_IMG" ]; then
    echo "❌ FAIL: Direct <img> tag found (use <ResponsiveImage /> component):"
    echo "$DIRECT_IMG" | head -5
    ERRORS=$((ERRORS + 1))
  else
    echo "✅ Images: using <ResponsiveImage />"
  fi

  # Check 2: Scoped <style> block (forbidden in .astro files)
  SCOPED_STYLE=$(grep -n '<style' "$ASTRO_FILE" 2>/dev/null || true)
  if [ -n "$SCOPED_STYLE" ]; then
    echo "❌ FAIL: <style> block found in .astro file (use src/scss/ instead):"
    echo "$SCOPED_STYLE" | head -3
    ERRORS=$((ERRORS + 1))
  else
    echo "✅ No scoped <style> blocks"
  fi

  # Check 3: SCSS import in .astro file (forbidden)
  SCSS_IMPORT=$(grep -n 'import.*\.scss' "$ASTRO_FILE" 2>/dev/null || true)
  if [ -n "$SCSS_IMPORT" ]; then
    echo "❌ FAIL: SCSS import found in .astro file (use src/css/ entry point instead):"
    echo "$SCSS_IMPORT" | head -3
    ERRORS=$((ERRORS + 1))
  else
    echo "✅ No SCSS imports in .astro"
  fi

  # Check 4: JS import in .astro file (forbidden)
  # Exclude Astro component imports (.astro), data imports (.json), and lib imports
  JS_IMPORT=$(grep -n 'import.*\.js' "$ASTRO_FILE" 2>/dev/null | grep -v '\.json' || true)
  if [ -n "$JS_IMPORT" ]; then
    echo "❌ FAIL: JS import found in .astro file (use src/js/ entry point instead):"
    echo "$JS_IMPORT" | head -3
    ERRORS=$((ERRORS + 1))
  else
    echo "✅ No JS imports in .astro"
  fi

  # Check 5: Inline <script> block (forbidden)
  INLINE_SCRIPT=$(grep -n '<script>' "$ASTRO_FILE" 2>/dev/null | grep -v 'is:inline' || true)
  INLINE_SCRIPT2=$(grep -n '<script ' "$ASTRO_FILE" 2>/dev/null | grep -v 'src=' | grep -v 'is:inline' || true)
  if [ -n "$INLINE_SCRIPT" ] || [ -n "$INLINE_SCRIPT2" ]; then
    echo "⚠️ WARN: Inline <script> block found (use src/js/ instead)"
    WARNINGS=$((WARNINGS + 1))
  else
    echo "✅ No inline <script> blocks"
  fi

  # Check 6: Debug code
  DEBUG_CODE=$(grep -n 'console\.log\|console\.warn\|console\.error\|debugger' "$ASTRO_FILE" 2>/dev/null || true)
  if [ -n "$DEBUG_CODE" ]; then
    echo "❌ FAIL: Debug code found:"
    echo "$DEBUG_CODE" | head -3
    ERRORS=$((ERRORS + 1))
  fi
fi

echo ""

# ----- Astro Section Components Check -----
# Also check section component files in the same directory
ASTRO_DIR=$(dirname "$ASTRO_FILE")
ASTRO_BASENAME=$(basename "$ASTRO_FILE" .astro)

# Check for section components if they exist
SECTIONS_DIR="astro/src/components/sections/$ASTRO_BASENAME"
if [ -d "$SECTIONS_DIR" ]; then
  echo "--- Section Components: $SECTIONS_DIR ---"

  for SECTION_FILE in "$SECTIONS_DIR"/*.astro; do
    [ -f "$SECTION_FILE" ] || continue

    SECTION_NAME=$(basename "$SECTION_FILE")

    # Check <img> in section components
    SECTION_IMG=$(grep -n '<img\s' "$SECTION_FILE" 2>/dev/null | grep -v 'ResponsiveImage' || true)
    if [ -n "$SECTION_IMG" ]; then
      echo "❌ FAIL: Direct <img> in $SECTION_NAME"
      ERRORS=$((ERRORS + 1))
    fi

    # Check <style> in section components
    SECTION_STYLE=$(grep -n '<style' "$SECTION_FILE" 2>/dev/null || true)
    if [ -n "$SECTION_STYLE" ]; then
      echo "❌ FAIL: <style> block in $SECTION_NAME"
      ERRORS=$((ERRORS + 1))
    fi

    # Check SCSS/JS imports in section components
    SECTION_SCSS=$(grep -n 'import.*\.scss' "$SECTION_FILE" 2>/dev/null || true)
    if [ -n "$SECTION_SCSS" ]; then
      echo "❌ FAIL: SCSS import in $SECTION_NAME"
      ERRORS=$((ERRORS + 1))
    fi
  done

  echo "✅ Section components checked"
  echo ""
fi

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

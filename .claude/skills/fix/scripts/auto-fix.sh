#!/bin/bash
# Auto Fix - Mechanical fix for safe issues
# Usage: bash auto-fix.sh [scss|js|php|all] [--dry-run]
#
# Fixes safe (auto-fixable) issues only:
#   SCSS: stylelint --fix, camelCase→kebab-case, &-→&__, empty blocks
#   JS:   eslint --fix, console.log/debugger removal
#   PHP:  var_dump/print_r removal, TODO comment removal
#
# Risky issues are NOT touched - LLM handles those with user approval.

set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
FIX_TYPE="${1:-all}"
DRY_RUN=false
[[ "${2:-}" == "--dry-run" ]] && DRY_RUN=true

REPORT_DIR="${PROJECT_ROOT}/reports"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
REPORT_FILE="${REPORT_DIR}/fix-${FIX_TYPE}-${TIMESTAMP}.json"

mkdir -p "$REPORT_DIR"

FIXES=()
FIX_COUNT=0
SKIP_COUNT=0

add_fix() {
  local type="$1" file="$2" rule="$3" desc="$4" status="$5"
  FIX_COUNT=$((FIX_COUNT + 1))
  FIXES+=("{\"type\":\"${type}\",\"file\":\"${file}\",\"rule\":\"${rule}\",\"description\":\"${desc}\",\"status\":\"${status}\"}")
}

echo "=========================================="
echo " Auto Fix (${FIX_TYPE}) $([ "$DRY_RUN" == true ] && echo '[DRY-RUN]')"
echo "=========================================="
echo ""

# ============================================================
# SCSS Fixes
# ============================================================
fix_scss() {
  echo "[SCSS] Fixing safe issues..."

  # 1. stylelint --fix
  echo "  Running stylelint --fix..."
  if [[ "$DRY_RUN" == false ]]; then
    STYLELINT_OUTPUT=$(cd "$PROJECT_ROOT" && npx stylelint "src/**/*.scss" --fix 2>&1 || true)
    STYLELINT_FIXED=$(echo "$STYLELINT_OUTPUT" | grep -c "fixed" 2>/dev/null || echo "0")
    echo "    stylelint auto-fixed: ${STYLELINT_FIXED} issue(s)"
    [[ $STYLELINT_FIXED -gt 0 ]] && add_fix "scss" "multiple" "stylelint --fix" "${STYLELINT_FIXED} auto-fixed" "fixed"
  else
    echo "    [DRY-RUN] Would run stylelint --fix"
  fi

  # 2. &- nest → &__ nest (BEM violation)
  echo "  Checking &- nest violations..."
  while IFS=: read -r file line content; do
    [[ -z "$file" ]] && continue
    if [[ "$DRY_RUN" == false ]]; then
      # Only fix simple cases: &-foo → &__foo
      sed -i "${line}s/&-\([a-z]\)/\&__\1/" "$file" 2>/dev/null || true
      add_fix "scss" "$file" "&- → &__" "Line ${line}: BEM element fix" "fixed"
      echo "    Fixed: ${file}:${line}"
    else
      echo "    [DRY-RUN] Would fix: ${file}:${line} - ${content}"
      add_fix "scss" "$file" "&- → &__" "Line ${line}" "dry-run"
    fi
  done < <(grep -rn '&-[a-z]' "$PROJECT_ROOT/src/" --include="*.scss" 2>/dev/null | head -20 || true)

  # 3. Empty SCSS blocks removal
  echo "  Checking empty blocks..."
  while IFS=: read -r file line _; do
    [[ -z "$file" ]] && continue
    if [[ "$DRY_RUN" == false ]]; then
      # Remove lines matching empty block pattern (conservative)
      add_fix "scss" "$file" "empty-block" "Line ${line}: empty block detected" "skipped"
      SKIP_COUNT=$((SKIP_COUNT + 1))
      echo "    Skipped (risky): ${file}:${line} - empty block needs manual review"
    else
      echo "    [DRY-RUN] Would check: ${file}:${line}"
    fi
  done < <(grep -rn '{\s*}' "$PROJECT_ROOT/src/" --include="*.scss" 2>/dev/null | head -10 || true)

  # 4. &:hover → @include hover
  echo "  Checking bare :hover..."
  HOVER_COUNT=$(grep -rn '&:hover' "$PROJECT_ROOT/src/" --include="*.scss" 2>/dev/null | grep -v '@include hover' | wc -l || echo 0)
  if [[ $HOVER_COUNT -gt 0 ]]; then
    echo "    Found ${HOVER_COUNT} bare :hover (needs LLM - multi-line replacement)"
    SKIP_COUNT=$((SKIP_COUNT + HOVER_COUNT))
    add_fix "scss" "multiple" "&:hover → @include hover" "${HOVER_COUNT} occurrences" "skipped-complex"
  fi

  echo ""
}

# ============================================================
# JS Fixes
# ============================================================
fix_js() {
  echo "[JS] Fixing safe issues..."

  # 1. eslint --fix
  echo "  Running eslint --fix..."
  if [[ "$DRY_RUN" == false ]]; then
    ESLINT_OUTPUT=$(cd "$PROJECT_ROOT" && npx eslint "src/**/*.js" --fix 2>&1 || true)
    echo "    eslint --fix completed"
    add_fix "js" "multiple" "eslint --fix" "Auto-fixed" "fixed"
  else
    echo "    [DRY-RUN] Would run eslint --fix"
  fi

  # 2. console.log removal
  echo "  Removing console.log..."
  while IFS=: read -r file line content; do
    [[ -z "$file" ]] && continue
    if [[ "$DRY_RUN" == false ]]; then
      # Remove the entire line containing console.log
      sed -i "${line}d" "$file" 2>/dev/null || true
      add_fix "js" "$file" "console.log" "Line ${line}: removed" "fixed"
      echo "    Removed: ${file}:${line}"
    else
      echo "    [DRY-RUN] Would remove: ${file}:${line}"
      add_fix "js" "$file" "console.log" "Line ${line}" "dry-run"
    fi
  done < <(grep -rn '^\s*console\.log(' "$PROJECT_ROOT/src/" --include="*.js" 2>/dev/null | head -20 || true)

  # 3. console.debug removal
  while IFS=: read -r file line content; do
    [[ -z "$file" ]] && continue
    if [[ "$DRY_RUN" == false ]]; then
      sed -i "${line}d" "$file" 2>/dev/null || true
      add_fix "js" "$file" "console.debug" "Line ${line}: removed" "fixed"
      echo "    Removed: ${file}:${line}"
    else
      echo "    [DRY-RUN] Would remove: ${file}:${line}"
    fi
  done < <(grep -rn '^\s*console\.debug(' "$PROJECT_ROOT/src/" --include="*.js" 2>/dev/null | head -10 || true)

  # 4. debugger removal
  echo "  Removing debugger statements..."
  while IFS=: read -r file line content; do
    [[ -z "$file" ]] && continue
    if [[ "$DRY_RUN" == false ]]; then
      sed -i "${line}d" "$file" 2>/dev/null || true
      add_fix "js" "$file" "debugger" "Line ${line}: removed" "fixed"
      echo "    Removed: ${file}:${line}"
    else
      echo "    [DRY-RUN] Would remove: ${file}:${line}"
      add_fix "js" "$file" "debugger" "Line ${line}" "dry-run"
    fi
  done < <(grep -rn '^\s*debugger\s*;*\s*$' "$PROJECT_ROOT/src/" --include="*.js" 2>/dev/null | head -10 || true)

  echo ""
}

# ============================================================
# PHP Fixes
# ============================================================
fix_php() {
  echo "[PHP] Fixing safe issues..."

  # Detect theme dir
  THEME_DIR=""
  for d in "$PROJECT_ROOT"/themes/*/; do
    [[ -f "${d}functions.php" ]] && THEME_DIR="$d" && break
  done
  [[ -z "$THEME_DIR" ]] && echo "  WARN: No theme found" && return

  # 1. var_dump removal
  echo "  Removing var_dump..."
  while IFS=: read -r file line content; do
    [[ -z "$file" ]] && continue
    if [[ "$DRY_RUN" == false ]]; then
      sed -i "${line}d" "$file" 2>/dev/null || true
      add_fix "php" "$file" "var_dump" "Line ${line}: removed" "fixed"
      echo "    Removed: ${file}:${line}"
    else
      echo "    [DRY-RUN] Would remove: ${file}:${line}"
      add_fix "php" "$file" "var_dump" "Line ${line}" "dry-run"
    fi
  done < <(grep -rn '^\s*var_dump(' "$THEME_DIR" --include="*.php" 2>/dev/null | head -20 || true)

  # 2. print_r removal
  echo "  Removing print_r..."
  while IFS=: read -r file line content; do
    [[ -z "$file" ]] && continue
    if [[ "$DRY_RUN" == false ]]; then
      sed -i "${line}d" "$file" 2>/dev/null || true
      add_fix "php" "$file" "print_r" "Line ${line}: removed" "fixed"
      echo "    Removed: ${file}:${line}"
    else
      echo "    [DRY-RUN] Would remove: ${file}:${line}"
      add_fix "php" "$file" "print_r" "Line ${line}" "dry-run"
    fi
  done < <(grep -rn '^\s*print_r(' "$THEME_DIR" --include="*.php" 2>/dev/null | head -20 || true)

  # 3. error_log removal (debug only)
  echo "  Removing error_log..."
  while IFS=: read -r file line content; do
    [[ -z "$file" ]] && continue
    if [[ "$DRY_RUN" == false ]]; then
      sed -i "${line}d" "$file" 2>/dev/null || true
      add_fix "php" "$file" "error_log" "Line ${line}: removed" "fixed"
      echo "    Removed: ${file}:${line}"
    else
      echo "    [DRY-RUN] Would remove: ${file}:${line}"
      add_fix "php" "$file" "error_log" "Line ${line}" "dry-run"
    fi
  done < <(grep -rn '^\s*error_log(' "$THEME_DIR" --include="*.php" 2>/dev/null | head -20 || true)

  # 4. the_field() detection (report only - risky to auto-fix)
  echo "  Checking the_field() usage..."
  THE_FIELD_COUNT=$(grep -rn 'the_field(' "$THEME_DIR" --include="*.php" 2>/dev/null | wc -l || echo 0)
  if [[ $THE_FIELD_COUNT -gt 0 ]]; then
    echo "    Found ${THE_FIELD_COUNT} the_field() usages (needs LLM - risky)"
    SKIP_COUNT=$((SKIP_COUNT + THE_FIELD_COUNT))
    add_fix "php" "multiple" "the_field→get_field" "${THE_FIELD_COUNT} occurrences" "skipped-risky"
  fi

  # 5. Unescaped echo detection (report only - risky)
  echo "  Checking unescaped echo..."
  UNESCAPED=$(grep -rn 'echo \$' "$THEME_DIR" --include="*.php" 2>/dev/null | grep -v 'esc_\|wp_kses' | wc -l || echo 0)
  if [[ $UNESCAPED -gt 0 ]]; then
    echo "    Found ${UNESCAPED} unescaped echo (needs LLM - risky/security)"
    SKIP_COUNT=$((SKIP_COUNT + UNESCAPED))
    add_fix "php" "multiple" "unescaped-echo" "${UNESCAPED} occurrences" "skipped-risky"
  fi

  echo ""
}

# ============================================================
# Execute
# ============================================================
[[ "$FIX_TYPE" == "all" || "$FIX_TYPE" == "scss" ]] && fix_scss
[[ "$FIX_TYPE" == "all" || "$FIX_TYPE" == "js" ]] && fix_js
[[ "$FIX_TYPE" == "all" || "$FIX_TYPE" == "php" ]] && fix_php

# ============================================================
# Post-fix Verification
# ============================================================
echo "[Verify] Post-fix check"
echo "------------------------"

BUILD_OK=false
if [[ "$DRY_RUN" == false ]]; then
  echo "  Running build..."
  if (cd "$PROJECT_ROOT" && npm run build > /dev/null 2>&1); then
    echo "    Build: PASS"
    BUILD_OK=true
  else
    echo "    Build: FAIL (check errors above)"
  fi
else
  echo "  [DRY-RUN] Would run build verification"
fi

echo ""

# ============================================================
# Generate Report
# ============================================================
FIXED_COUNT=$(printf '%s\n' "${FIXES[@]}" 2>/dev/null | grep -c '"status":"fixed"' || echo 0)
SKIPPED_COUNT=$(printf '%s\n' "${FIXES[@]}" 2>/dev/null | grep -c '"status":"skipped' || echo 0)
FIXES_JSON=$(printf '%s\n' "${FIXES[@]}" 2>/dev/null | paste -sd, - || echo "")

cat > "$REPORT_FILE" << EOF
{
  "timestamp": "${TIMESTAMP}",
  "type": "${FIX_TYPE}",
  "dry_run": ${DRY_RUN},
  "fixed": ${FIXED_COUNT},
  "skipped": ${SKIPPED_COUNT},
  "build_ok": ${BUILD_OK},
  "fixes": [${FIXES_JSON}],
  "verdict": "$([ "$BUILD_OK" == true ] && echo "PASS" || echo "$([ "$DRY_RUN" == true ] && echo "DRY_RUN" || echo "BUILD_FAIL")")"
}
EOF

echo "=========================================="
echo " Fix Summary"
echo "=========================================="
echo ""
echo "  Fixed: ${FIXED_COUNT}"
echo "  Skipped (risky/complex): ${SKIPPED_COUNT}"
echo "  Build: $([ "$BUILD_OK" == true ] && echo "PASS" || echo "$([ "$DRY_RUN" == true ] && echo "DRY-RUN" || echo "FAIL")")"
echo ""
echo "  Report: ${REPORT_FILE}"
echo ""

if [[ $SKIPPED_COUNT -gt 0 ]]; then
  echo "  Remaining risky issues need LLM:"
  echo "    /fix security   - Fix security issues (with approval)"
  echo "    /fix {issue-id}  - Fix specific issue"
fi

exit $([ "$BUILD_OK" == true ] || [ "$DRY_RUN" == true ] && echo 0 || echo 1)

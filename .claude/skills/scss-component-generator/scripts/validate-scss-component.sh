#!/bin/bash
set -euo pipefail

# validate-scss-component.sh
# Purpose: Validate BEM/FLOCSS compliance of SCSS file
# Input: Path to SCSS file
# Output: Validation results (text)
# Exit: 0=PASS, 1=FAIL

FILE="${1:-}"
ERRORS=0

if [[ -z "$FILE" || ! -f "$FILE" ]]; then
  echo "Error: SCSS file path required" >&2
  echo "Usage: $0 <scss-file>" >&2
  exit 1
fi

echo "Validating: ${FILE}"
echo ""

# --- Check 1: FLOCSS prefix ---
FILENAME=$(basename "$FILE" .scss | sed 's/^_//')
if [[ ! "$FILENAME" =~ ^(c|p|l|u)- ]]; then
  echo "FAIL: Missing FLOCSS prefix (c-/p-/l-/u-) in filename: ${FILENAME}"
  ((ERRORS++))
else
  echo "PASS: FLOCSS prefix OK"
fi

# --- Check 2: kebab-case only ---
if grep -qP '\.[a-z]+[A-Z]' "$FILE" 2>/dev/null; then
  echo "FAIL: camelCase detected in class names"
  grep -nP '\.[a-z]+[A-Z]' "$FILE" | head -5
  ((ERRORS++))
else
  echo "PASS: kebab-case naming OK"
fi

# --- Check 3: &__ nesting (not &-) ---
if grep -qP '^\s+&-[a-z]' "$FILE" 2>/dev/null; then
  echo "FAIL: &- nesting detected (should use &__)"
  grep -nP '^\s+&-[a-z]' "$FILE" | head -5
  ((ERRORS++))
else
  echo "PASS: BEM nesting OK (no &- violations)"
fi

# --- Check 4: container rule ---
if grep -qP '__container' "$FILE" 2>/dev/null; then
  # Check if container blocks have only @include container
  CONTAINER_VIOLATIONS=$(awk '
    /__container\s*\{/ { in_container=1; brace_count=1; next }
    in_container {
      brace_count += gsub(/\{/, "{")
      brace_count -= gsub(/\}/, "}")
      if (brace_count <= 0) { in_container=0; next }
      if (/^\s*@include container/ || /^\s*$/ || /^\s*\/\//) next
      if (/[a-z]/) { print NR": "$0; violations++ }
    }
    END { exit (violations > 0) ? 1 : 0 }
  ' "$FILE" 2>/dev/null)

  if [[ -n "$CONTAINER_VIOLATIONS" ]]; then
    echo "FAIL: Container rule violation (only @include container() allowed)"
    echo "$CONTAINER_VIOLATIONS" | head -3
    ((ERRORS++))
  else
    echo "PASS: Container rule OK"
  fi
fi

# --- Check 5: :hover direct usage ---
if grep -qP '&:hover\s*\{' "$FILE" 2>/dev/null; then
  echo "FAIL: Direct :hover detected (use @include hover)"
  grep -nP '&:hover\s*\{' "$FILE" | head -3
  ((ERRORS++))
else
  echo "PASS: Hover rule OK"
fi

# --- Check 6: Nesting depth ---
MAX_DEPTH=$(awk '
  BEGIN { max=0; depth=0 }
  /\{/ { depth++; if(depth>max) max=depth }
  /\}/ { depth-- }
  END { print max }
' "$FILE")

if (( MAX_DEPTH > 4 )); then
  echo "FAIL: Nesting too deep (${MAX_DEPTH} levels, max 4)"
  ((ERRORS++))
else
  echo "PASS: Nesting depth OK (${MAX_DEPTH} levels)"
fi

echo ""
if (( ERRORS > 0 )); then
  echo "Result: FAIL (${ERRORS} issues)"
  exit 1
else
  echo "Result: PASS"
  exit 0
fi

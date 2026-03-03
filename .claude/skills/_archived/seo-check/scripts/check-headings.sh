#!/bin/bash
# Heading Structure Check Script
# Usage: bash check-headings.sh {file}
# Exit 0: PASS, Exit 1: FAIL

FILE="$1"
ERRORS=0

if [ ! -f "$FILE" ]; then
  echo "❌ File not found: $FILE"
  exit 1
fi

echo "🔍 Checking heading structure: $FILE"
echo ""

# Extract theme directory from file path
THEME_DIR=$(dirname "$FILE" | sed 's|/pages.*||')

# Create temporary file for merged content
TEMP_FILE=$(mktemp)
trap "rm -f $TEMP_FILE" EXIT

# Copy main file
cat "$FILE" > "$TEMP_FILE"

# Find and append template parts
grep -oP "get_template_part\(['\"]([^'\"]+)" "$FILE" | while read -r line; do
  PART_PATH=$(echo "$line" | sed "s/get_template_part(['\"]//")
  FULL_PATH="$THEME_DIR/$PART_PATH.php"

  if [ -f "$FULL_PATH" ]; then
    echo "  → Including: $PART_PATH.php" >&2
    cat "$FULL_PATH" >> "$TEMP_FILE"
  fi
done

echo ""

# Check 1: h1 count
H1_COUNT=$(grep -o '<h1[^>]*>' "$TEMP_FILE" | wc -l)
H1_COUNT=$(echo "$H1_COUNT" | tr -d '[:space:]')

if [ "$H1_COUNT" -eq 0 ]; then
  echo "❌ No h1 found (required: exactly 1 per page)"
  ERRORS=$((ERRORS + 1))
elif [ "$H1_COUNT" -eq 1 ]; then
  echo "✓ h1 count: 1"
else
  echo "❌ Multiple h1 found: $H1_COUNT (expected: 1)"
  ERRORS=$((ERRORS + 1))
fi

# Check 2: Empty headings
EMPTY_HEADINGS=$(grep -E '<h[1-6][^>]*>\s*</h[1-6]>' "$TEMP_FILE" | wc -l)
EMPTY_HEADINGS=$(echo "$EMPTY_HEADINGS" | tr -d '[:space:]')

if [ "$EMPTY_HEADINGS" -gt 0 ]; then
  echo "❌ Empty headings found: $EMPTY_HEADINGS"
  ERRORS=$((ERRORS + EMPTY_HEADINGS))
else
  echo "✓ No empty headings"
fi

# Check 3: Heading hierarchy
# Extract all heading levels from actual HTML tags
LEVELS=$(grep -o '<h[1-6][^>]*>' "$TEMP_FILE" | sed -E 's/<h([1-6]).*/\1/' | tr '\n' ' ')

# Also detect section-heading component calls (dynamic h2)
SECTION_HEADING_COUNT=$(grep -c "get_template_part.*section-heading" "$TEMP_FILE" || echo "0")
SECTION_HEADING_COUNT=$(echo "$SECTION_HEADING_COUNT" | tr -d '[:space:]')

# If section-heading is used, inject h2 into LEVELS at appropriate positions
if [ "$SECTION_HEADING_COUNT" -gt 0 ]; then
  # For simplicity, assume section-headings appear before their section content
  # We'll add h2 tokens after h1 (page header) and before first h3
  LEVELS_ARRAY=($LEVELS)
  NEW_LEVELS=""

  H2_INJECTED=0
  for i in "${!LEVELS_ARRAY[@]}"; do
    LEVEL="${LEVELS_ARRAY[$i]}"
    NEW_LEVELS="$NEW_LEVELS$LEVEL "

    # After h1, inject section-heading h2s before any h3+
    if [ "$LEVEL" = "1" ] && [ "$H2_INJECTED" -eq 0 ]; then
      for ((j=0; j<SECTION_HEADING_COUNT; j++)); do
        NEW_LEVELS="${NEW_LEVELS}2 "
      done
      H2_INJECTED=1
    fi
  done

  LEVELS="$NEW_LEVELS"
fi

if [ -n "$LEVELS" ]; then
  echo ""
  echo "📊 Heading sequence: h$LEVELS"

  # Check for skips (e.g., h2 → h4)
  PREV_LEVEL=""
  SKIP_FOUND=0

  for LEVEL in $LEVELS; do
    if [ -n "$PREV_LEVEL" ]; then
      DIFF=$((LEVEL - PREV_LEVEL))
      if [ "$DIFF" -gt 1 ]; then
        echo "❌ Hierarchy skip: h$PREV_LEVEL → h$LEVEL"
        SKIP_FOUND=1
        ERRORS=$((ERRORS + 1))
      fi
    fi
    PREV_LEVEL=$LEVEL
  done

  if [ "$SKIP_FOUND" -eq 0 ]; then
    echo "✓ No hierarchy skips"
  fi
elif [ "$H1_COUNT" -eq 0 ]; then
  # Already counted as error above
  true
fi

echo ""
if [ "$ERRORS" -gt 0 ]; then
  echo "❌ Heading structure check failed: $ERRORS errors"
  exit 1
fi

echo "✅ Heading structure check passed"
exit 0

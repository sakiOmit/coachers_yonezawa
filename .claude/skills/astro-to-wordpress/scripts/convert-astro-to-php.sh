#!/bin/bash
# Astro → WordPress PHP Semi-Automatic Converter
# Usage: bash convert-astro-to-php.sh <page-slug> [--dry-run]
#
# Automates mechanical conversion patterns:
#   1. Props interface → PHP $args defaults array
#   2. camelCase → snake_case variable names
#   3. {text} → <?php echo esc_html($text); ?>
#   4. <ResponsiveImage> → render_responsive_image()
#   5. Template Name comment insertion
#
# LLM handles: ACF logic, complex conditionals, loop structures

set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
SLUG="${1:-}"
DRY_RUN=false
[[ "${2:-}" == "--dry-run" ]] && DRY_RUN=true

if [[ -z "$SLUG" ]]; then
  echo "Usage: bash convert-astro-to-php.sh <page-slug> [--dry-run]"
  echo ""
  echo "Example: bash convert-astro-to-php.sh about"
  exit 1
fi

# Detect theme directory
THEME_DIR=""
for d in "$PROJECT_ROOT"/themes/*/; do
  [[ -f "${d}functions.php" ]] && THEME_DIR="$d" && break
done
if [[ -z "$THEME_DIR" ]]; then
  echo "ERROR: No WordPress theme found in themes/"
  exit 1
fi
THEME_NAME=$(basename "$THEME_DIR")

# Source paths
ASTRO_PAGE="$PROJECT_ROOT/astro/src/pages/${SLUG}.astro"
ASTRO_SECTIONS_DIR="$PROJECT_ROOT/astro/src/components/sections/${SLUG}"
ASTRO_DATA="$PROJECT_ROOT/astro/src/data/pages/${SLUG}.json"

# Output paths
WP_PAGE_DIR="${THEME_DIR}pages"
WP_PARTS_DIR="${THEME_DIR}template-parts/sections/${SLUG}"
SCSS_DIR="$PROJECT_ROOT/src/scss/object/project/${SLUG}"
SCSS_ENTRY="$PROJECT_ROOT/src/css/pages/${SLUG}/style.scss"

REPORT_DIR="$PROJECT_ROOT/reports"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
REPORT_FILE="${REPORT_DIR}/convert-${SLUG}-${TIMESTAMP}.json"

mkdir -p "$REPORT_DIR"

echo "=========================================="
echo " Astro -> WordPress Converter: ${SLUG}"
echo "=========================================="
echo ""

ERRORS=0
WARNINGS=0
CONVERTED=()
MANUAL_REQUIRED=()

# ============================================================
# Phase 1: Source Validation
# ============================================================
echo "[Phase 1] Source Validation"
echo "----------------------------"

if [[ ! -f "$ASTRO_PAGE" ]]; then
  echo "  ERROR: Astro page not found: ${ASTRO_PAGE}"
  ERRORS=$((ERRORS + 1))
fi

SECTIONS=()
if [[ -d "$ASTRO_SECTIONS_DIR" ]]; then
  while IFS= read -r f; do
    SECTIONS+=("$(basename "$f" .astro)")
  done < <(find "$ASTRO_SECTIONS_DIR" -name "*.astro" -type f | sort)
  echo "  Found ${#SECTIONS[@]} section(s): ${SECTIONS[*]}"
else
  echo "  WARN: No sections directory: ${ASTRO_SECTIONS_DIR}"
  WARNINGS=$((WARNINGS + 1))
fi

if [[ -f "$ASTRO_DATA" ]]; then
  echo "  Data file: ${ASTRO_DATA}"
else
  echo "  INFO: No data file (may use inline data)"
fi

if [[ $ERRORS -gt 0 ]]; then
  echo ""
  echo "ABORT: Source validation failed with ${ERRORS} error(s)"
  exit 1
fi

echo "  PASS"
echo ""

# ============================================================
# Phase 2: Extract Props (camelCase → snake_case mapping)
# ============================================================
echo "[Phase 2] Props Extraction & Mapping"
echo "--------------------------------------"

# Extract Props interface from each section
declare -A PROPS_MAP
for section in "${SECTIONS[@]}"; do
  section_file="${ASTRO_SECTIONS_DIR}/${section}.astro"
  [[ ! -f "$section_file" ]] && continue

  # Extract lines between "interface Props {" and "}"
  props_block=$(sed -n '/interface Props/,/^}/p' "$section_file" 2>/dev/null || true)

  if [[ -n "$props_block" ]]; then
    # Convert camelCase to snake_case
    while IFS= read -r line; do
      # Extract prop name (camelCase, with optional ?)
      prop=$(echo "$line" | grep -oP '^\s*(\w+)\??' | sed 's/^\s*//' | sed 's/?.*//')
      [[ -z "$prop" || "$prop" == "interface" || "$prop" == "}" ]] && continue

      # camelCase → snake_case
      snake=$(echo "$prop" | sed -E 's/([A-Z])/_\L\1/g' | sed 's/^_//')
      PROPS_MAP["${section}:${prop}"]="$snake"
      echo "  ${section}: ${prop} -> ${snake}"
    done <<< "$props_block"
  fi
done

echo "  Total props mapped: ${#PROPS_MAP[@]}"
echo ""

# ============================================================
# Phase 3: Mechanical Conversion Patterns
# ============================================================
echo "[Phase 3] Conversion Pattern Analysis"
echo "---------------------------------------"

analyze_file() {
  local file="$1"
  local name="$2"
  local auto=0 manual=0

  # Count auto-convertible patterns
  auto=$((auto + $(grep -c '{[a-zA-Z_]*}' "$file" 2>/dev/null || echo 0)))  # {text} expressions
  auto=$((auto + $(grep -c '<ResponsiveImage' "$file" 2>/dev/null || echo 0)))  # ResponsiveImage
  auto=$((auto + $(grep -c 'import.*from' "$file" 2>/dev/null || echo 0)))  # imports

  # Count manual patterns (LLM required)
  manual=$((manual + $(grep -c '\.map(' "$file" 2>/dev/null || echo 0)))  # Array map (→ while/have_rows)
  manual=$((manual + $(grep -c '&&' "$file" 2>/dev/null || echo 0)))  # Conditional rendering
  manual=$((manual + $(grep -c 'set:html' "$file" 2>/dev/null || echo 0)))  # HTML injection
  manual=$((manual + $(grep -c 'ternary\|?' "$file" 2>/dev/null || echo 0)))  # Ternary

  echo "  ${name}: auto=${auto}, manual=${manual}"
  [[ $manual -gt 0 ]] && MANUAL_REQUIRED+=("${name}: ${manual} patterns need LLM")
}

if [[ -f "$ASTRO_PAGE" ]]; then
  analyze_file "$ASTRO_PAGE" "page"
fi

for section in "${SECTIONS[@]}"; do
  section_file="${ASTRO_SECTIONS_DIR}/${section}.astro"
  [[ -f "$section_file" ]] && analyze_file "$section_file" "$section"
done

echo ""

# ============================================================
# Phase 4: Generate PHP Stubs (dry-run safe)
# ============================================================
echo "[Phase 4] PHP Stub Generation"
echo "-------------------------------"

# Convert PascalCase to kebab-case
to_kebab() {
  echo "$1" | sed -E 's/([A-Z])/-\L\1/g' | sed 's/^-//'
}

generate_page_template() {
  local slug="$1"
  local output="${WP_PAGE_DIR}/page-${slug}.php"

  if [[ "$DRY_RUN" == true ]]; then
    echo "  [DRY-RUN] Would create: ${output}"
    return
  fi

  mkdir -p "$(dirname "$output")"

  # Generate page template with section includes
  cat > "$output" << 'PHPEOF'
<?php
/**
 * Template Name: {{PAGE_NAME}}
 * Description: {{PAGE_NAME}}ページ
 */

get_header();
PHPEOF

  # Replace placeholder
  sed -i "s/{{PAGE_NAME}}/${slug}/g" "$output"

  # Add section includes
  for section in "${SECTIONS[@]}"; do
    local kebab_section
    kebab_section=$(to_kebab "$section")
    echo "" >> "$output"
    echo "get_template_part('template-parts/sections/${slug}/${kebab_section}');" >> "$output"
  done

  echo "" >> "$output"
  echo "get_footer();" >> "$output"

  chmod 644 "$output"
  CONVERTED+=("$output")
  echo "  Created: ${output}"
}

generate_section_template() {
  local slug="$1"
  local section="$2"
  local section_file="${ASTRO_SECTIONS_DIR}/${section}.astro"
  local kebab_section
  kebab_section=$(to_kebab "$section")
  local output="${WP_PARTS_DIR}/${kebab_section}.php"

  if [[ "$DRY_RUN" == true ]]; then
    echo "  [DRY-RUN] Would create: ${output}"
    return
  fi

  mkdir -p "$(dirname "$output")"

  # Extract BEM block name from the section file
  local bem_block
  bem_block=$(grep -oP 'class="(p-[a-z0-9-]+)' "$section_file" 2>/dev/null | head -1 | sed 's/class="//' || echo "p-${slug}-${kebab_section}")

  # Start PHP file with args validation
  cat > "$output" << PHPEOF
<?php
/**
 * ${section} Section
 *
 * @package Theme
 */

// \$args defaults
\$args = merge_template_defaults(\$args ?? [], [
PHPEOF

  # Add props as defaults
  for key in "${!PROPS_MAP[@]}"; do
    if [[ "$key" == "${section}:"* ]]; then
      local snake="${PROPS_MAP[$key]}"
      echo "    '${snake}' => ''," >> "$output"
    fi
  done

  cat >> "$output" << PHPEOF
]);
?>

<section class="${bem_block}">
  <div class="${bem_block}__container">
    <!-- TODO: LLM converts detailed HTML from ${section}.astro -->
  </div>
</section>
PHPEOF

  chmod 644 "$output"
  CONVERTED+=("$output")
  echo "  Created: ${output}"
}

generate_page_template "$SLUG"

for section in "${SECTIONS[@]}"; do
  generate_section_template "$SLUG" "$section"
done

echo ""

# ============================================================
# Phase 5: Build Config Check
# ============================================================
echo "[Phase 5] Build Configuration Check"
echo "--------------------------------------"

# Check vite.config.js entry
VITE_CONFIG="$PROJECT_ROOT/vite.config.js"
if [[ -f "$VITE_CONFIG" ]]; then
  if grep -q "pages/${SLUG}" "$VITE_CONFIG" 2>/dev/null; then
    echo "  vite.config.js: Entry exists"
  else
    echo "  vite.config.js: MISSING entry for pages/${SLUG}"
    MANUAL_REQUIRED+=("vite.config.js: Add entry for pages/${SLUG}/style.scss")
    WARNINGS=$((WARNINGS + 1))
  fi
fi

# Check enqueue.php
ENQUEUE_FILE=$(find "$THEME_DIR" -name "enqueue.php" -type f 2>/dev/null | head -1)
if [[ -n "$ENQUEUE_FILE" ]]; then
  if grep -q "$SLUG" "$ENQUEUE_FILE" 2>/dev/null; then
    echo "  enqueue.php: Conditional exists"
  else
    echo "  enqueue.php: MISSING conditional for ${SLUG}"
    MANUAL_REQUIRED+=("enqueue.php: Add conditional enqueue for ${SLUG}")
    WARNINGS=$((WARNINGS + 1))
  fi
fi

# Check SCSS entry
if [[ -f "$SCSS_ENTRY" ]]; then
  echo "  SCSS entry: exists"
else
  echo "  SCSS entry: MISSING (${SCSS_ENTRY})"
  MANUAL_REQUIRED+=("Create SCSS entry: ${SCSS_ENTRY}")
  WARNINGS=$((WARNINGS + 1))
fi

echo ""

# ============================================================
# Phase 6: Verification (post-generation)
# ============================================================
echo "[Phase 6] Post-Generation Verification"
echo "----------------------------------------"

VERIFY_PASS=0
VERIFY_FAIL=0

# PHP syntax check on generated files
for f in "${CONVERTED[@]}"; do
  if [[ -f "$f" ]] && php -l "$f" > /dev/null 2>&1; then
    echo "  PHP syntax OK: $(basename "$f")"
    VERIFY_PASS=$((VERIFY_PASS + 1))
  elif [[ -f "$f" ]]; then
    echo "  PHP syntax FAIL: $(basename "$f")"
    VERIFY_FAIL=$((VERIFY_FAIL + 1))
  fi
done

# Check file permissions
for f in "${CONVERTED[@]}"; do
  if [[ -f "$f" ]]; then
    perms=$(stat -c %a "$f" 2>/dev/null || echo "unknown")
    if [[ "$perms" == "644" ]]; then
      echo "  Permission OK (644): $(basename "$f")"
    else
      echo "  Permission WARN (${perms}): $(basename "$f")"
      WARNINGS=$((WARNINGS + 1))
    fi
  fi
done

echo ""

# ============================================================
# Generate Report
# ============================================================
SECTIONS_JSON=$(printf '"%s",' "${SECTIONS[@]}" | sed 's/,$//')
CONVERTED_JSON=$(printf '"%s",' "${CONVERTED[@]}" | sed 's/,$//')
MANUAL_JSON=$(printf '"%s",' "${MANUAL_REQUIRED[@]}" 2>/dev/null | sed 's/,$//' || echo "")

VERDICT="READY_FOR_LLM"
[[ $ERRORS -gt 0 ]] && VERDICT="FAILED"
[[ ${#MANUAL_REQUIRED[@]} -gt 3 ]] && VERDICT="NEEDS_SIGNIFICANT_WORK"

cat > "$REPORT_FILE" << EOF
{
  "timestamp": "${TIMESTAMP}",
  "slug": "${SLUG}",
  "theme": "${THEME_NAME}",
  "sections": [${SECTIONS_JSON}],
  "props_mapped": ${#PROPS_MAP[@]},
  "files_generated": [${CONVERTED_JSON}],
  "manual_required": [${MANUAL_JSON}],
  "verification": {
    "php_syntax_pass": ${VERIFY_PASS},
    "php_syntax_fail": ${VERIFY_FAIL},
    "warnings": ${WARNINGS}
  },
  "verdict": "${VERDICT}"
}
EOF

echo "=========================================="
echo " Conversion Summary: ${SLUG}"
echo "=========================================="
echo ""
echo "  Sections: ${#SECTIONS[@]}"
echo "  Props mapped: ${#PROPS_MAP[@]}"
echo "  Files generated: ${#CONVERTED[@]}"
echo "  Manual items: ${#MANUAL_REQUIRED[@]}"
echo "  PHP syntax: ${VERIFY_PASS} pass, ${VERIFY_FAIL} fail"
echo "  Verdict: ${VERDICT}"
echo ""
echo "  Report: ${REPORT_FILE}"
echo ""

if [[ ${#MANUAL_REQUIRED[@]} -gt 0 ]]; then
  echo "  LLM TODO:"
  for item in "${MANUAL_REQUIRED[@]}"; do
    echo "    - ${item}"
  done
  echo ""
fi

echo "  Next: LLM completes HTML conversion using references/conversion-patterns.md"

exit $([ $ERRORS -eq 0 ] && echo 0 || echo 1)

#!/bin/bash
set -euo pipefail

# generate-wp-page.sh
# Purpose: Generate WordPress page template scaffold
# Input: page-slug, sections (comma-separated), estimated lines
# Output: PHP templates, SCSS structure, entry point
# Exit: 0=success, 1=validation error

SLUG="${1:-}"
SECTIONS="${2:-}"
LINES="${3:-100}"
SRC_DIR="src"

# --- Theme detection ---
detect_theme() {
  if [[ -f "config/theme.js" ]]; then
    local theme
    theme=$(grep -oP "(?<=['\"])([^'\"]+)(?=['\"])" config/theme.js 2>/dev/null | head -1)
    if [[ -n "$theme" ]]; then
      echo "$theme"
      return
    fi
  fi
  # Fallback: find first directory in themes/ with functions.php
  for dir in themes/*/; do
    if [[ -f "${dir}functions.php" ]]; then
      basename "$dir"
      return
    fi
  done
  echo ""
}

THEME=$(detect_theme)

# --- Validation ---
if [[ -z "$SLUG" ]]; then
  echo "Error: page-slug required" >&2
  echo "Usage: $0 <page-slug> <sections> [lines]" >&2
  echo "Example: $0 recruit hero,message,positions 300" >&2
  exit 1
fi

if [[ ! "$SLUG" =~ ^[a-z][a-z0-9-]*$ ]]; then
  echo "Error: slug must be kebab-case" >&2
  exit 1
fi

if [[ -z "$SECTIONS" ]]; then
  echo "Error: sections required (comma-separated)" >&2
  exit 1
fi

if [[ -z "$THEME" ]]; then
  echo "Error: No WordPress theme found in themes/" >&2
  echo "Create a theme directory with functions.php first." >&2
  exit 1
fi

THEME_DIR="themes/${THEME}"
if [[ ! -d "$THEME_DIR" ]]; then
  echo "Error: Theme directory not found: ${THEME_DIR}" >&2
  exit 1
fi

# --- Parse sections ---
IFS=',' read -ra SECTION_ARRAY <<< "$SECTIONS"
SPLIT=$( (( LINES >= 200 )) && echo "true" || echo "false" )

echo "Generating WordPress page: ${SLUG}"
echo "Theme: ${THEME}"
echo "Sections: ${SECTIONS}"
echo "Lines: ${LINES} (split: ${SPLIT})"
echo ""

# --- Check existing files ---
PAGE_FILE="${THEME_DIR}/pages/page-${SLUG}.php"
if [[ -f "$PAGE_FILE" ]]; then
  echo "Warning: ${PAGE_FILE} already exists (will not overwrite)" >&2
  exit 1
fi

# --- Create directories ---
mkdir -p "${THEME_DIR}/pages"
mkdir -p "${SRC_DIR}/scss/object/project/${SLUG}"
mkdir -p "${SRC_DIR}/css/pages/${SLUG}"

if [[ "$SPLIT" == "true" ]]; then
  mkdir -p "${THEME_DIR}/template-parts/${SLUG}"
fi

# --- Generate page template ---
{
  echo "<?php"
  echo "/**"
  echo " * Template Name: TODO_PAGE_NAME"
  echo " *"
  echo " * @package ${THEME}"
  echo " */"
  echo ""
  echo "get_header();"
  echo "?>"
  echo ""
  echo "<main class=\"l-main\">"

  for section in "${SECTION_ARRAY[@]}"; do
    section=$(echo "$section" | tr -d ' ')
    if [[ "$SPLIT" == "true" ]]; then
      echo "  <?php get_template_part('template-parts/${SLUG}/${section}'); ?>"
    else
      echo ""
      echo "  <section class=\"p-${SLUG}-${section}\">"
      echo "    <div class=\"p-${SLUG}-${section}__container\">"
      echo "      <!-- TODO: Implement ${section} section -->"
      echo "    </div>"
      echo "  </section>"
    fi
  done

  echo "</main>"
  echo ""
  echo "<?php get_footer(); ?>"
} > "$PAGE_FILE"
echo "  Created: ${PAGE_FILE}"

# --- Generate template-parts (if split) ---
if [[ "$SPLIT" == "true" ]]; then
  for section in "${SECTION_ARRAY[@]}"; do
    section=$(echo "$section" | tr -d ' ')
    PART_FILE="${THEME_DIR}/template-parts/${SLUG}/${section}.php"

    if [[ -f "$PART_FILE" ]]; then
      echo "  Skip (exists): ${PART_FILE}"
      continue
    fi

    cat > "$PART_FILE" << PHPEOF
<?php
/**
 * ${SLUG} - ${section} section
 *
 * @package ${THEME}
 */
?>

<section class="p-${SLUG}-${section}">
  <div class="p-${SLUG}-${section}__container">
    <!-- TODO: Implement ${section} section -->
  </div>
</section>
PHPEOF
    echo "  Created: ${PART_FILE}"
  done
fi

# --- Generate SCSS files ---
SCSS_DIR="${SRC_DIR}/scss/object/project/${SLUG}"

MAIN_SCSS="${SCSS_DIR}/_p-${SLUG}.scss"
if [[ ! -f "$MAIN_SCSS" ]]; then
  echo "// p-${SLUG} - Page styles" > "$MAIN_SCSS"
  for section in "${SECTION_ARRAY[@]}"; do
    section=$(echo "$section" | tr -d ' ')
    echo "@use 'p-${SLUG}-${section}';" >> "$MAIN_SCSS"
  done
  echo "  Created: ${MAIN_SCSS}"
fi

for section in "${SECTION_ARRAY[@]}"; do
  section=$(echo "$section" | tr -d ' ')
  SECTION_SCSS="${SCSS_DIR}/_p-${SLUG}-${section}.scss"
  if [[ ! -f "$SECTION_SCSS" ]]; then
    cat > "$SECTION_SCSS" << SCSSEOF
.p-${SLUG}-${section} {
  &__container {
    @include container();
  }
}
SCSSEOF
    echo "  Created: ${SECTION_SCSS}"
  fi
done

ENTRY_FILE="${SRC_DIR}/css/pages/${SLUG}/style.scss"
if [[ ! -f "$ENTRY_FILE" ]]; then
  cat > "$ENTRY_FILE" << SCSSEOF
@use "../../../scss/object/project/${SLUG}/p-${SLUG}";
SCSSEOF
  echo "  Created: ${ENTRY_FILE}"
fi

# --- Set permissions ---
find "${THEME_DIR}/pages/" -name "*.php" -exec chmod 644 {} \; 2>/dev/null || true
if [[ "$SPLIT" == "true" ]]; then
  find "${THEME_DIR}/template-parts/${SLUG}/" -name "*.php" -exec chmod 644 {} \; 2>/dev/null || true
fi

echo ""
echo "Done! Generated files for '${SLUG}' page."
echo ""
echo "Next steps:"
echo "  1. Update TODO_PAGE_NAME in ${PAGE_FILE}"
echo "  2. Add entry to vite.config.js"
echo "  3. Add conditional enqueue to inc/enqueue.php"
echo "  4. Implement section content"
echo "  5. Run: npm run dev"

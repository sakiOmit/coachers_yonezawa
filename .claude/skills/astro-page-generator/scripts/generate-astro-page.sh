#!/bin/bash
set -euo pipefail

# generate-astro-page.sh
# Purpose: Generate Astro page scaffold from arguments
# Input: page-slug, sections (comma-separated)
# Output: Astro page, section components, mock data, SCSS files
# Exit: 0=success, 1=validation error

SLUG="${1:-}"
SECTIONS="${2:-}"
ASTRO_DIR="astro/src"
SRC_DIR="src"

# --- Validation ---
if [[ -z "$SLUG" ]]; then
  echo "Error: page-slug required" >&2
  echo "Usage: $0 <page-slug> <sections>" >&2
  echo "Example: $0 about hero,mission,team" >&2
  exit 1
fi

if [[ ! "$SLUG" =~ ^[a-z][a-z0-9-]*$ ]]; then
  echo "Error: slug must be kebab-case (e.g., about, contact-us)" >&2
  exit 1
fi

if [[ -z "$SECTIONS" ]]; then
  echo "Error: sections required (comma-separated)" >&2
  echo "Example: $0 $SLUG hero,mission,team" >&2
  exit 1
fi

if [[ ! -f "astro/package.json" ]]; then
  echo "Error: Astro environment not found. Run 'npm run astro:install' first." >&2
  exit 1
fi

# --- Parse sections ---
IFS=',' read -ra SECTION_ARRAY <<< "$SECTIONS"

# --- Check existing files ---
PAGE_FILE="${ASTRO_DIR}/pages/${SLUG}.astro"
if [[ -f "$PAGE_FILE" ]]; then
  echo "Warning: ${PAGE_FILE} already exists (will not overwrite)" >&2
  echo "Delete the file first if you want to regenerate." >&2
  exit 1
fi

echo "Generating Astro page: ${SLUG}"
echo "Sections: ${SECTIONS}"
echo ""

# --- Create directories ---
mkdir -p "${ASTRO_DIR}/components/sections/${SLUG}"
mkdir -p "${ASTRO_DIR}/data/pages"
mkdir -p "${SRC_DIR}/scss/object/project/${SLUG}"
mkdir -p "${SRC_DIR}/css/pages/${SLUG}"

# --- Generate section components ---
for section in "${SECTION_ARRAY[@]}"; do
  section=$(echo "$section" | tr -d ' ')
  # Convert kebab-case to PascalCase
  PASCAL=$(echo "$section" | sed -E 's/(^|-)([a-z])/\U\2/g')
  SECTION_FILE="${ASTRO_DIR}/components/sections/${SLUG}/${PASCAL}.astro"

  if [[ -f "$SECTION_FILE" ]]; then
    echo "  Skip (exists): ${SECTION_FILE}"
    continue
  fi

  cat > "$SECTION_FILE" << ASTROEOF
---
/**
 * ${PASCAL}
 * WordPress template-parts/${SLUG}/${section}.php に相当
 *
 * 変換先: get_template_part('template-parts/${SLUG}/${section}')
 */
interface Props {
  // TODO: Define props matching ACF fields
}

const { } = Astro.props;
---

<section class="p-${SLUG}-${section}">
  <div class="p-${SLUG}-${section}__container">
    <!-- TODO: Implement section content -->
  </div>
</section>
ASTROEOF
  echo "  Created: ${SECTION_FILE}"
done

# --- Generate mock data ---
DATA_FILE="${ASTRO_DIR}/data/pages/${SLUG}.json"
if [[ ! -f "$DATA_FILE" ]]; then
  echo "{" > "$DATA_FILE"
  FIRST=true
  for section in "${SECTION_ARRAY[@]}"; do
    section=$(echo "$section" | tr -d ' ')
    # Convert kebab-case to camelCase
    CAMEL=$(echo "$section" | sed -E 's/-([a-z])/\U\1/g')
    if [[ "$FIRST" == true ]]; then
      FIRST=false
    else
      echo "," >> "$DATA_FILE"
    fi
    printf '  "%s": {}' "$CAMEL" >> "$DATA_FILE"
  done
  echo "" >> "$DATA_FILE"
  echo "}" >> "$DATA_FILE"
  echo "  Created: ${DATA_FILE}"
fi

# --- Generate page file ---
IMPORTS=""
COMPONENTS=""
for section in "${SECTION_ARRAY[@]}"; do
  section=$(echo "$section" | tr -d ' ')
  PASCAL=$(echo "$section" | sed -E 's/(^|-)([a-z])/\U\2/g')
  CAMEL=$(echo "$section" | sed -E 's/-([a-z])/\U\1/g')
  IMPORTS="${IMPORTS}import ${PASCAL} from '../components/sections/${SLUG}/${PASCAL}.astro';
"
  COMPONENTS="${COMPONENTS}    <${PASCAL} {...pageData.${CAMEL}} />
"
done

cat > "$PAGE_FILE" << ASTROEOF
---
/**
 * ${SLUG}
 * WordPress pages/page-${SLUG}.php に相当
 *
 * 変換先: pages/page-${SLUG}.php
 * Template Name: TODO_PAGE_NAME
 */
import BaseLayout from '../layouts/BaseLayout.astro';
${IMPORTS}
import pageData from '../data/pages/${SLUG}.json';
---

<BaseLayout title="TODO_PAGE_NAME | サイト名" bodyClass="p-${SLUG}">
  <link rel="stylesheet" href="/assets/css/pages/${SLUG}/style.css" slot="addCSS" />
  <main>
${COMPONENTS}  </main>
</BaseLayout>
ASTROEOF
echo "  Created: ${PAGE_FILE}"

# --- Generate SCSS files ---
SCSS_DIR="${SRC_DIR}/scss/object/project/${SLUG}"

# Main import file
MAIN_SCSS="${SCSS_DIR}/_p-${SLUG}.scss"
if [[ ! -f "$MAIN_SCSS" ]]; then
  echo "// p-${SLUG} - Page styles" > "$MAIN_SCSS"
  for section in "${SECTION_ARRAY[@]}"; do
    section=$(echo "$section" | tr -d ' ')
    echo "@use 'p-${SLUG}-${section}';" >> "$MAIN_SCSS"
  done
  echo "  Created: ${MAIN_SCSS}"
fi

# Section SCSS files
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

# Entry point
ENTRY_FILE="${SRC_DIR}/css/pages/${SLUG}/style.scss"
if [[ ! -f "$ENTRY_FILE" ]]; then
  cat > "$ENTRY_FILE" << SCSSEOF
@use "../../../scss/object/project/${SLUG}/p-${SLUG}";
SCSSEOF
  echo "  Created: ${ENTRY_FILE}"
fi

echo ""
echo "Done! Generated files for '${SLUG}' page."
echo ""
echo "Next steps:"
echo "  1. Update TODO_PAGE_NAME in ${PAGE_FILE}"
echo "  2. Define Props interfaces in section components"
echo "  3. Populate mock data in ${DATA_FILE}"
echo "  4. Add vite.config.js entry if needed"
echo "  5. Run: npm run astro:dev"

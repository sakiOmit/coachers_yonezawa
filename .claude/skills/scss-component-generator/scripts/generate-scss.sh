#!/bin/bash
set -euo pipefail

# generate-scss.sh
# Purpose: Generate FLOCSS-compliant SCSS file from template
# Input: type (component|project|layout), name, [page], [elements], [modifiers]
# Output: SCSS file in appropriate directory
# Exit: 0=success, 1=validation error

TYPE="${1:-}"
NAME="${2:-}"
PAGE="${3:-}"
ELEMENTS="${4:-}"
MODIFIERS="${5:-}"
SRC_DIR="src"

# --- Validation ---
if [[ -z "$TYPE" || -z "$NAME" ]]; then
  echo "Error: type and name required" >&2
  echo "Usage: $0 <component|project|layout> <name> [page] [elements] [modifiers]" >&2
  echo "Examples:" >&2
  echo "  $0 component button '' icon,text primary,secondary" >&2
  echo "  $0 project hero top title,description,image large" >&2
  echo "  $0 layout sidebar" >&2
  exit 1
fi

if [[ ! "$TYPE" =~ ^(component|project|layout)$ ]]; then
  echo "Error: type must be component, project, or layout" >&2
  exit 1
fi

if [[ ! "$NAME" =~ ^[a-z][a-z0-9-]*$ ]]; then
  echo "Error: name must be kebab-case (e.g., button, hero-section)" >&2
  exit 1
fi

if [[ "$TYPE" == "project" && -z "$PAGE" ]]; then
  echo "Error: page name required for project type" >&2
  echo "Usage: $0 project <name> <page> [elements] [modifiers]" >&2
  exit 1
fi

# --- Determine prefix and path ---
case "$TYPE" in
  component)
    PREFIX="c"
    FULL_NAME="c-${NAME}"
    OUTPUT_DIR="${SRC_DIR}/scss/object/component"
    OUTPUT_FILE="${OUTPUT_DIR}/_${FULL_NAME}.scss"
    ;;
  project)
    PREFIX="p"
    FULL_NAME="p-${PAGE}-${NAME}"
    OUTPUT_DIR="${SRC_DIR}/scss/object/project/${PAGE}"
    OUTPUT_FILE="${OUTPUT_DIR}/_${FULL_NAME}.scss"
    ;;
  layout)
    PREFIX="l"
    FULL_NAME="l-${NAME}"
    OUTPUT_DIR="${SRC_DIR}/scss/layout"
    OUTPUT_FILE="${OUTPUT_DIR}/_${FULL_NAME}.scss"
    ;;
esac

# --- Check existing file ---
if [[ -f "$OUTPUT_FILE" ]]; then
  echo "Error: ${OUTPUT_FILE} already exists" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "Generating SCSS: ${FULL_NAME}"
echo "  Type: ${TYPE} (${PREFIX}-)"
echo "  File: ${OUTPUT_FILE}"
echo ""

# --- Generate SCSS ---
{
  echo ".${FULL_NAME} {"

  # Parse elements
  if [[ -n "$ELEMENTS" ]]; then
    IFS=',' read -ra ELEM_ARRAY <<< "$ELEMENTS"
    for elem in "${ELEM_ARRAY[@]}"; do
      elem=$(echo "$elem" | tr -d ' ')
      if [[ "$elem" == "container" ]]; then
        echo ""
        echo "  &__container {"
        echo "    @include container();"
        echo "  }"
      else
        echo ""
        echo "  &__${elem} {"
        echo "  }"
      fi
    done
  fi

  # Parse modifiers
  if [[ -n "$MODIFIERS" ]]; then
    IFS=',' read -ra MOD_ARRAY <<< "$MODIFIERS"
    for mod in "${MOD_ARRAY[@]}"; do
      mod=$(echo "$mod" | tr -d ' ')
      echo ""
      echo "  &--${mod} {"
      echo "  }"
    done
  fi

  echo "}"
} > "$OUTPUT_FILE"

echo "  Created: ${OUTPUT_FILE}"
echo ""
echo "Done! Next steps:"
echo "  1. Add styles to the generated file"
echo "  2. Add @use to the appropriate entry point"
echo "  3. Run: npm run lint:css"

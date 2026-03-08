#!/usr/bin/env bash
# Phase 3: Generate Semantic Rename Map
#
# Usage: bash generate-rename-map.sh <metadata.json> [--output rename-map.yaml] [--llm-fallback-context fallback.json]
# Input: Figma get_metadata output (JSON)
# Output: YAML rename map (nodeId → newName)
# Exit: 0=success, 1=error

set -euo pipefail

if [[ $# -lt 1 ]] || [[ ! -f "$1" ]]; then
  echo '{"error": "Usage: generate-rename-map.sh <metadata.json> [--output file.yaml] [--llm-fallback-context fallback.json]"}' >&2
  exit 1
fi

METADATA_FILE="$1"
shift

OUTPUT_FILE=""
FALLBACK_CONTEXT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      OUTPUT_FILE="${2:-}"
      shift 2
      ;;
    --llm-fallback-context)
      FALLBACK_CONTEXT="${2:-}"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${SCRIPT_DIR}/../lib"

python3 -c "
import sys, os
sys.path.insert(0, os.path.join('${LIB_DIR}'))
from figma_utils.semantic_rename import generate_rename_map
generate_rename_map(sys.argv[1], sys.argv[2], sys.argv[3])
" "$METADATA_FILE" "$OUTPUT_FILE" "$FALLBACK_CONTEXT"

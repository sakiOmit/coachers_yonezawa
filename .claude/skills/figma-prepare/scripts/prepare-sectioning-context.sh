#!/usr/bin/env bash
# Phase 2 Stage B: Prepare Sectioning Context
#
# Extracts top-level children summary from metadata JSON for Claude sectioning.
# Output: JSON with page info, sorted children (Y ascending), and heuristic hints.
#
# Usage: bash prepare-sectioning-context.sh <metadata.json> [--output file.json] [--enriched-table]
# Exit: 0=success, 1=error

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo '{"error": "Usage: prepare-sectioning-context.sh <metadata.json> [--output file.json] [--enriched-table]"}' >&2
  exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE=""
ENRICHED_TABLE=""

# Parse optional flags (order-independent)
shift  # consume the positional metadata.json argument
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      OUTPUT_FILE="${2:-}"
      shift 2
      ;;
    --enriched-table)
      ENRICHED_TABLE="1"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/figma-utils.sh"

validate_input_file "$INPUT_FILE" "Usage: prepare-sectioning-context.sh <metadata.json> [--output file.json] [--enriched-table]"

run_figma_python "
import json
from figma_utils.sectioning import run_sectioning_context

try:
    result = run_sectioning_context(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else '', sys.argv[3] if len(sys.argv) > 3 else '')
    print(result)
except Exception as e:
    print(json.dumps({'error': str(e)}), file=sys.stderr)
    sys.exit(1)
" "$INPUT_FILE" "$OUTPUT_FILE" "$ENRICHED_TABLE"

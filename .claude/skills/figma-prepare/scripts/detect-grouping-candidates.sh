#!/usr/bin/env bash
# Phase 2: Detect Grouping Candidates
#
# Usage: bash detect-grouping-candidates.sh <metadata.json> [--output grouping-plan.yaml] [--skip-root] [--disable-detectors bg-content,table,highlight]
# Input: Figma get_metadata output (JSON)
# Output: JSON/YAML with grouping candidates
# Exit: 0=success, 1=error

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo '{"error": "Usage: detect-grouping-candidates.sh <metadata.json> [--output file.yaml] [--skip-root] [--disable-detectors list]"}' >&2
  exit 1
fi

INPUT_FILE="$1"

OUTPUT_FILE=""
SKIP_ROOT=""
DISABLE_DETECTORS=""
# Parse optional flags (order-independent)
shift  # consume the positional metadata.json argument
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      OUTPUT_FILE="${2:-}"
      shift 2
      ;;
    --skip-root)
      SKIP_ROOT="1"
      shift
      ;;
    --disable-detectors)
      DISABLE_DETECTORS="${2:-}"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/figma-utils.sh"

validate_input_file "$INPUT_FILE" "Usage: detect-grouping-candidates.sh <metadata.json> [--output file.yaml] [--skip-root] [--disable-detectors list]"

run_figma_python "
import json
sys.setrecursionlimit(3000)
from figma_utils.grouping_engine import detect_grouping_candidates

try:
    result = detect_grouping_candidates(
        metadata_path=sys.argv[1],
        output_file=sys.argv[2],
        skip_root=sys.argv[3],
        disable_detectors=sys.argv[4] if len(sys.argv) > 4 else '',
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print(json.dumps({'error': str(e)}), file=sys.stderr)
    sys.exit(1)
" "$INPUT_FILE" "$OUTPUT_FILE" "$SKIP_ROOT" "$DISABLE_DETECTORS"

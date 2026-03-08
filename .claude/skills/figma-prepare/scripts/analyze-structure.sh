#!/usr/bin/env bash
# Phase 1: Figma Structure Quality Analysis
#
# Usage: bash analyze-structure.sh <metadata.json>
# Input: Figma get_metadata output (JSON with 'document' or 'node' key)
# Output: JSON with quality score, grade, and issue breakdown
# Exit: 0=success, 1=error

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo '{"error": "Usage: analyze-structure.sh <metadata.json>"}' >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/figma-utils.sh"

validate_input_file "$1" "Usage: analyze-structure.sh <metadata.json>"

run_figma_python "
import json
from figma_utils.structure_analysis import run_structure_analysis

try:
    result = run_structure_analysis(sys.argv[1])
    print(result)
except Exception as e:
    print(json.dumps({'error': str(e)}), file=sys.stderr)
    sys.exit(1)
" "$1"

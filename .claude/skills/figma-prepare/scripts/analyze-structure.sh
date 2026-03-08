#!/usr/bin/env bash
# Phase 1: Figma Structure Quality Analysis
#
# Usage: bash analyze-structure.sh <metadata.json>
# Input: Figma get_metadata output (JSON with 'document' or 'node' key)
# Output: JSON with quality score, grade, and issue breakdown
# Exit: 0=success, 1=error

set -euo pipefail

if [[ $# -lt 1 ]] || [[ ! -f "$1" ]]; then
  echo '{"error": "Usage: analyze-structure.sh <metadata.json>"}' >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 -c "
import sys, os, json
sys.path.insert(0, os.path.join(sys.argv[1], 'lib'))
from figma_utils.structure_analysis import run_structure_analysis

try:
    result = run_structure_analysis(sys.argv[2])
    print(result)
except Exception as e:
    print(json.dumps({'error': str(e)}), file=sys.stderr)
    sys.exit(1)
" "${SCRIPT_DIR}/.." "$1"

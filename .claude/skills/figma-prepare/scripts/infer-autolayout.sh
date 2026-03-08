#!/usr/bin/env bash
# Phase 4: Infer Auto Layout Settings
#
# Usage: bash infer-autolayout.sh <metadata.json> [--output autolayout-plan.yaml]
# Input: Figma get_metadata output (JSON)
# Output: JSON/YAML with Auto Layout settings per frame
# Exit: 0=success, 1=error

set -euo pipefail

if [[ $# -lt 1 ]] || [[ ! -f "$1" ]]; then
  echo '{"error": "Usage: infer-autolayout.sh <metadata.json> [--output file.yaml]"}' >&2
  exit 1
fi

OUTPUT_FILE=""
if [[ "${2:-}" == "--output" ]] && [[ -n "${3:-}" ]]; then
  OUTPUT_FILE="$3"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 -c "
import sys, os
sys.path.insert(0, os.path.join(sys.argv[1], 'lib'))
from figma_utils.autolayout import run_autolayout_inference
import json

try:
    result = run_autolayout_inference(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else '')
    print(result)
except Exception as e:
    print(json.dumps({'error': str(e)}), file=sys.stderr)
    sys.exit(1)
" "${SCRIPT_DIR}/.." "$1" "$OUTPUT_FILE"

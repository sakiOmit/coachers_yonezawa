#!/usr/bin/env bash
# Phase 1.5: Enrich Metadata with Design Context Data
#
# Usage: bash enrich-metadata.sh <metadata.json> <enrichment.json> [--output enriched.json]
# Input:
#   metadata.json    - Figma get_metadata output (JSON tree)
#   enrichment.json  - Flat map: { nodeId: { fills, layoutMode, characters, ... } }
# Output: Enriched metadata JSON (merged tree)
# Exit: 0=success, 1=error
#
# The enrichment JSON format:
# {
#   "1:101": {
#     "fills": [{"type": "IMAGE", "imageRef": "abc123"}],
#     "layoutMode": "HORIZONTAL",
#     "itemSpacing": 24,
#     "paddingTop": 10,
#     "paddingRight": 20,
#     "paddingBottom": 10,
#     "paddingLeft": 20,
#     "characters": "Button Text"
#   }
# }

set -euo pipefail

if [[ $# -lt 2 ]] || [[ ! -f "$1" ]] || [[ ! -f "$2" ]]; then
  echo '{"error": "Usage: enrich-metadata.sh <metadata.json> <enrichment.json> [--output file.json]"}' >&2
  exit 1
fi

OUTPUT_FILE=""
if [[ "${3:-}" == "--output" ]] && [[ -n "${4:-}" ]]; then
  OUTPUT_FILE="$4"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 -c "
import json, sys, os
sys.path.insert(0, os.path.join(sys.argv[1], 'lib'))
from figma_utils.metadata_enricher import enrich_metadata_from_files

try:
    result = enrich_metadata_from_files(sys.argv[2], sys.argv[3], sys.argv[4])
    print(result)
except Exception as e:
    print(json.dumps({'error': str(e)}), file=sys.stderr)
    sys.exit(1)
" "${SCRIPT_DIR}/.." "$1" "$2" "$OUTPUT_FILE"

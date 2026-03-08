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

if [[ $# -lt 2 ]]; then
  echo '{"error": "Usage: enrich-metadata.sh <metadata.json> <enrichment.json> [--output file.json]"}' >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/figma-utils.sh"

validate_input_file "$1" "Usage: enrich-metadata.sh <metadata.json> <enrichment.json> [--output file.json]"
validate_input_file "$2" "Usage: enrich-metadata.sh <metadata.json> <enrichment.json> [--output file.json]"

OUTPUT_FILE=""
if [[ "${3:-}" == "--output" ]] && [[ -n "${4:-}" ]]; then
  OUTPUT_FILE="$4"
fi

run_figma_python "
import json
from figma_utils.metadata_enricher import enrich_metadata_from_files

try:
    result = enrich_metadata_from_files(sys.argv[1], sys.argv[2], sys.argv[3])
    print(result)
except Exception as e:
    print(json.dumps({'error': str(e)}), file=sys.stderr)
    sys.exit(1)
" "$1" "$2" "$OUTPUT_FILE"

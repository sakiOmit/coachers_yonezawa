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
import json, sys
sys.path.insert(0, '${SCRIPT_DIR}/../lib')
from figma_utils import get_root_node

# Properties to merge from enrichment into metadata nodes
ENRICHMENT_KEYS = [
    'fills', 'strokes', 'effects',
    'layoutMode', 'itemSpacing',
    'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
    'primaryAxisAlignItems', 'counterAxisAlignItems',
    'characters', 'style',
]

def enrich_node(node, enrichment_map, stats):
    \"\"\"Recursively walk metadata tree and merge enrichment data.\"\"\"
    node_id = node.get('id', '')

    if node_id in enrichment_map:
        enrich_data = enrichment_map[node_id]
        merged_keys = []
        for key in ENRICHMENT_KEYS:
            if key in enrich_data and enrich_data[key] is not None:
                node[key] = enrich_data[key]
                merged_keys.append(key)
        if merged_keys:
            stats['enriched_nodes'] += 1
            stats['merged_keys'] += len(merged_keys)

    for child in node.get('children', []):
        enrich_node(child, enrichment_map, stats)

try:
    with open(sys.argv[1], 'r') as f:
        metadata = json.load(f)

    with open(sys.argv[2], 'r') as f:
        enrichment = json.load(f)

    root = get_root_node(metadata)

    stats = {'enriched_nodes': 0, 'merged_keys': 0}
    enrich_node(root, enrichment, stats)

    output_file = '${OUTPUT_FILE}'

    if output_file:
        # Write enriched metadata to file
        with open(output_file, 'w') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(json.dumps({
            'enriched_nodes': stats['enriched_nodes'],
            'merged_keys': stats['merged_keys'],
            'total_enrichment_entries': len(enrichment),
            'output': output_file,
            'status': 'success'
        }, indent=2))
    else:
        # Write enriched metadata to stdout
        print(json.dumps(metadata, indent=2, ensure_ascii=False))

except Exception as e:
    print(json.dumps({'error': str(e)}), file=sys.stderr)
    sys.exit(1)
" "$1" "$2"

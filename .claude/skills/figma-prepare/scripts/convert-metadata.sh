#!/usr/bin/env bash
# Convert Figma metadata from any format (XML, MCP response, JSON) to standard JSON.
#
# Usage: bash convert-metadata.sh <input-file> [--output <output-file>]
# Input: Figma get_metadata output in any supported format
# Output: JSON with 'document' key containing the root node tree
# Exit: 0=success, 1=error
#
# Supported input formats:
#   - Raw XML from Figma Dev Mode MCP get_metadata
#   - MCP response wrapper: [{"type": "text", "text": "<frame ...>"}]
#   - JSON with 'document'/'node'/'nodes' key (existing format, passthrough)

set -euo pipefail

if [[ $# -lt 1 ]] || [[ ! -f "$1" ]]; then
  echo '{"error": "Usage: convert-metadata.sh <input-file> [--output <output-file>]"}' >&2
  exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE=""

shift
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output) OUTPUT_FILE="$2"; shift 2 ;;
    *) shift ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 -c "
import json, sys, os
sys.path.insert(0, os.path.join(sys.argv[1], 'lib'))
from figma_utils import load_metadata, get_root_node

try:
    data = load_metadata(sys.argv[2])
    root = get_root_node(data)

    # Wrap in standard format
    output = {'document': root}

    output_file = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else None
    result = json.dumps(output, ensure_ascii=False)

    if output_file:
        with open(output_file, 'w') as f:
            f.write(result)
        print(json.dumps({
            'status': 'ok',
            'output': output_file,
            'root_name': root.get('name', ''),
            'root_type': root.get('type', ''),
            'children': len(root.get('children', [])),
        }))
    else:
        print(result)

except Exception as e:
    print(json.dumps({'error': str(e)}), file=sys.stderr)
    sys.exit(1)
" "${SCRIPT_DIR}/.." "$INPUT_FILE" "$OUTPUT_FILE"

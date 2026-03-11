#!/bin/bash
set -euo pipefail

# validate-yaml.sh
# Purpose: Validate YAML syntax of skill-audit output
# Input: Path to YAML file
# Output: Validation result (text)
# Exit: 0=VALID, 1=INVALID

FILE="${1:-}"

if [[ -z "$FILE" || ! -f "$FILE" ]]; then
  echo "Error: YAML file path required" >&2
  echo "Usage: $0 <yaml-file>" >&2
  exit 1
fi

echo "Validating YAML: ${FILE}"

if command -v python3 &>/dev/null; then
  python3 -c "
import yaml
import sys

try:
    with open('${FILE}', 'r') as f:
        data = yaml.safe_load(f)
    if data is None:
        print('WARN: File is empty or contains only comments')
        sys.exit(0)
    print('PASS: Valid YAML')
    print(f'  Top-level keys: {list(data.keys()) if isinstance(data, dict) else \"(not a mapping)\"}')
    sys.exit(0)
except yaml.YAMLError as e:
    print(f'FAIL: Invalid YAML syntax')
    print(f'  Error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'FAIL: Could not read file')
    print(f'  Error: {e}')
    sys.exit(1)
"
else
  # Fallback: basic syntax check without python
  if grep -qP '^\t' "$FILE"; then
    echo "FAIL: Tabs detected (YAML requires spaces)"
    exit 1
  fi
  echo "WARN: python3 not available, basic check only"
  echo "PASS: No tabs detected (basic check)"
  exit 0
fi

#!/usr/bin/env bash
# Post-process nested-grouping-plan.yaml to absorb single-element dividers
# into adjacent list-item groups (Issue 253).
#
# Usage: bash postprocess-grouping-plan.sh <nested-grouping-plan.yaml>
# Output: Modified YAML to stdout (redirect to overwrite the file)
# Exit: 0=success (with modifications), 1=error, 2=no changes needed

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: postprocess-grouping-plan.sh <plan.yaml>" >&2
  exit 1
fi

PLAN_FILE="$1"

if [[ ! -f "$PLAN_FILE" ]]; then
  echo "ERROR: Plan file not found: $PLAN_FILE" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 -c "
import sys, os
sys.path.insert(0, os.path.join(sys.argv[1], 'lib'))
from figma_utils.grouping_postprocess import postprocess_plan

plan_file = sys.argv[2]
output_text, total_absorbed, exit_code = postprocess_plan(plan_file)
print(output_text)
sys.exit(exit_code)
" "${SCRIPT_DIR}/.." "$PLAN_FILE"

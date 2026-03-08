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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/figma-utils.sh"

validate_input_file "$PLAN_FILE" "Plan file not found: $PLAN_FILE"

run_figma_python "
from figma_utils.grouping_postprocess import postprocess_plan

plan_file = sys.argv[1]
output_text, total_absorbed, exit_code = postprocess_plan(plan_file)
print(output_text)
sys.exit(exit_code)
" "$PLAN_FILE"

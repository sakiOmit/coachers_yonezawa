#!/usr/bin/env bash
# Compare Stage A (rule-based) and Stage C (Haiku inference) grouping results.
#
# Usage: bash compare-grouping.sh <grouping-plan.yaml> <nested-grouping-result.yaml> [--section name]
# Input:
#   - grouping-plan.yaml: Stage A output from detect-grouping-candidates.sh
#   - nested-grouping-result.yaml: Stage C output from Haiku inference
# Output: Comparison report to stdout
# Exit: 0=success, 1=error

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: compare-grouping.sh <grouping-plan.yaml> <nested-grouping-result.yaml> [--section name]" >&2
  exit 1
fi

STAGE_A_FILE="$1"
STAGE_C_FILE="$2"
SECTION_FILTER=""

shift 2
while [[ $# -gt 0 ]]; do
  case "$1" in
    --section)
      SECTION_FILTER="${2:-}"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/figma-utils.sh"

validate_input_file "$STAGE_A_FILE" "Stage A file not found: $STAGE_A_FILE"
validate_input_file "$STAGE_C_FILE" "Stage C file not found: $STAGE_C_FILE"

run_figma_python "
from figma_utils.grouping_compare import run_comparison

stage_a_file = sys.argv[1]
stage_c_file = sys.argv[2]
section_filter = sys.argv[3] if len(sys.argv) > 3 else ''

result, _, _, report = run_comparison(stage_a_file, stage_c_file, section_filter)
print(report)
" "$STAGE_A_FILE" "$STAGE_C_FILE" "$SECTION_FILTER"

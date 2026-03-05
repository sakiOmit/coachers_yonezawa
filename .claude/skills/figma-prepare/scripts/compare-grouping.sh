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

if [[ ! -f "$STAGE_A_FILE" ]]; then
  echo "ERROR: Stage A file not found: $STAGE_A_FILE" >&2
  exit 1
fi
if [[ ! -f "$STAGE_C_FILE" ]]; then
  echo "ERROR: Stage C file not found: $STAGE_C_FILE" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 -c "
import json, sys, os
sys.path.insert(0, os.path.join(sys.argv[1], 'lib'))
from figma_utils import compare_grouping_results, _stage_a_pattern_key

stage_a_file = sys.argv[2]
stage_c_file = sys.argv[3]
section_filter = sys.argv[4] if len(sys.argv) > 4 else ''

# --- Parse Stage A (YAML-like format from detect-grouping-candidates.sh) ---
def parse_stage_a_yaml(filepath):
    \"\"\"Parse the YAML output from detect-grouping-candidates.sh.\"\"\"
    candidates = []
    current = None
    with open(filepath, 'r') as f:
        for line in f:
            line = line.rstrip()
            if line.startswith('#') or not line.strip():
                continue
            if line.strip().startswith('- index:'):
                if current is not None:
                    candidates.append(current)
                current = {}
            elif current is not None and ':' in line:
                stripped = line.strip()
                key, _, val = stripped.partition(':')
                key = key.strip()
                val = val.strip()
                # Remove YAML quotes
                if val.startswith('\"') and val.endswith('\"'):
                    val = val[1:-1]
                if key == 'node_ids':
                    try:
                        current[key] = json.loads(val)
                    except json.JSONDecodeError:
                        current[key] = []
                elif key == 'bg_node_ids':
                    try:
                        current[key] = json.loads(val)
                    except json.JSONDecodeError:
                        current[key] = []
                elif key == 'count':
                    try:
                        current[key] = int(val)
                    except ValueError:
                        current[key] = 0
                elif key in ('fuzzy_match',):
                    current[key] = val.lower() == 'true'
                elif key in ('tuple_size', 'repetitions', 'row_count'):
                    try:
                        current[key] = int(val)
                    except ValueError:
                        current[key] = 0
                else:
                    current[key] = val
    if current is not None:
        candidates.append(current)
    return candidates

# --- Parse Stage C (YAML from Haiku output) ---
def parse_stage_c_yaml(filepath):
    \"\"\"Parse the YAML output from Haiku nested grouping.\"\"\"
    groups = []
    current = None
    with open(filepath, 'r') as f:
        for line in f:
            line = line.rstrip()
            if line.startswith('#') or not line.strip():
                continue
            stripped = line.strip()
            if stripped.startswith('- name:'):
                if current is not None:
                    groups.append(current)
                current = {'name': stripped.split(':', 1)[1].strip().strip('\"')}
            elif current is not None and ':' in stripped:
                key, _, val = stripped.partition(':')
                key = key.strip()
                val = val.strip()
                if val.startswith('\"') and val.endswith('\"'):
                    val = val[1:-1]
                if key == 'node_ids':
                    try:
                        current[key] = json.loads(val)
                    except json.JSONDecodeError:
                        current[key] = []
                else:
                    current[key] = val
    if current is not None:
        groups.append(current)
    return groups

# Parse inputs
stage_a_candidates = parse_stage_a_yaml(stage_a_file)
stage_c_groups = parse_stage_c_yaml(stage_c_file)

# Apply section filter if specified
if section_filter:
    stage_a_candidates = [c for c in stage_a_candidates
                          if section_filter.lower() in c.get('parent', '').lower()
                          or section_filter.lower() in c.get('suggested_name', '').lower()]
    stage_c_groups = [g for g in stage_c_groups
                      if section_filter.lower() in g.get('name', '').lower()]

# Run comparison
result = compare_grouping_results(stage_a_candidates, stage_c_groups)

# --- Output Report ---
print('=== Grouping Comparison Report ===')
print()

# Coverage
all_a_nodes = set()
for c in stage_a_candidates:
    all_a_nodes.update(c.get('node_ids', []))
all_c_nodes = set()
for g in stage_c_groups:
    all_c_nodes.update(g.get('node_ids', []))
covered = len(all_a_nodes & all_c_nodes)
print(f'Coverage: {result[\"coverage\"]*100:.0f}% ({covered}/{len(all_a_nodes)} nodes)')
print(f'Mean Jaccard: {result[\"mean_jaccard\"]:.2f}')
print()

# Pattern Accuracy
if result['pattern_accuracy']:
    print('Pattern Accuracy:')
    for pat_key, counts in sorted(result['pattern_accuracy'].items()):
        m = counts['matched']
        t = counts['total']
        pct = f'{100*m//t}%' if t > 0 else 'N/A'
        status = ''
        if t > 0 and m < t:
            status = '  <-- Stage C missed some'
        print(f'  {pat_key:20s} {m}/{t} ({pct}){status}')
    print()

# Matched pairs detail
if result['matched_pairs']:
    print('Matched Pairs:')
    for pair in result['matched_pairs']:
        a_idx = pair['stage_a_idx']
        c_idx = pair['stage_c_idx']
        a_name = stage_a_candidates[a_idx].get('suggested_name', f'group-{a_idx}')
        c_name = stage_c_groups[c_idx].get('name', f'group-{c_idx}')
        j = pair['jaccard']
        print(f'  [{a_name}] <-> [{c_name}]  Jaccard={j:.2f}')
    print()

# Stage A only
if result['stage_a_only']:
    print('Stage A only (not matched by Stage C):')
    for idx in result['stage_a_only']:
        c = stage_a_candidates[idx]
        name = c.get('suggested_name', '?')
        method = c.get('method', '?')
        count = c.get('count', 0)
        print(f'  [{name}] (method={method}, {count} nodes)')
    print()

# Stage C only
if result['stage_c_only']:
    print('Stage C only (no Stage A counterpart):')
    for idx in result['stage_c_only']:
        g = stage_c_groups[idx]
        name = g.get('name', '?')
        pattern = g.get('pattern', '?')
        count = len(g.get('node_ids', []))
        print(f'  [{name}] (pattern={pattern}, {count} nodes)')
    print()

# Migration recommendation
print('=== Migration Recommendation ===')
cov = result['coverage']
mj = result['mean_jaccard']
if cov >= 0.8 and mj >= 0.7:
    print(f'RECOMMEND: Stage C is sufficient (coverage={cov*100:.0f}%, jaccard={mj:.2f}).')
    print('  -> Stage A detectors can be removed for matched pattern types.')
elif cov >= 0.6:
    print(f'CAUTION: Stage C is partial (coverage={cov*100:.0f}%, jaccard={mj:.2f}).')
    print('  -> Use Stage C as supplement. Maintain Stage A.')
else:
    print(f'INSUFFICIENT: Stage C coverage too low (coverage={cov*100:.0f}%, jaccard={mj:.2f}).')
    print('  -> Maintain Stage A. Improve Stage C prompts.')

# JSON output for programmatic use
print()
print('--- JSON ---')
print(json.dumps(result, indent=2))
" "${SCRIPT_DIR}/.." "$STAGE_A_FILE" "$STAGE_C_FILE" "$SECTION_FILTER"

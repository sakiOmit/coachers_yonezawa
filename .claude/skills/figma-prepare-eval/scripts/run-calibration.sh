#!/usr/bin/env bash
# /figma-prepare-eval Calibration Runner
#
# Usage: bash run-calibration.sh [--report] [--verbose]
# Input: .claude/data/figma-prepare-calibration.yaml
# Output: Calibration report (stdout) + YAML result file
# Exit: 0=all pass, 1=failures detected

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
CALIBRATION_FILE="$PROJECT_ROOT/.claude/data/figma-prepare-calibration.yaml"
ANALYZE_SCRIPT="$PROJECT_ROOT/.claude/skills/figma-prepare/scripts/analyze-structure.sh"
CACHE_DIR="$PROJECT_ROOT/.claude/cache/figma"
VERBOSE=false

for arg in "$@"; do
  case "$arg" in
    --verbose|-v) VERBOSE=true ;;
    --report) ;; # default mode
  esac
done

if [[ ! -f "$CALIBRATION_FILE" ]]; then
  echo "ERROR: Calibration file not found: $CALIBRATION_FILE" >&2
  exit 1
fi

if [[ ! -f "$ANALYZE_SCRIPT" ]]; then
  echo "ERROR: analyze-structure.sh not found: $ANALYZE_SCRIPT" >&2
  exit 1
fi

mkdir -p "$CACHE_DIR"

python3 -c "
import json, sys, os, subprocess, re
from datetime import datetime

PROJECT_ROOT = '$PROJECT_ROOT'
ANALYZE_SCRIPT = '$ANALYZE_SCRIPT'
CACHE_DIR = '$CACHE_DIR'
VERBOSE = '$VERBOSE' == 'true'

# ── YAML parser (minimal, no PyYAML dependency) ──

def parse_calibration_yaml(path):
    \"\"\"Parse calibration YAML without PyYAML dependency.\"\"\"
    with open(path, 'r') as f:
        content = f.read()

    result = {
        'version': '',
        'updated_at': '',
        'scoring_parameters': {},
        'cases': [],
    }

    # Extract version
    m = re.search(r'^version:\s*\"(.+?)\"', content, re.M)
    if m:
        result['version'] = m.group(1)

    # Extract updated_at
    m = re.search(r'^updated_at:\s*\"(.+?)\"', content, re.M)
    if m:
        result['updated_at'] = m.group(1)

    # Extract scoring_parameters
    sp_match = re.search(r'^scoring_parameters:\s*\n((?:  .+\n)*)', content, re.M)
    if sp_match:
        sp_block = sp_match.group(1)
        for line in sp_block.strip().split('\n'):
            line = line.strip()
            # Parse: key: { weight: N, cap: N }
            m = re.match(r'(\w+):\s*\{\s*weight:\s*([\d.]+),\s*cap:\s*(\d+)', line)
            if m:
                result['scoring_parameters'][m.group(1)] = {
                    'weight': float(m.group(2)),
                    'cap': int(m.group(3)),
                }
            # Parse: last_tuned
            m = re.match(r'last_tuned:\s*\"(.+?)\"', line)
            if m:
                result['scoring_parameters']['last_tuned'] = m.group(1)

    # Extract cases
    case_blocks = re.split(r'\n  - id:\s*', content)
    for i, block in enumerate(case_blocks):
        if i == 0:
            continue  # skip header
        case = {}
        # id
        m = re.match(r'(\S+)', block)
        if m:
            case['id'] = m.group(1)

        # source
        m = re.search(r'source:\s*(\S+)', block)
        if m:
            case['source'] = m.group(1)

        # expected_grade
        m = re.search(r'expected_grade:\s*(\S+)', block)
        if m:
            val = m.group(1)
            case['expected_grade'] = None if val == 'null' else val

        # expected_score_range
        m = re.search(r'expected_score_range:\s*\[(\d+),\s*(\d+)\]', block)
        if m:
            case['expected_score_range'] = [int(m.group(1)), int(m.group(2))]

        # tags
        m = re.search(r'tags:\s*\[(.+?)\]', block)
        if m:
            case['tags'] = [t.strip() for t in m.group(1).split(',')]

        # notes
        m = re.search(r'notes:\s*\"(.+?)\"', block)
        if m:
            case['notes'] = m.group(1)

        if 'id' in case and 'source' in case:
            result['cases'].append(case)

    return result

# ── Run analysis ──

def run_analyze(source_path):
    \"\"\"Run analyze-structure.sh and return parsed JSON.\"\"\"
    full_path = os.path.join(PROJECT_ROOT, source_path)
    if not os.path.isfile(full_path):
        return None, f'Source file not found: {source_path}'
    try:
        proc = subprocess.run(
            ['bash', ANALYZE_SCRIPT, full_path],
            capture_output=True, text=True, timeout=60
        )
        if proc.returncode != 0:
            return None, f'Script error: {proc.stderr.strip()}'
        return json.loads(proc.stdout), None
    except Exception as e:
        return None, str(e)

# ── Grade from score ──

def score_to_grade(score):
    if score >= 80: return 'A'
    if score >= 60: return 'B'
    if score >= 40: return 'C'
    if score >= 20: return 'D'
    return 'F'

# ── Main ──

config = parse_calibration_yaml('$CALIBRATION_FILE')
cases = config['cases']

# ANSI colors
GREEN = '\033[32m'
RED = '\033[31m'
YELLOW = '\033[33m'
BOLD = '\033[1m'
RESET = '\033[0m'
DIM = '\033[2m'

print(f'{BOLD}=== /figma-prepare Calibration Report ==={RESET}')
print(f'Dataset: v{config[\"version\"]} (updated: {config[\"updated_at\"]})')
print(f'Scoring params: {json.dumps({k: v for k, v in config[\"scoring_parameters\"].items() if k != \"last_tuned\"}, separators=(\",\", \":\"))}')
print()

results = []
pass_count = 0
fail_count = 0
skip_count = 0
evaluated_count = 0
total_penalties = {'unnamed': 0, 'flat': 0, 'ungrouped': 0, 'nesting': 0}

for case in cases:
    case_id = case['id']
    source = case['source']
    expected_grade = case.get('expected_grade')
    score_range = case.get('expected_score_range', [0, 100])

    data, err = run_analyze(source)
    if err:
        print(f'{YELLOW}  SKIP: {case_id} — {err}{RESET}')
        skip_count += 1
        results.append({
            'id': case_id,
            'status': 'SKIP',
            'reason': err,
        })
        continue

    actual_score = data['score']
    actual_grade = data['grade']
    breakdown = data.get('score_breakdown', {})

    # Accumulate penalties for contribution analysis
    total_penalties['unnamed'] += breakdown.get('unnamed_penalty', 0)
    total_penalties['flat'] += breakdown.get('flat_penalty', 0)
    total_penalties['ungrouped'] += breakdown.get('ungrouped_penalty', 0)
    total_penalties['nesting'] += breakdown.get('nesting_penalty', 0)

    # Determine pass/fail
    in_range = score_range[0] <= actual_score <= score_range[1]

    if expected_grade is None:
        # Grade not specified — only check score range
        if in_range:
            status = 'PASS'
            pass_count += 1
        else:
            status = 'FAIL'
            fail_count += 1
        grade_match = None
        skip_count_note = '(grade N/A)'
    else:
        grade_match = actual_grade == expected_grade
        evaluated_count += 1
        if grade_match and in_range:
            status = 'PASS'
            pass_count += 1
        else:
            status = 'FAIL'
            fail_count += 1

    # Color
    if status == 'PASS':
        color = GREEN
    elif status == 'SKIP':
        color = YELLOW
    else:
        color = RED

    results.append({
        'id': case_id,
        'status': status,
        'expected_grade': expected_grade,
        'actual_grade': actual_grade,
        'actual_score': actual_score,
        'score_range': score_range,
        'in_range': in_range,
        'grade_match': grade_match,
        'breakdown': breakdown,
        'metrics': data.get('metrics', {}),
    })

# ── Summary table ──

print(f'{BOLD}  {\"ID\":<20s} {\"Expected\":>8s}  {\"Actual\":>6s}  {\"Score\":>6s} {\"(range)\":<12s}  Status{RESET}')
print(f'  {\"-\"*20} {\"-\"*8}  {\"-\"*6}  {\"-\"*6} {\"-\"*12}  ------')
for r in results:
    if r['status'] == 'SKIP':
        print(f'{YELLOW}  {r[\"id\"]:<20s} {\"—\":>8s}  {\"—\":>6s}  {\"—\":>6s} {\"\":12s}  SKIP ({r[\"reason\"][:30]}){RESET}')
        continue

    exp_str = r['expected_grade'] if r['expected_grade'] else 'N/A'
    range_str = f'({r[\"score_range\"][0]}-{r[\"score_range\"][1]})'
    if r['status'] == 'PASS':
        color = GREEN
    else:
        color = RED
    print(f'{color}  {r[\"id\"]:<20s} {exp_str:>8s}  {r[\"actual_grade\"]:>6s}  {r[\"actual_score\"]:>6.1f} {range_str:<12s}  {r[\"status\"]}{RESET}')

print()

# Grade accuracy (only for cases with expected_grade)
if evaluated_count > 0:
    grade_correct = sum(1 for r in results if r.get('grade_match') is True)
    accuracy = grade_correct / evaluated_count * 100
    acc_color = GREEN if accuracy == 100 else (YELLOW if accuracy >= 80 else RED)
    print(f'{BOLD}Grade Accuracy: {acc_color}{accuracy:.0f}%{RESET} ({grade_correct}/{evaluated_count})')
else:
    print(f'{BOLD}Grade Accuracy: N/A (no cases with expected_grade){RESET}')

total_cases = len(cases)
print(f'{BOLD}Cases: {total_cases} | Evaluated: {evaluated_count} | Pass: {pass_count} | Fail: {fail_count} | Skip: {skip_count}{RESET}')
print()

# ── Penalty contribution ──

total_penalty_sum = sum(total_penalties.values())
if total_penalty_sum > 0:
    print(f'{BOLD}Penalty Contribution:{RESET}')
    for name, val in sorted(total_penalties.items(), key=lambda x: -x[1]):
        pct = val / total_penalty_sum * 100
        bar_len = int(pct / 2)
        bar = chr(0x2588) * bar_len
        print(f'  {name:<12s} {pct:>4.0f}%  {bar}')
    print()

# ── Confusion matrix (5x5) ──

if evaluated_count > 0:
    grades = ['A', 'B', 'C', 'D', 'F']
    matrix = {exp: {act: 0 for act in grades} for exp in grades}
    for r in results:
        if r.get('expected_grade') and r.get('actual_grade'):
            exp = r['expected_grade']
            act = r['actual_grade']
            if exp in grades and act in grades:
                matrix[exp][act] += 1

    has_data = any(matrix[e][a] > 0 for e in grades for a in grades)
    if has_data:
        print(f'{BOLD}Confusion Matrix (expected x actual):{RESET}')
        header = '          ' + '  '.join(f'{g:>3s}' for g in grades)
        print(f'  {header}')
        for exp in grades:
            row = '  '.join(f'{matrix[exp][act]:>3d}' for act in grades)
            print(f'  {exp:>8s}  {row}')
        print()

# ── Verbose output ──

if VERBOSE:
    print(f'{BOLD}Detailed Breakdown:{RESET}')
    for r in results:
        if r['status'] == 'SKIP':
            continue
        print(f'  {r[\"id\"]}:')
        bd = r.get('breakdown', {})
        print(f'    unnamed={bd.get(\"unnamed_penalty\",0):.1f} flat={bd.get(\"flat_penalty\",0)} ungrouped={bd.get(\"ungrouped_penalty\",0)} nesting={bd.get(\"nesting_penalty\",0)}')
        m = r.get('metrics', {})
        print(f'    nodes={m.get(\"total_nodes\",\"?\")} unnamed_rate={m.get(\"unnamed_rate_pct\",\"?\")}% flat={m.get(\"flat_sections\",\"?\")} deep={m.get(\"deep_nesting_count\",\"?\")}')
    print()

# ── Save result YAML ──

timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
result_file = os.path.join(CACHE_DIR, f'calibration-result-{timestamp}.yaml')

with open(result_file, 'w') as f:
    f.write(f'# Calibration Result — {timestamp}\n')
    f.write(f'version: \"{config[\"version\"]}\"\n')
    f.write(f'run_at: \"{datetime.now().isoformat()}\"\n')
    f.write(f'total_cases: {total_cases}\n')
    f.write(f'evaluated: {evaluated_count}\n')
    f.write(f'pass: {pass_count}\n')
    f.write(f'fail: {fail_count}\n')
    f.write(f'skip: {skip_count}\n')
    if evaluated_count > 0:
        f.write(f'grade_accuracy: {accuracy:.1f}\n')
    f.write(f'\npenalty_contribution:\n')
    for name, val in sorted(total_penalties.items(), key=lambda x: -x[1]):
        pct = val / total_penalty_sum * 100 if total_penalty_sum > 0 else 0
        f.write(f'  {name}: {pct:.1f}\n')
    f.write(f'\nresults:\n')
    for r in results:
        f.write(f'  - id: {r[\"id\"]}\n')
        f.write(f'    status: {r[\"status\"]}\n')
        if r['status'] == 'SKIP':
            f.write(f'    reason: \"{r.get(\"reason\", \"\")}\"\n')
        else:
            f.write(f'    expected_grade: {r.get(\"expected_grade\", \"null\")}\n')
            f.write(f'    actual_grade: {r[\"actual_grade\"]}\n')
            f.write(f'    actual_score: {r[\"actual_score\"]}\n')
            f.write(f'    score_range: [{r[\"score_range\"][0]}, {r[\"score_range\"][1]}]\n')

print(f'{DIM}Result saved: {result_file}{RESET}')

# Exit code
sys.exit(1 if fail_count > 0 else 0)
"

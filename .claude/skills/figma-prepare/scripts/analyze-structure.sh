#!/usr/bin/env bash
# Phase 1: Figma Structure Quality Analysis
#
# Usage: bash analyze-structure.sh <metadata.json>
# Input: Figma get_metadata XML output saved as JSON (with 'xml' key)
# Output: JSON with quality score, grade, and issue breakdown
# Exit: 0=success, 1=error

set -euo pipefail

if [[ $# -lt 1 ]] || [[ ! -f "$1" ]]; then
  echo '{"error": "Usage: analyze-structure.sh <metadata.json>"}' >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 -c "
import json, re, sys, os
sys.setrecursionlimit(3000)  # Guard against deeply nested Figma files (Issue 48)
sys.path.insert(0, os.path.join(sys.argv[1], 'lib'))
from figma_utils import resolve_absolute_coords, get_root_node, UNNAMED_RE, is_section_root

FLAT_THRESHOLD = 15
DEEP_NESTING_THRESHOLD = 6

def count_nodes(node, depth=0, section_depth=None):
    \"\"\"Recursively count nodes and collect metrics.

    depth: absolute depth from root (for reference)
    section_depth: relative depth from nearest section root (for nesting check)
    \"\"\"
    stats = {
        'total': 0,
        'unnamed': 0,
        'flat_sections': 0,
        'deep_nesting': 0,
        'no_autolayout': 0,
        'max_depth': depth,
        'max_section_depth': section_depth if section_depth is not None else 0,  # Issue 71: track relative depth separately
        'frames': 0,
        'unnamed_names': [],
    }

    name = node.get('name', '')
    node_type = node.get('type', '')
    children = node.get('children', [])

    # Reset section_depth at section root boundaries
    if is_section_root(node):
        section_depth = 0
    elif section_depth is not None:
        pass  # keep current section_depth
    # else: above section level, don't count nesting

    stats['total'] += 1

    # Check unnamed
    if UNNAMED_RE.match(name):
        stats['unnamed'] += 1
        stats['unnamed_names'].append(name)

    # Check flat structure (direct children > threshold)
    # Issue 72: Include INSTANCE nodes as they can have children and create flat structures
    if node_type in ('FRAME', 'GROUP', 'COMPONENT', 'INSTANCE', 'SECTION') and len(children) > FLAT_THRESHOLD:
        stats['flat_sections'] += 1

    # Check deep nesting — only count container nodes at deep levels.
    # Leaf nodes (TEXT, RECTANGLE, etc.) inside deep structures are not counted
    # to avoid inflating the metric (Issue 5).
    # Issue 72: Include INSTANCE nodes as they can create deep nesting
    if (section_depth is not None
        and section_depth > DEEP_NESTING_THRESHOLD
        and node_type in ('FRAME', 'GROUP', 'COMPONENT', 'INSTANCE', 'SECTION')):
        stats['deep_nesting'] += 1

    # Check Auto Layout (frames without layoutMode)
    if node_type == 'FRAME' and not node.get('layoutMode'):
        stats['no_autolayout'] += 1
        stats['frames'] += 1
    elif node_type == 'FRAME':
        stats['frames'] += 1

    # Recurse children
    child_section_depth = (section_depth + 1) if section_depth is not None else None
    for child in children:
        child_stats = count_nodes(child, depth + 1, child_section_depth)
        stats['total'] += child_stats['total']
        stats['unnamed'] += child_stats['unnamed']
        stats['flat_sections'] += child_stats['flat_sections']
        stats['deep_nesting'] += child_stats['deep_nesting']
        stats['no_autolayout'] += child_stats['no_autolayout']
        stats['frames'] += child_stats['frames']
        stats['max_depth'] = max(stats['max_depth'], child_stats['max_depth'])
        stats['max_section_depth'] = max(stats['max_section_depth'], child_stats['max_section_depth'])  # Issue 71
        stats['unnamed_names'].extend(child_stats['unnamed_names'])

    return stats

def detect_grouping_candidates(node):
    \"\"\"Detect sibling elements that could be grouped (simplified heuristic for scoring).

    Note (Issue 40): This is an intentionally simplified version for Phase 1 scoring.
    Phase 2 (detect-grouping-candidates.sh) uses full Union-Find proximity + pattern hash.
    The simplification is acceptable because ungrouped_candidates has the lowest
    weight in scoring (cap=10, weight=1).
    \"\"\"
    candidates = 0
    children = node.get('children', [])

    if len(children) >= 3:
        # Check for repeated similar structures
        type_counts = {}
        for child in children:
            ctype = child.get('type', '')
            cchildren_count = len(child.get('children', []))
            key = f'{ctype}_{cchildren_count}'
            type_counts[key] = type_counts.get(key, 0) + 1

        for count in type_counts.values():
            if count >= 3:
                candidates += 1

    for child in children:
        candidates += detect_grouping_candidates(child)

    return candidates

try:
    with open(sys.argv[2], 'r') as f:
        data = json.load(f)

    root = get_root_node(data)
    resolve_absolute_coords(root)
    stats = count_nodes(root)
    ungrouped = detect_grouping_candidates(root)

    # Calculate quality score
    total = max(stats['total'], 1)
    unnamed_rate = (stats['unnamed'] / total) * 100

    # NOTE: Auto Layout metric excluded from scoring.
    # get_metadata API does not return layoutMode attribute,
    # so no_autolayout is always inaccurate. Kept as reference only.
    score = 100.0
    score -= min(30, unnamed_rate * 0.5)
    score -= min(20, stats['flat_sections'] * 5)
    score -= min(10, ungrouped * 1)  # cap=10, weight=1 (grouping is least reliable metric)
    score -= min(15, stats['deep_nesting'] * 3)
    # autolayout_penalty removed — unmeasurable via get_metadata
    score = max(0, round(score, 1))

    # Grade
    if score >= 80:
        grade = 'A'
        recommendation = 'Proceed to /figma-analyze directly'
    elif score >= 60:
        grade = 'B'
        recommendation = 'Phase 2 (grouping) recommended'
    elif score >= 40:
        grade = 'C'
        recommendation = 'Phase 2 + 3 (grouping + rename) recommended'
    elif score >= 20:
        grade = 'D'
        recommendation = 'All phases recommended'
    else:
        grade = 'F'
        recommendation = 'All phases recommended + manual review'

    result = {
        'score': score,
        'grade': grade,
        'recommendation': recommendation,
        'metrics': {
            'total_nodes': stats['total'],
            'unnamed_nodes': stats['unnamed'],
            'unnamed_rate_pct': round(unnamed_rate, 1),
            'flat_sections': stats['flat_sections'],
            'ungrouped_candidates': ungrouped,
            'deep_nesting_count': stats['deep_nesting'],
            'no_autolayout_frames': stats['no_autolayout'],
            'total_frames': stats['frames'],
            'max_depth': stats['max_depth'],
            'max_section_depth': stats['max_section_depth'],  # Issue 71: relative depth used for nesting scoring
        },
        'score_breakdown': {
            'unnamed_penalty': round(min(30, unnamed_rate * 0.5), 1),
            'flat_penalty': min(20, stats['flat_sections'] * 5),
            'ungrouped_penalty': min(10, ungrouped * 1),
            'nesting_penalty': min(15, stats['deep_nesting'] * 3),
            'autolayout_penalty': 0,  # unmeasurable via get_metadata — excluded from score
        },
        'sample_unnamed': stats['unnamed_names'][:10],
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))

except Exception as e:
    print(json.dumps({'error': str(e)}), file=sys.stderr)
    sys.exit(1)
" "${SCRIPT_DIR}/.." "$1"

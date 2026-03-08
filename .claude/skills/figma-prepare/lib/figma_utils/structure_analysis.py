"""Structure quality analysis for figma-prepare Phase 1.

Analyzes Figma structure and computes quality scores, grades, and issue breakdowns.
"""

import json

from .constants import (
    UNNAMED_RE,
    FLAT_THRESHOLD,
    DEEP_NESTING_THRESHOLD,
    OFF_CANVAS_MARGIN,
)
from .geometry import get_bbox, resolve_absolute_coords
from .metadata import (
    get_root_node,
    load_metadata,
    is_section_root,
    is_off_canvas,
    count_nested_flat,
)


def count_nodes(node, depth=0, section_depth=None, page_width=0, root_x=0):
    """Recursively count nodes and collect metrics.

    depth: absolute depth from root (for reference)
    section_depth: relative depth from nearest section root (for nesting check)
    page_width: width of the page root (for off-canvas detection, Issue 182)
    root_x: X offset of root artboard (for off-canvas coordinate correction)
    """
    stats = {
        'total': 0,
        'unnamed': 0,
        'flat_sections': 0,
        'flat_excess': 0,  # Issue 89: sum of (child_count - threshold) for flat sections
        'deep_nesting': 0,
        'no_autolayout': 0,
        'max_depth': depth,
        'max_section_depth': section_depth if section_depth is not None else 0,  # Issue 71
        'frames': 0,
        'unnamed_names': [],
        'hidden_nodes': 0,  # Issue 187: count of hidden nodes skipped
        'off_canvas_nodes': 0,  # Issue 182: count of off-canvas nodes skipped
    }

    # Issue 187: Skip hidden (visible: false) nodes entirely
    if node.get('visible') == False:
        stats['hidden_nodes'] = 1
        return stats

    # Issue 182: Skip off-canvas nodes at top level (direct children of root)
    if page_width > 0 and depth == 1 and is_off_canvas(node, page_width, root_x=root_x):
        stats['off_canvas_nodes'] = 1
        return stats

    name = node.get('name', '')
    node_type = node.get('type', '')
    all_children = node.get('children', [])
    children = [c for c in all_children if c.get('visible') != False]

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
        stats['flat_excess'] += len(children) - FLAT_THRESHOLD  # Issue 89

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

    # Recurse all children (including hidden) to count hidden_nodes correctly
    child_section_depth = (section_depth + 1) if section_depth is not None else None
    for child in all_children:
        child_stats = count_nodes(child, depth + 1, child_section_depth, page_width, root_x)
        stats['total'] += child_stats['total']
        stats['unnamed'] += child_stats['unnamed']
        stats['flat_sections'] += child_stats['flat_sections']
        stats['flat_excess'] += child_stats['flat_excess']  # Issue 89
        stats['deep_nesting'] += child_stats['deep_nesting']
        stats['no_autolayout'] += child_stats['no_autolayout']
        stats['frames'] += child_stats['frames']
        stats['max_depth'] = max(stats['max_depth'], child_stats['max_depth'])
        stats['max_section_depth'] = max(stats['max_section_depth'], child_stats['max_section_depth'])  # Issue 71
        stats['unnamed_names'].extend(child_stats['unnamed_names'])
        stats['hidden_nodes'] += child_stats['hidden_nodes']  # Issue 187
        stats['off_canvas_nodes'] += child_stats['off_canvas_nodes']  # Issue 182

    return stats


def detect_grouping_candidates_simple(node):
    """Detect sibling elements that could be grouped (simplified heuristic for scoring).

    Note (Issue 40): This is an intentionally simplified version for Phase 1 scoring.
    Phase 2 (detect-grouping-candidates.sh) uses full Union-Find proximity + pattern hash.
    The simplification is acceptable because ungrouped_candidates has the lowest
    weight in scoring (cap=10, weight=1).
    """
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
        candidates += detect_grouping_candidates_simple(child)

    return candidates


def run_structure_analysis(metadata_path):
    """Main entry point for structure quality analysis.

    Args:
        metadata_path: Path to Figma metadata JSON file.

    Returns:
        JSON string with quality score, grade, and issue breakdown.
    """
    import sys
    sys.setrecursionlimit(3000)  # Guard against deeply nested Figma files (Issue 48)

    data = load_metadata(metadata_path)
    root = get_root_node(data)
    resolve_absolute_coords(root)
    # Issue 182: Determine page width for off-canvas detection
    root_bb = get_bbox(root)
    page_width = root_bb.get('w', 0) if root_bb else 0
    root_x = root_bb.get('x', 0) if root_bb else 0
    stats = count_nodes(root, page_width=page_width, root_x=root_x)
    ungrouped = detect_grouping_candidates_simple(root)
    # Issue 228: Count all FRAME/GROUP nodes at any level with >FLAT_THRESHOLD visible children
    nested_flat = count_nested_flat(root)

    # Calculate quality score
    total = max(stats['total'], 1)
    unnamed_rate = (stats['unnamed'] / total) * 100

    # NOTE: Auto Layout metric excluded from scoring.
    # get_metadata API does not return layoutMode attribute,
    # so no_autolayout is always inaccurate. Kept as reference only.
    score = 100.0
    score -= min(30, unnamed_rate * 0.5)
    # Issue 89: flat_penalty accounts for both count and severity (excess children)
    # Issue 188: cap raised from 30 -> 40
    score -= min(40, stats['flat_sections'] * 5 + stats['flat_excess'] * 0.5)
    score -= min(10, ungrouped * 1)  # cap=10, weight=1 (grouping is least reliable metric)
    score -= min(15, stats['deep_nesting'] * 3)
    # autolayout_penalty removed — unmeasurable via get_metadata
    # Issue 228: nested_flat_count is informational only (not in score yet).
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
            'named_rate_pct': round(100 - unnamed_rate, 1),  # Issue 188
            'flat_sections': stats['flat_sections'],
            'ungrouped_candidates': ungrouped,
            'deep_nesting_count': stats['deep_nesting'],
            'no_autolayout_frames': stats['no_autolayout'],
            'total_frames': stats['frames'],
            'max_depth': stats['max_depth'],
            'max_section_depth': stats['max_section_depth'],  # Issue 71
            'hidden_nodes': stats['hidden_nodes'],  # Issue 187
            'off_canvas_nodes': stats['off_canvas_nodes'],  # Issue 182
            'nested_flat_count': nested_flat,  # Issue 228
        },
        'score_breakdown': {
            'unnamed_penalty': round(min(30, unnamed_rate * 0.5), 1),
            'flat_penalty': round(min(40, stats['flat_sections'] * 5 + stats['flat_excess'] * 0.5), 1),  # Issue 105, 188
            'ungrouped_penalty': min(10, ungrouped * 1),
            'nesting_penalty': min(15, stats['deep_nesting'] * 3),
            'autolayout_penalty': 0,  # unmeasurable via get_metadata — excluded from score
        },
        'sample_unnamed': stats['unnamed_names'][:10],
    }

    return json.dumps(result, indent=2, ensure_ascii=False)

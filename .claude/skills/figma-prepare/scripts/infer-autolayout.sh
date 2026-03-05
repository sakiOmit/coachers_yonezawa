#!/usr/bin/env bash
# Phase 4: Infer Auto Layout Settings
#
# Usage: bash infer-autolayout.sh <metadata.json> [--output autolayout-plan.yaml]
# Input: Figma get_metadata output (JSON)
# Output: JSON/YAML with Auto Layout settings per frame
# Exit: 0=success, 1=error

set -euo pipefail

if [[ $# -lt 1 ]] || [[ ! -f "$1" ]]; then
  echo '{"error": "Usage: infer-autolayout.sh <metadata.json> [--output file.yaml]"}' >&2
  exit 1
fi

OUTPUT_FILE=""
if [[ "${2:-}" == "--output" ]] && [[ -n "${3:-}" ]]; then
  OUTPUT_FILE="$3"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 -c "
import json, sys, statistics, os
sys.setrecursionlimit(3000)  # Guard against deeply nested Figma files (Issue 48)
sys.path.insert(0, os.path.join(sys.argv[1], 'lib'))
from figma_utils import (resolve_absolute_coords, get_bbox, get_root_node, yaml_str, snap, GRID_SNAP,
    ROW_TOLERANCE, infer_direction_two_elements, detect_wrap, detect_space_between, compute_gap_consistency,
    CENTER_ALIGN_VARIANCE, ALIGN_TOLERANCE, CONFIDENCE_HIGH_COV, CONFIDENCE_MEDIUM_COV)

VARIANCE_RATIO = 1.5

def infer_layout(frame):
    \"\"\"Infer Auto Layout settings for a frame.\"\"\"
    children = frame.get('children', [])
    if len(children) < 2:
        return None

    frame_bb = get_bbox(frame)
    child_bboxes = [get_bbox(c) for c in children]

    # Skip if frame has no meaningful size
    if frame_bb['w'] <= 0 or frame_bb['h'] <= 0:
        return None

    # Direction inference
    xs = [bb['x'] for bb in child_bboxes]
    ys = [bb['y'] for bb in child_bboxes]

    if len(set(xs)) <= 1 and len(set(ys)) <= 1:
        return None  # All at same position, can't infer

    # Use specialized 2-element direction inference
    if len(children) == 2:
        direction = infer_direction_two_elements(child_bboxes[0], child_bboxes[1])
    else:
        x_var = statistics.variance(xs) if len(xs) > 1 else 0
        y_var = statistics.variance(ys) if len(ys) > 1 else 0

        if x_var > y_var * VARIANCE_RATIO:
            direction = 'HORIZONTAL'
        else:
            direction = 'VERTICAL'

    # Sort by primary axis
    if direction == 'HORIZONTAL':
        sorted_bboxes = sorted(child_bboxes, key=lambda b: b['x'])
    else:
        sorted_bboxes = sorted(child_bboxes, key=lambda b: b['y'])

    # Check for WRAP (before gap calculation)
    is_wrap = detect_wrap(child_bboxes, direction)
    if is_wrap:
        direction = 'WRAP'

    # Gap inference
    if is_wrap:
        # For WRAP, calculate gap within rows only
        rows = {}
        for bb in child_bboxes:
            row_key = round(bb['y'] / ROW_TOLERANCE)  # Issue 131: use shared constant
            rows.setdefault(row_key, []).append(bb)
        gaps = []
        for row_bbs in rows.values():
            row_sorted = sorted(row_bbs, key=lambda b: b['x'])
            for i in range(len(row_sorted) - 1):
                g = row_sorted[i+1]['x'] - (row_sorted[i]['x'] + row_sorted[i]['w'])
                gaps.append(max(0, g))
    else:
        gaps = []
        for i in range(len(sorted_bboxes) - 1):
            curr = sorted_bboxes[i]
            nxt = sorted_bboxes[i + 1]
            if direction == 'HORIZONTAL':
                gap = nxt['x'] - (curr['x'] + curr['w'])
            else:
                gap = nxt['y'] - (curr['y'] + curr['h'])
            gaps.append(max(0, gap))

    item_gap = snap(statistics.median(gaps)) if gaps else 0

    # Gap consistency for confidence
    gap_cov = compute_gap_consistency(gaps)

    # Padding inference
    min_child_x = min(bb['x'] for bb in child_bboxes)
    min_child_y = min(bb['y'] for bb in child_bboxes)
    max_child_x = max(bb['x'] + bb['w'] for bb in child_bboxes)
    max_child_y = max(bb['y'] + bb['h'] for bb in child_bboxes)

    padding_top = snap(max(0, min_child_y - frame_bb['y']))
    padding_left = snap(max(0, min_child_x - frame_bb['x']))
    padding_bottom = snap(max(0, (frame_bb['y'] + frame_bb['h']) - max_child_y))
    padding_right = snap(max(0, (frame_bb['x'] + frame_bb['w']) - max_child_x))

    # Primary axis alignment
    primary_align = 'MIN'  # default
    if detect_space_between(child_bboxes, direction, frame_bb):
        primary_align = 'SPACE_BETWEEN'

    # Counter axis alignment
    # Issue 104: Use 'MAX' instead of 'END' to match Figma Plugin API terminology
    # Figma's counterAxisAlignItems only accepts: MIN, CENTER, MAX
    if direction in ('HORIZONTAL', 'WRAP'):
        centers = [bb['y'] + bb['h'] / 2 for bb in child_bboxes]
        center_var = statistics.variance(centers) if len(centers) > 1 else 0
        if center_var < CENTER_ALIGN_VARIANCE:
            counter_align = 'CENTER'
        elif all(abs((bb['y'] + bb['h']) - (child_bboxes[0]['y'] + child_bboxes[0]['h'])) < ALIGN_TOLERANCE for bb in child_bboxes):
            counter_align = 'MAX'
        elif all(abs(bb['y'] - child_bboxes[0]['y']) < ALIGN_TOLERANCE for bb in child_bboxes):
            counter_align = 'MIN'
        else:
            counter_align = 'MIN'
    else:
        centers = [bb['x'] + bb['w'] / 2 for bb in child_bboxes]
        center_var = statistics.variance(centers) if len(centers) > 1 else 0
        if center_var < CENTER_ALIGN_VARIANCE:
            counter_align = 'CENTER'
        elif all(abs((bb['x'] + bb['w']) - (child_bboxes[0]['x'] + child_bboxes[0]['w'])) < ALIGN_TOLERANCE for bb in child_bboxes):
            counter_align = 'MAX'
        elif all(abs(bb['x'] - child_bboxes[0]['x']) < ALIGN_TOLERANCE for bb in child_bboxes):
            counter_align = 'MIN'
        else:
            counter_align = 'MIN'

    # Confidence based on gap consistency
    if len(children) == 2:
        confidence = 'medium'
    elif gap_cov < CONFIDENCE_HIGH_COV:
        confidence = 'high'
    elif gap_cov < CONFIDENCE_MEDIUM_COV:
        confidence = 'medium'
    else:
        confidence = 'low'

    return {
        'direction': direction,
        'gap': item_gap,
        'padding': {
            'top': padding_top,
            'right': padding_right,
            'bottom': padding_bottom,
            'left': padding_left,
        },
        'primary_axis_align': primary_align,
        'counter_axis_align': counter_align,
        'confidence': confidence,
    }

def layout_from_enrichment(frame):
    \"\"\"Extract Auto Layout settings from enriched metadata (Issue 18).
    Returns layout dict if layoutMode is present, None otherwise.
    Issue 132: Handles layoutWrap='WRAP' by converting direction to 'WRAP'.\"\"\"
    layout_mode = frame.get('layoutMode')
    if not layout_mode:
        return None

    direction = layout_mode  # HORIZONTAL or VERTICAL
    # Issue 132: Check for WRAP layout
    if frame.get('layoutWrap') == 'WRAP':
        direction = 'WRAP'
    # Issue 63: Do not snap exact Figma values — preserve original design intent
    item_gap = int(frame.get('itemSpacing', 0))
    padding = {
        'top': int(frame.get('paddingTop', 0)),
        'right': int(frame.get('paddingRight', 0)),
        'bottom': int(frame.get('paddingBottom', 0)),
        'left': int(frame.get('paddingLeft', 0)),
    }
    primary_align = frame.get('primaryAxisAlignItems', 'MIN')
    counter_align = frame.get('counterAxisAlignItems', 'MIN')

    return {
        'direction': direction,
        'gap': item_gap,
        'padding': padding,
        'primary_axis_align': primary_align,
        'counter_axis_align': counter_align,
        'confidence': 'exact',  # from actual Figma data, not inferred
    }

def walk_and_infer(node, results=None):
    \"\"\"Walk tree and infer Auto Layout for eligible frames.\"\"\"
    if results is None:
        results = []

    node_type = node.get('type', '')
    children = node.get('children', [])

    # Issue 69: Include INSTANCE/COMPONENT nodes for Auto Layout inference
    if node_type in ('FRAME', 'INSTANCE', 'COMPONENT', 'SECTION') and len(children) >= 2:
        # Issue 18: Use enriched layoutMode if available
        layout = layout_from_enrichment(node)
        source = None  # Issue 95: Initialize before conditional assignment
        # Issue 70, 75: Set source based on actual data origin
        # 'exact' = from Figma layoutMode (base or enriched metadata)
        # 'inferred' = calculated from child positions
        if layout:
            source = 'exact'
        elif not node.get('layoutMode'):
            # No layoutMode in metadata — fallback to inference
            layout = infer_layout(node)
            source = 'inferred'

        if layout:
            # Issue 126: INSTANCE/COMPONENT are read-only in Figma Plugin API
            # Include in output for informational purposes but flag as non-applicable
            applicable = node_type == 'FRAME'
            results.append({
                'node_id': node.get('id', ''),
                'node_name': node.get('name', ''),
                'node_type': node_type,
                'child_count': len(children),
                'layout': layout,
                'source': source,
                'applicable': applicable,
            })

    for child in children:
        walk_and_infer(child, results)

    return results

try:
    with open(sys.argv[2], 'r') as f:
        data = json.load(f)

    root = get_root_node(data)
    resolve_absolute_coords(root)
    results = walk_and_infer(root)

    output_file = sys.argv[3] if len(sys.argv) > 3 else ''

    if output_file:
        with open(output_file, 'w') as f:
            f.write('# Figma Auto Layout Plan\\n')
            f.write(f'# Total frames: {len(results)}\\n')
            f.write('# Generated by /figma-prepare Phase 4\\n')
            f.write('# Review before applying with --apply\\n\\n')
            f.write('frames:\\n')
            for r in results:
                f.write(f'  - node_id: {yaml_str(r[\"node_id\"])}\\n')
                f.write(f'    name: {yaml_str(r[\"node_name\"])}\\n')
                f.write(f'    node_type: {r.get(\"node_type\", \"FRAME\")}\\n')
                f.write(f'    children: {r[\"child_count\"]}\\n')
                f.write(f'    direction: {r[\"layout\"][\"direction\"]}\\n')
                f.write(f'    gap: {r[\"layout\"][\"gap\"]}\\n')
                p = r['layout']['padding']
                f.write(f'    padding: [{p[\"top\"]}, {p[\"right\"]}, {p[\"bottom\"]}, {p[\"left\"]}]\\n')
                f.write(f'    primary_axis_align: {r[\"layout\"][\"primary_axis_align\"]}\\n')
                f.write(f'    counter_axis_align: {r[\"layout\"][\"counter_axis_align\"]}\\n')
                f.write(f'    confidence: {r[\"layout\"][\"confidence\"]}\\n')
                f.write(f'    source: {r[\"source\"]}\\n')  # Issue 74: include source in YAML output
                if not r.get('applicable', True):
                    f.write(f'    applicable: false  # {r.get(\"node_type\", \"\")} — read-only in Plugin API\\n')
        print(json.dumps({
            'total': len(results),
            'output': output_file,
            'status': 'dry-run'
        }, indent=2))
    else:
        print(json.dumps({
            'total': len(results),
            'frames': results,
            'status': 'dry-run'
        }, indent=2, ensure_ascii=False))

except Exception as e:
    print(json.dumps({'error': str(e)}), file=sys.stderr)
    sys.exit(1)
" "${SCRIPT_DIR}/.." "$1" "$OUTPUT_FILE"

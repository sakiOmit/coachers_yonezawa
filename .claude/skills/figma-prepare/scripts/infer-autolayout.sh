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

python3 -c "
import json, sys, statistics

GRID_SNAP = 4  # px
VARIANCE_RATIO = 1.5

def resolve_absolute_coords(node, parent_x=0, parent_y=0):
    \"\"\"Convert parent-relative coordinates to absolute coordinates.\"\"\"
    bbox = node.get('absoluteBoundingBox', {})
    abs_x = parent_x + bbox.get('x', 0)
    abs_y = parent_y + bbox.get('y', 0)
    bbox['x'] = abs_x
    bbox['y'] = abs_y
    node['absoluteBoundingBox'] = bbox
    for child in node.get('children', []):
        resolve_absolute_coords(child, abs_x, abs_y)

def snap(value):
    \"\"\"Snap value to grid.\"\"\"
    return round(value / GRID_SNAP) * GRID_SNAP

def get_bbox(node):
    bbox = node.get('absoluteBoundingBox', {})
    return {
        'x': bbox.get('x', 0),
        'y': bbox.get('y', 0),
        'w': bbox.get('width', 0),
        'h': bbox.get('height', 0),
    }

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

    x_var = statistics.variance(xs) if len(xs) > 1 else 0
    y_var = statistics.variance(ys) if len(ys) > 1 else 0

    if x_var > y_var * VARIANCE_RATIO:
        direction = 'HORIZONTAL'
        # Sort by X position
        sorted_bboxes = sorted(child_bboxes, key=lambda b: b['x'])
    else:
        direction = 'VERTICAL'
        # Sort by Y position
        sorted_bboxes = sorted(child_bboxes, key=lambda b: b['y'])

    # Gap inference
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
    if direction == 'HORIZONTAL':
        # Check if children are vertically centered
        centers = [bb['y'] + bb['h'] / 2 for bb in child_bboxes]
        center_var = statistics.variance(centers) if len(centers) > 1 else 0
        primary_align = 'MIN'  # default
        counter_align = 'CENTER' if center_var < 4 else 'MIN'
    else:
        centers = [bb['x'] + bb['w'] / 2 for bb in child_bboxes]
        center_var = statistics.variance(centers) if len(centers) > 1 else 0
        primary_align = 'MIN'
        # Check horizontal alignment
        if center_var < 4:
            counter_align = 'CENTER'
        elif all(abs(bb['x'] - child_bboxes[0]['x']) < 2 for bb in child_bboxes):
            counter_align = 'MIN'
        else:
            counter_align = 'MIN'

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
        'confidence': 'high' if len(children) >= 3 else 'medium',
    }

def layout_from_enrichment(frame):
    \"\"\"Extract Auto Layout settings from enriched metadata (Issue 18).
    Returns layout dict if layoutMode is present, None otherwise.\"\"\"
    layout_mode = frame.get('layoutMode')
    if not layout_mode:
        return None

    direction = layout_mode  # HORIZONTAL or VERTICAL
    item_gap = snap(frame.get('itemSpacing', 0))
    padding = {
        'top': snap(frame.get('paddingTop', 0)),
        'right': snap(frame.get('paddingRight', 0)),
        'bottom': snap(frame.get('paddingBottom', 0)),
        'left': snap(frame.get('paddingLeft', 0)),
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

    if node_type == 'FRAME' and len(children) >= 2:
        # Issue 18: Use enriched layoutMode if available
        layout = layout_from_enrichment(node)
        source = 'enriched'
        if not layout and not node.get('layoutMode'):
            # Fallback to inference
            layout = infer_layout(node)
            source = 'inferred'

        if layout:
            results.append({
                'node_id': node.get('id', ''),
                'node_name': node.get('name', ''),
                'child_count': len(children),
                'layout': layout,
                'source': source,
            })

    for child in children:
        walk_and_infer(child, results)

    return results

try:
    with open(sys.argv[1], 'r') as f:
        data = json.load(f)

    root = data
    if 'document' in data:
        root = data['document']
    elif 'node' in data:
        root = data['node']

    resolve_absolute_coords(root)
    results = walk_and_infer(root)

    output_file = '${OUTPUT_FILE}'

    if output_file:
        with open(output_file, 'w') as f:
            f.write('# Figma Auto Layout Plan\\n')
            f.write(f'# Total frames: {len(results)}\\n')
            f.write('# Generated by /figma-prepare Phase 4\\n')
            f.write('# Review before applying with --apply\\n\\n')
            f.write('frames:\\n')
            for r in results:
                f.write(f'  - node_id: \"{r[\"node_id\"]}\"\\n')
                f.write(f'    name: \"{r[\"node_name\"]}\"\\n')
                f.write(f'    children: {r[\"child_count\"]}\\n')
                f.write(f'    direction: {r[\"layout\"][\"direction\"]}\\n')
                f.write(f'    gap: {r[\"layout\"][\"gap\"]}\\n')
                p = r['layout']['padding']
                f.write(f'    padding: [{p[\"top\"]}, {p[\"right\"]}, {p[\"bottom\"]}, {p[\"left\"]}]\\n')
                f.write(f'    counter_align: {r[\"layout\"][\"counter_axis_align\"]}\\n')
                f.write(f'    confidence: {r[\"layout\"][\"confidence\"]}\\n')
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
" "$1"

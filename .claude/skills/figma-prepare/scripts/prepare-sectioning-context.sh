#!/usr/bin/env bash
# Phase 2 Stage B: Prepare Sectioning Context
#
# Extracts top-level children summary from metadata JSON for Claude sectioning.
# Output: JSON with page info, sorted children (Y ascending), and heuristic hints.
#
# Usage: bash prepare-sectioning-context.sh <metadata.json> [--output file.json]
# Exit: 0=success, 1=error

set -euo pipefail

if [[ $# -lt 1 ]] || [[ ! -f "$1" ]]; then
  echo '{"error": "Usage: prepare-sectioning-context.sh <metadata.json> [--output file.json]"}' >&2
  exit 1
fi

OUTPUT_FILE=""
if [[ "${2:-}" == "--output" ]] && [[ -n "${3:-}" ]]; then
  OUTPUT_FILE="$3"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 -c "
import json, sys, re
sys.path.insert(0, '${SCRIPT_DIR}/../lib')
from figma_utils import resolve_absolute_coords, get_root_node, UNNAMED_RE

def get_bbox(node):
    \"\"\"Get bounding box with full key names (width/height) for output compatibility.\"\"\"
    bbox = node.get('absoluteBoundingBox', {})
    return {
        'x': bbox.get('x', 0),
        'y': bbox.get('y', 0),
        'width': bbox.get('width', 0),
        'height': bbox.get('height', 0),
    }

def count_children(node):
    return len(node.get('children', []))

def get_child_types_summary(node):
    \"\"\"Get summary of child types like 'RECTANGLE:2, FRAME:2'.\"\"\"
    children = node.get('children', [])
    if not children:
        return ''
    from collections import Counter
    types = Counter(c.get('type', 'UNKNOWN') for c in children)
    return ', '.join(f'{t}:{n}' for t, n in sorted(types.items()))

def has_text_children(node):
    children = node.get('children', [])
    return any(c.get('type') == 'TEXT' for c in children)

def get_text_children_preview(node, max_items=5):
    \"\"\"Get preview of text content from direct TEXT children.\"\"\"
    children = node.get('children', [])
    texts = []
    for c in children:
        if c.get('type') == 'TEXT':
            name = c.get('name', '')
            chars = c.get('characters', '')
            texts.append(chars if chars else name)
    return texts[:max_items]

def collect_all_text(node, depth=0, max_depth=3):
    \"\"\"Recursively collect text from children up to max_depth.\"\"\"
    texts = []
    if depth > max_depth:
        return texts
    for c in node.get('children', []):
        if c.get('type') == 'TEXT':
            name = c.get('name', '')
            chars = c.get('characters', '')
            texts.append(chars if chars else name)
        else:
            texts.extend(collect_all_text(c, depth + 1, max_depth))
    return texts

def detect_heuristic_hints(children, page_bbox):
    \"\"\"Detect header/footer/page-kv candidates from top-level children.\"\"\"
    page_h = page_bbox.get('height', 0)
    page_y = page_bbox.get('y', 0)
    page_w = page_bbox.get('width', 0)
    if page_h <= 0:
        return {'header_candidates': [], 'footer_candidates': [], 'page_kv_candidates': []}

    upper_threshold = page_y + page_h * 0.3

    header_candidates = []
    footer_candidates = []
    page_kv_candidates = []

    # Sort by Y for analysis
    sorted_children = sorted(children, key=lambda c: get_bbox(c).get('y', 0))

    for child in sorted_children:
        bb = get_bbox(child)
        node_type = child.get('type', '')
        node_name = child.get('name', '')
        node_id = child.get('id', '')

        # Header: top area, wide frame
        if bb['y'] < page_y + page_h * 0.05:
            if node_type in ('FRAME', 'GROUP') and bb['width'] > page_w * 0.8:
                header_candidates.append(node_id)

        # Footer: bottom area, wide frame
        if bb['y'] + bb['height'] > page_y + page_h * 0.9:
            if node_type in ('FRAME', 'GROUP') and bb['width'] > page_w * 0.8:
                footer_candidates.append(node_id)

        # Page KV: upper 30%, breadcrumb or heading
        if bb['y'] <= upper_threshold:
            # Breadcrumb: TEXT with '>'
            if node_type == 'TEXT':
                check_text = child.get('characters', '') or node_name
                if '>' in check_text or '\\u203a' in check_text:
                    page_kv_candidates.append(node_id)
                    continue

            # Heading: FRAME with 2+ TEXT children
            if node_type in ('FRAME', 'GROUP'):
                sub = child.get('children', [])
                text_count = sum(1 for c in sub if c.get('type') == 'TEXT')
                if text_count >= 2:
                    page_kv_candidates.append(node_id)
                    continue

    return {
        'header_candidates': header_candidates,
        'footer_candidates': footer_candidates,
        'page_kv_candidates': page_kv_candidates,
    }

try:
    with open(sys.argv[1], 'r') as f:
        data = json.load(f)

    root = get_root_node(data)
    resolve_absolute_coords(root)

    page_bbox = get_bbox(root)
    children = root.get('children', [])

    # Sort by Y ascending
    sorted_children = sorted(children, key=lambda c: get_bbox(c).get('y', 0))

    # Build top_level_children summary
    top_level = []
    for child in sorted_children:
        bb = get_bbox(child)
        child_info = {
            'id': child.get('id', ''),
            'name': child.get('name', ''),
            'type': child.get('type', ''),
            'bbox': bb,
            'child_count': count_children(child),
            'child_types_summary': get_child_types_summary(child),
            'has_text_children': has_text_children(child),
            'text_children_preview': get_text_children_preview(child),
            'is_unnamed': bool(UNNAMED_RE.match(child.get('name', ''))),
        }
        top_level.append(child_info)

    # Heuristic hints
    hints = detect_heuristic_hints(children, page_bbox)

    result = {
        'page_name': root.get('name', ''),
        'page_id': root.get('id', ''),
        'page_size': {
            'width': page_bbox.get('width', 0),
            'height': page_bbox.get('height', 0),
        },
        'top_level_children': top_level,
        'total_children': len(sorted_children),
        'heuristic_hints': hints,
    }

    output_file = '${OUTPUT_FILE}'
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(json.dumps({
            'status': 'ok',
            'output': output_file,
            'total_children': len(sorted_children),
        }, indent=2))
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))

except Exception as e:
    print(json.dumps({'error': str(e)}), file=sys.stderr)
    sys.exit(1)
" "$1"

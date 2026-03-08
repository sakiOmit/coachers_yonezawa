#!/usr/bin/env bash
# Phase 2 Stage B: Prepare Sectioning Context
#
# Extracts top-level children summary from metadata JSON for Claude sectioning.
# Output: JSON with page info, sorted children (Y ascending), and heuristic hints.
#
# Usage: bash prepare-sectioning-context.sh <metadata.json> [--output file.json] [--enriched-table]
# Exit: 0=success, 1=error

set -euo pipefail

if [[ $# -lt 1 ]] || [[ ! -f "$1" ]]; then
  echo '{"error": "Usage: prepare-sectioning-context.sh <metadata.json> [--output file.json] [--enriched-table]"}' >&2
  exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE=""
ENRICHED_TABLE=""

# Parse optional flags (order-independent)
shift  # consume the positional metadata.json argument
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      OUTPUT_FILE="${2:-}"
      shift 2
      ;;
    --enriched-table)
      ENRICHED_TABLE="1"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 -c "
import json, sys, os
from collections import Counter
sys.setrecursionlimit(3000)  # Guard against deeply nested Figma files (Issue 48)
sys.path.insert(0, os.path.join(sys.argv[1], 'lib'))
from figma_utils import (resolve_absolute_coords, get_bbox, get_root_node, load_metadata, UNNAMED_RE,
    get_text_children_content, structure_hash, structure_similarity, is_heading_like,
    generate_enriched_table,
    HINT_HEADER_Y_RATIO, HINT_FOOTER_Y_RATIO, HINT_WIDE_ELEMENT_RATIO,
    HINT_BG_MIN_HEIGHT, HINT_HEADING_MAX_HEIGHT,
    HEADER_ZONE_HEIGHT, FOOTER_ZONE_MARGIN, NAV_MAX_TEXT_LEN, HEADER_NAV_MIN_TEXTS,
    JACCARD_THRESHOLD, CONSECUTIVE_PATTERN_MIN, LOOSE_ELEMENT_MAX_HEIGHT)

def count_children(node):
    return len([c for c in node.get('children', []) if c.get('visible') != False])

def get_child_types_summary(node):
    \"\"\"Get summary of child types like 'RECTANGLE:2, FRAME:2'.\"\"\"
    children = [c for c in node.get('children', []) if c.get('visible') != False]
    if not children:
        return ''
    types = Counter(c.get('type', 'UNKNOWN') for c in children)
    return ', '.join(f'{t}:{n}' for t, n in sorted(types.items()))

def has_text_children(node):
    children = [c for c in node.get('children', []) if c.get('visible') != False]
    return any(c.get('type') == 'TEXT' for c in children)

def get_text_children_preview(node, max_items=5):
    \"\"\"Get preview of text content from direct TEXT children.
    Delegates to shared util (Issue 49).\"\"\"
    return get_text_children_content(node.get('children', []), max_items=max_items)

def detect_heuristic_hints(children, page_bbox):
    \"\"\"Detect header/footer candidates, gap analysis, and background candidates.

    Semantic understanding (page-kv, section boundaries) is delegated to Stage B Claude reasoning.
    This function provides mechanical hints to support Claude's decision-making.
    \"\"\"
    page_h = page_bbox['h']
    page_y = page_bbox['y']
    page_w = page_bbox['w']
    if page_h <= 0:
        return {
            'header_candidates': [],
            'header_cluster_ids': [],
            'footer_candidates': [],
            'gap_analysis': [],
            'background_candidates': [],
            'consecutive_patterns': [],
            'heading_candidates': [],
            'loose_elements': [],
        }

    header_candidates = []
    footer_candidates = []
    background_candidates = []

    # Sort by Y for analysis
    sorted_children = sorted(
        [c for c in children if c.get('visible') != False],
        key=lambda c: get_bbox(c).get('y', 0)
    )

    for child in sorted_children:
        bb = get_bbox(child)
        node_type = child.get('type', '')
        node_id = child.get('id', '')

        # Header: top area, wide container-like node
        # Include INSTANCE/COMPONENT/SECTION as headers/footers may be component instances
        if bb['y'] < page_y + page_h * HINT_HEADER_Y_RATIO:
            if node_type in ('FRAME', 'GROUP', 'INSTANCE', 'COMPONENT', 'SECTION') and bb['w'] > page_w * HINT_WIDE_ELEMENT_RATIO:
                header_candidates.append(node_id)

        # Footer: bottom area, wide container-like node
        if bb['y'] + bb['h'] > page_y + page_h * HINT_FOOTER_Y_RATIO:
            if node_type in ('FRAME', 'GROUP', 'INSTANCE', 'COMPONENT', 'SECTION') and bb['w'] > page_w * HINT_WIDE_ELEMENT_RATIO:
                footer_candidates.append(node_id)

        # Background candidates: RECTANGLE with significant height
        if node_type == 'RECTANGLE' and bb['h'] >= HINT_BG_MIN_HEIGHT:
            background_candidates.append(node_id)

    # Gap analysis: Y-direction gaps between consecutive children
    gap_analysis = []
    for i in range(len(sorted_children) - 1):
        curr = sorted_children[i]
        next_child = sorted_children[i + 1]
        curr_bb = get_bbox(curr)
        next_bb = get_bbox(next_child)
        curr_bottom = curr_bb['y'] + curr_bb['h']
        gap_px = round(next_bb['y'] - curr_bottom)
        gap_analysis.append({
            'between': [curr.get('id', ''), next_child.get('id', '')],
            'gap_px': gap_px,
        })

    # --- Header cluster detection for flat structures (Issue 179) ---
    # Detect a cluster of individual elements (logo + nav texts + CTA frame)
    # in the header zone. This provides extra context for Stage B even when
    # header_candidates already has entries (which may be false positives like hero).
    header_cluster_ids = []
    header_zone_top = page_y
    header_zone_bottom = page_y + HEADER_ZONE_HEIGHT
    header_zone_elements = []
    header_zone_texts = 0
    for child in sorted_children:
        bb_c = get_bbox(child)
        # Element must start within header zone and bottom within zone + 50px margin
        if bb_c['y'] >= header_zone_top and bb_c['y'] + bb_c['h'] <= header_zone_bottom + FOOTER_ZONE_MARGIN:
            header_zone_elements.append(child.get('id', ''))
            if child.get('type') == 'TEXT':
                text_content = child.get('characters', child.get('name', ''))
                if len(text_content) < NAV_MAX_TEXT_LEN:
                    header_zone_texts += 1
    if header_zone_texts >= HEADER_NAV_MIN_TEXTS and len(header_zone_elements) >= HEADER_NAV_MIN_TEXTS + 1:
        header_cluster_ids = header_zone_elements

    # --- Consecutive similar patterns ---
    # Detect runs of 3+ consecutive children with similar structure hash
    hashes = [structure_hash(c) for c in sorted_children]
    consecutive_patterns = []
    i = 0
    while i < len(sorted_children):
        run_indices = [i]
        j = i + 1
        while j < len(sorted_children):
            sim = structure_similarity(hashes[i], hashes[j])
            if sim >= JACCARD_THRESHOLD:
                run_indices.append(j)
                j += 1
            else:
                break
        if len(run_indices) >= CONSECUTIVE_PATTERN_MIN:
            consecutive_patterns.append({
                'indices': run_indices,
                'ids': [sorted_children[idx].get('id', '') for idx in run_indices],
                'names': [sorted_children[idx].get('name', '') for idx in run_indices],
                'hash': hashes[i],
            })
            i = j
        else:
            i += 1

    # --- Heading candidates ---
    # Small, text-heavy frames that likely serve as section headings
    # Height filter: headings should be compact to distinguish from card/content frames
    heading_candidates = []
    for idx, child in enumerate(sorted_children):
        bb = get_bbox(child)
        child_h = bb.get('h', 999)
        if child_h > HINT_HEADING_MAX_HEIGHT:
            continue
        if is_heading_like(child):
            heading_candidates.append({
                'index': idx,
                'id': child.get('id', ''),
                'name': child.get('name', ''),
                'height': child_h,
            })

    # --- Loose elements ---
    # LINE nodes or very small leaf elements (dividers, spacers, decorations)
    loose_elements = []
    for idx, child in enumerate(sorted_children):
        bb = get_bbox(child)
        child_type = child.get('type', '')
        if child_type == 'LINE' or (bb.get('h', 999) <= LOOSE_ELEMENT_MAX_HEIGHT and not child.get('children')):
            loose_elements.append({
                'index': idx,
                'id': child.get('id', ''),
                'name': child.get('name', ''),
                'type': child_type,
                'height': bb.get('h', 0),
            })

    return {
        'header_candidates': header_candidates,
        'header_cluster_ids': header_cluster_ids,
        'footer_candidates': footer_candidates,
        'gap_analysis': gap_analysis,
        'background_candidates': background_candidates,
        'consecutive_patterns': consecutive_patterns,
        'heading_candidates': heading_candidates,
        'loose_elements': loose_elements,
    }

try:
    data = load_metadata(sys.argv[2])
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
            'width': page_bbox['w'],
            'height': page_bbox['h'],
        },
        'top_level_children': top_level,
        'total_children': len(sorted_children),
        'heuristic_hints': hints,
    }

    # Issue 194: Generate enriched table when --enriched-table flag is set
    enriched_flag = sys.argv[4] if len(sys.argv) > 4 else ''
    if enriched_flag:
        enriched = generate_enriched_table(
            sorted_children,
            page_width=page_bbox['w'],
            page_height=page_bbox['h'],
            root_x=page_bbox.get('x', 0),
            root_y=page_bbox.get('y', 0),
        )
        result['enriched_children_table'] = enriched

    output_file = sys.argv[3] if len(sys.argv) > 3 else ''
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(json.dumps({
            'status': 'ok',
            'output': output_file,
            'total_children': len(sorted_children),
            'enriched_table': bool(enriched_flag),
        }, indent=2))
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))

except Exception as e:
    print(json.dumps({'error': str(e)}), file=sys.stderr)
    sys.exit(1)
" "${SCRIPT_DIR}/.." "$INPUT_FILE" "$OUTPUT_FILE" "$ENRICHED_TABLE"

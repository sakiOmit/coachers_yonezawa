"""Sectioning context preparation for figma-prepare Phase 2 Stage B.

Extracts top-level children summary from metadata JSON for Claude sectioning.
Produces page info, sorted children (Y ascending), heuristic hints, and
optionally an enriched children table.
"""

import json
import statistics
from collections import Counter

from .constants import (
    UNNAMED_RE,
    HINT_HEADER_Y_RATIO,
    HINT_FOOTER_Y_RATIO,
    HINT_WIDE_ELEMENT_RATIO,
    HINT_BG_MIN_HEIGHT,
    HINT_HEADING_MAX_HEIGHT,
    HEADER_ZONE_HEIGHT,
    HEADER_ZONE_MARGIN,
    NAV_MAX_TEXT_LEN,
    HEADER_NAV_MIN_TEXTS,
    JACCARD_THRESHOLD,
    CONSECUTIVE_PATTERN_MIN,
    LOOSE_ELEMENT_MAX_HEIGHT,
    scaled_threshold,
)
from .geometry import filter_visible_children, get_bbox, resolve_absolute_coords, sort_by_y
from .metadata import get_root_node, load_metadata, get_text_children_content
from .detection import is_heading_like
from .scoring import structure_hash, structure_similarity
from .enrichment import generate_enriched_table


def count_children(node):
    """Count visible children of a node."""
    return len(filter_visible_children(node))


def get_child_types_summary(node):
    """Get summary of child types like 'RECTANGLE:2, FRAME:2'."""
    children = filter_visible_children(node)
    if not children:
        return ''
    types = Counter(c.get('type', 'UNKNOWN') for c in children)
    return ', '.join(f'{t}:{n}' for t, n in sorted(types.items()))


def has_text_children(node):
    """Check if node has any direct TEXT children."""
    children = filter_visible_children(node)
    return any(c.get('type') == 'TEXT' for c in children)


def get_text_children_preview(node, max_items=5):
    """Get preview of text content from direct TEXT children.
    Delegates to shared util (Issue 49)."""
    return get_text_children_content(node.get('children', []), max_items=max_items)


def _detect_header_footer_bg(sorted_children, page_y, page_h, page_w, viewport_scale=None):
    """Detect header, footer, and background RECTANGLE candidates by position.

    Args:
        sorted_children: Children sorted by Y.
        page_y: Page top Y coordinate.
        page_h: Page height.
        page_w: Page width.
        viewport_scale: Optional dict from compute_viewport_scale().

    Returns (header_candidates, footer_candidates, background_candidates) lists of node IDs.
    """
    w_scale = viewport_scale.get('w_scale', 1.0) if viewport_scale else 1.0
    bg_min_h = scaled_threshold(HINT_BG_MIN_HEIGHT, w_scale, min_value=50)

    header_candidates = []
    footer_candidates = []
    background_candidates = []

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
        if node_type == 'RECTANGLE' and bb['h'] >= bg_min_h:
            background_candidates.append(node_id)

    return header_candidates, footer_candidates, background_candidates


def _detect_header_cluster(sorted_children, page_y):
    """Detect header cluster IDs for flat structures (Issue 179).

    Looks for nav-like TEXT elements within the header zone.
    Returns list of node IDs forming the header cluster, or empty list.
    """
    header_zone_top = page_y
    header_zone_bottom = page_y + HEADER_ZONE_HEIGHT
    header_zone_elements = []
    header_zone_texts = 0

    for child in sorted_children:
        bb_c = get_bbox(child)
        if bb_c['y'] >= header_zone_top and bb_c['y'] + bb_c['h'] <= header_zone_bottom + HEADER_ZONE_MARGIN:
            header_zone_elements.append(child.get('id', ''))
            if child.get('type') == 'TEXT':
                text_content = child.get('characters', child.get('name', ''))
                if len(text_content) < NAV_MAX_TEXT_LEN:
                    header_zone_texts += 1

    if header_zone_texts >= HEADER_NAV_MIN_TEXTS and len(header_zone_elements) >= HEADER_NAV_MIN_TEXTS + 1:
        return header_zone_elements
    return []


def _detect_consecutive_patterns(sorted_children):
    """Detect consecutive runs of structurally similar children.

    Uses Jaccard similarity on structure hashes.
    Returns list of pattern dicts with indices/ids/names/hash.
    """
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
    return consecutive_patterns


def _detect_heading_and_loose(sorted_children, viewport_scale=None):
    """Detect heading candidates and loose elements (dividers, small leaf nodes).

    Args:
        sorted_children: Children sorted by Y.
        viewport_scale: Optional dict from compute_viewport_scale().

    Returns (heading_candidates, loose_elements) tuple.
    """
    w_scale = viewport_scale.get('w_scale', 1.0) if viewport_scale else 1.0
    heading_max_h = scaled_threshold(HINT_HEADING_MAX_HEIGHT, w_scale, min_value=80)

    heading_candidates = []
    for idx, child in enumerate(sorted_children):
        bb = get_bbox(child)
        child_h = bb.get('h', 999)
        if child_h > heading_max_h:
            continue
        if is_heading_like(child):
            heading_candidates.append({
                'index': idx,
                'id': child.get('id', ''),
                'name': child.get('name', ''),
                'height': child_h,
            })

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

    return heading_candidates, loose_elements


def detect_heuristic_hints(children, page_bbox, viewport_scale=None):
    """Detect header/footer candidates, gap analysis, and background candidates.

    Semantic understanding (page-kv, section boundaries) is delegated to Stage B Claude reasoning.
    This function provides mechanical hints to support Claude's decision-making.

    Args:
        children: List of child nodes.
        page_bbox: Page bounding box dict with x, y, w, h.
        viewport_scale: Optional dict from compute_viewport_scale() for
            viewport-relative threshold scaling.
    """
    page_h = page_bbox['h']
    page_y = page_bbox['y']
    page_w = page_bbox['w']
    empty_result = {
        'header_candidates': [], 'header_cluster_ids': [],
        'footer_candidates': [], 'gap_analysis': [],
        'background_candidates': [], 'consecutive_patterns': [],
        'heading_candidates': [], 'loose_elements': [],
    }
    if page_h <= 0:
        return empty_result

    # Sort by Y for analysis
    sorted_children = sorted(
        [c for c in children if c.get('visible') != False],
        key=lambda c: get_bbox(c).get('y', 0)
    )

    header_cands, footer_cands, bg_cands = _detect_header_footer_bg(sorted_children, page_y, page_h, page_w, viewport_scale=viewport_scale)

    # Gap analysis: Y-direction gaps between consecutive children
    gap_analysis = []
    for i in range(len(sorted_children) - 1):
        curr = sorted_children[i]
        next_child = sorted_children[i + 1]
        curr_bb = get_bbox(curr)
        next_bb = get_bbox(next_child)
        gap_px = round(next_bb['y'] - (curr_bb['y'] + curr_bb['h']))
        gap_analysis.append({
            'between': [curr.get('id', ''), next_child.get('id', '')],
            'gap_px': gap_px,
        })

    header_cluster_ids = _detect_header_cluster(sorted_children, page_y)
    consecutive_patterns = _detect_consecutive_patterns(sorted_children)
    heading_candidates, loose_elements = _detect_heading_and_loose(sorted_children, viewport_scale=viewport_scale)

    return {
        'header_candidates': header_cands,
        'header_cluster_ids': header_cluster_ids,
        'footer_candidates': footer_cands,
        'gap_analysis': gap_analysis,
        'background_candidates': bg_cands,
        'consecutive_patterns': consecutive_patterns,
        'heading_candidates': heading_candidates,
        'loose_elements': loose_elements,
    }


def classify_section_type(hints, section_name=''):
    """Classify a section based on its heuristic hints and name.

    Args:
        hints: Dict of heuristic hints (from detect_heuristic_hints or subset).
        section_name: Optional section name string for keyword matching.

    Returns one of: 'header', 'footer', 'hero', 'content', 'unknown'.
    """
    if not hints:
        hints = {}
    name_lower = section_name.lower() if section_name else ''

    if hints.get('is_header') or hints.get('header_candidates') or 'header' in name_lower:
        return 'header'
    if hints.get('is_footer') or hints.get('footer_candidates') or 'footer' in name_lower:
        return 'footer'
    if hints.get('has_hero_bg') or 'hero' in name_lower:
        return 'hero'
    if hints.get('has_bg_candidate') or hints.get('background_candidates') or hints.get('has_heading') or hints.get('heading_candidates'):
        return 'content'
    return 'unknown'


def _compute_gap_analysis(children):
    """Compute gap statistics for a group of sibling nodes.

    Analyses vertical gaps between consecutive children (sorted by Y).

    Args:
        children: List of Figma node dicts.

    Returns:
        Dict with 'median', 'mean', 'consistency' keys, or None if
        insufficient data (fewer than 3 children or fewer than 2 positive gaps).
    """
    if len(children) < 3:
        return None

    visible = [c for c in children if c.get('visible') != False]
    if len(visible) < 3:
        return None

    bboxes = [get_bbox(c) for c in visible]
    sorted_bbs = sorted(bboxes, key=lambda b: b['y'])

    gaps = []
    for i in range(len(sorted_bbs) - 1):
        gap = sorted_bbs[i + 1]['y'] - (sorted_bbs[i]['y'] + sorted_bbs[i]['h'])
        if gap > 0:
            gaps.append(gap)

    if len(gaps) < 2:
        return None

    median_gap = int(statistics.median(gaps))
    mean_gap = int(statistics.mean(gaps))
    # Zero-division guard (Issue 238 pattern)
    cv = statistics.stdev(gaps) / mean_gap if mean_gap > 0 else 1.0

    if cv < 0.15:
        consistency = 'high'
    elif cv < 0.35:
        consistency = 'medium'
    else:
        consistency = 'low'

    return {
        'median': median_gap,
        'mean': mean_gap,
        'consistency': consistency,
    }


def run_sectioning_context(metadata_path, output_file='', enriched_flag=''):
    """Main entry point for sectioning context preparation.

    Args:
        metadata_path: Path to Figma metadata JSON file.
        output_file: Optional path to write JSON output.
        enriched_flag: Non-empty string to include enriched children table.

    Returns:
        JSON string to print to stdout.
    """
    import sys
    sys.setrecursionlimit(3000)  # Guard against deeply nested Figma files (Issue 48)

    data = load_metadata(metadata_path)
    root = get_root_node(data)
    resolve_absolute_coords(root)

    page_bbox = get_bbox(root)
    children = root.get('children', [])

    # Sort by Y ascending
    sorted_children = sort_by_y(children)

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
    if enriched_flag:
        enriched = generate_enriched_table(
            sorted_children,
            page_width=page_bbox['w'],
            page_height=page_bbox['h'],
            root_x=page_bbox.get('x', 0),
            root_y=page_bbox.get('y', 0),
        )
        result['enriched_children_table'] = enriched

    if output_file:
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        return json.dumps({
            'status': 'ok',
            'output': output_file,
            'total_children': len(sorted_children),
            'enriched_table': bool(enriched_flag),
        }, indent=2)
    else:
        return json.dumps(result, indent=2, ensure_ascii=False)

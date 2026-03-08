"""Background-content layer detection for figma-prepare.

Detects full-width background RECTANGLEs with overlay decorations vs content elements.

Issue 180: Background RECTANGLE + decoration vs content layer separation.
Issue 183: Also detect oversized elements (overflow design elements).
Issue 204: Left-overflow background detection.
"""

from .constants import (
    BG_DECORATION_MAX_AREA_RATIO,
    BG_LEFT_OVERFLOW_WIDTH_RATIO,
    BG_MIN_HEIGHT_RATIO,
    BG_WIDTH_RATIO,
    OVERFLOW_BG_MIN_WIDTH,
)
from .geometry import get_bbox


def _find_bg_rectangle(children, parent_bb):
    """Find a single background RECTANGLE among siblings.

    A background candidate is a leaf RECTANGLE that is:
    - Width >= 80% of parent width, OR
    - Width >= OVERFLOW_BG_MIN_WIDTH (1400px), OR
    - x < 0 (left overflow) and width >= parent width * BG_LEFT_OVERFLOW_WIDTH_RATIO
    And height >= 30% of parent height (not a thin divider).

    Args:
        children: List of sibling nodes (already filtered for visibility).
        parent_bb: Parent bounding box dict with x, y, w, h.

    Returns:
        tuple or None: (bg_idx, bg_node, bg_bb) if exactly 1 candidate found, else None.

    Issue 183: Also detect oversized elements (width >= OVERFLOW_BG_MIN_WIDTH or x < 0).
    """
    bg_candidates = []
    for i, child in enumerate(children):
        if child.get('type') != 'RECTANGLE':
            continue
        # Must be a leaf node (no children)
        if child.get('children'):
            continue
        bb = get_bbox(child)
        if bb['w'] <= 0 or bb['h'] <= 0:
            continue
        # Width check: original (>=80% parent) OR overflow (>=OVERFLOW_BG_MIN_WIDTH or x<0)
        is_wide_enough = bb['w'] >= parent_bb['w'] * BG_WIDTH_RATIO
        is_overflow = bb['w'] >= OVERFLOW_BG_MIN_WIDTH
        is_left_overflow = bb['x'] < 0 and bb['w'] >= parent_bb['w'] * BG_LEFT_OVERFLOW_WIDTH_RATIO
        if not (is_wide_enough or is_overflow or is_left_overflow):
            continue
        # Height >= 30% of parent height (not a thin divider)
        if bb['h'] < parent_bb['h'] * BG_MIN_HEIGHT_RATIO:
            continue
        bg_candidates.append((i, child, bb))

    # Must be exactly 1 bg candidate (ambiguous if multiple)
    if len(bg_candidates) != 1:
        return None

    return bg_candidates[0]


def _classify_decorations(children, bg_idx, bg_bb):
    """Separate decoration elements from content elements relative to a background RECTANGLE.

    Decoration elements are small VECTOR/ELLIPSE leaf nodes that overlap the
    background RECTANGLE (area < 5% of bg area). Everything else is content.

    Args:
        children: List of sibling nodes (already filtered for visibility).
        bg_idx: Index of the background RECTANGLE in children.
        bg_bb: Bounding box of the background RECTANGLE.

    Returns:
        tuple: (decoration_indices: set, content_indices: list)
    """
    bg_area = bg_bb['w'] * bg_bb['h']

    decoration_indices = set()
    decoration_indices.add(bg_idx)

    for i, child in enumerate(children):
        if i == bg_idx:
            continue
        child_type = child.get('type', '')
        if child_type not in ('VECTOR', 'ELLIPSE'):
            continue
        # Must be a leaf node
        if child.get('children'):
            continue
        cb = get_bbox(child)
        if cb['w'] <= 0 or cb['h'] <= 0:
            continue
        child_area = cb['w'] * cb['h']
        # "small" = area < 5% of bg RECTANGLE area
        if bg_area > 0 and child_area / bg_area >= BG_DECORATION_MAX_AREA_RATIO:
            continue
        # Must overlap the bg RECTANGLE's bounding box
        overlap_x = max(0, min(bg_bb['x'] + bg_bb['w'], cb['x'] + cb['w']) - max(bg_bb['x'], cb['x']))
        overlap_y = max(0, min(bg_bb['y'] + bg_bb['h'], cb['y'] + cb['h']) - max(bg_bb['y'], cb['y']))
        if overlap_x > 0 and overlap_y > 0:
            decoration_indices.add(i)

    content_indices = [i for i in range(len(children)) if i not in decoration_indices]
    return decoration_indices, content_indices


def detect_bg_content_layers(children, parent_bb):
    """Detect background RECTANGLE + decoration vs content elements.

    Pattern: A full-width RECTANGLE (>=80% parent width) acts as a background layer.
    Also detects oversized elements (width >= OVERFLOW_BG_MIN_WIDTH or x < 0) as
    background candidates (Issue 183: overflow design elements).
    Small sibling elements (VECTOR, ELLIPSE) that overlap the RECTANGLE's position
    are treated as decoration (same visual layer). Everything else is content.

    Only triggers when:
    1. There is exactly 1 bg-candidate RECTANGLE among siblings (leaf node, no children)
       - Width >= 80% of parent width, OR
       - Width >= OVERFLOW_BG_MIN_WIDTH (1400px), OR
       - x < 0 (left overflow) and width >= parent width * BG_LEFT_OVERFLOW_WIDTH_RATIO
    2. The RECTANGLE covers >=30% of parent height (not just a thin divider)
    3. There are >=2 non-decoration siblings (content elements)

    Args:
        children: List of sibling nodes.
        parent_bb: Parent bounding box dict with x, y, w, h.

    Returns:
        list: Grouping candidates. Each has:
            - method: 'semantic'
            - semantic_type: 'bg-content'
            - node_ids: IDs of content-layer elements
            - bg_node_ids: IDs of bg-layer elements (RECTANGLE + decorations)
            - suggested_name: 'content-layer'
            - suggested_wrapper: 'content-group'
    """
    if not children or not parent_bb or parent_bb['w'] <= 0 or parent_bb['h'] <= 0:
        return []

    children = [c for c in children if c.get('visible') != False]

    # Step 1: Find background RECTANGLE (exactly 1)
    bg_result = _find_bg_rectangle(children, parent_bb)
    if bg_result is None:
        return []

    bg_idx, bg_node, bg_bb = bg_result

    # Step 2: Classify decorations vs content
    decoration_indices, content_indices = _classify_decorations(children, bg_idx, bg_bb)

    # Must have >= 2 content elements
    if len(content_indices) < 2:
        return []

    content_ids = [children[i].get('id', '') for i in content_indices]
    content_names = [children[i].get('name', '') for i in content_indices]
    bg_ids = [children[i].get('id', '') for i in sorted(decoration_indices)]
    bg_names = [children[i].get('name', '') for i in sorted(decoration_indices)]

    return [{
        'method': 'semantic',
        'semantic_type': 'bg-content',
        'node_ids': content_ids,
        'node_names': content_names,
        'bg_node_ids': bg_ids,
        'bg_node_names': bg_names,
        'count': len(content_ids),
        'suggested_name': 'content-layer',
        'suggested_wrapper': 'content-group',
    }]

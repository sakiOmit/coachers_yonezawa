"""Highlight text detection for figma-prepare.

Detects RECTANGLE + TEXT highlight pairs where a rectangle acts as
a background emphasis for short text content.

Issue 190: Text highlighting pattern detection.
"""

from .constants import (
    HIGHLIGHT_HEIGHT_RATIO_MAX,
    HIGHLIGHT_HEIGHT_RATIO_MIN,
    HIGHLIGHT_OVERLAP_RATIO,
    HIGHLIGHT_TEXT_MAX_LEN,
    HIGHLIGHT_X_OVERLAP_RATIO,
)
from .geometry import get_bbox


def _check_rect_text_overlap(r_bb, t_bb, text_content):
    """Check if a RECTANGLE and TEXT node form a valid highlight pair.

    Validates height ratio, Y overlap, X overlap, and text length constraints.

    Args:
        r_bb: Bounding box of the RECTANGLE node.
        t_bb: Bounding box of the TEXT node.
        text_content: Text content string.

    Returns:
        bool: True if the pair qualifies as a highlight.
    """
    # Check text length
    if len(text_content) > HIGHLIGHT_TEXT_MAX_LEN:
        return False

    # Check height ratio
    if t_bb['h'] <= 0:
        return False
    height_ratio = r_bb['h'] / t_bb['h']
    if height_ratio < HIGHLIGHT_HEIGHT_RATIO_MIN or height_ratio > HIGHLIGHT_HEIGHT_RATIO_MAX:
        return False

    # Check Y overlap
    y_overlap_top = max(r_bb['y'], t_bb['y'])
    y_overlap_bot = min(r_bb['y'] + r_bb['h'], t_bb['y'] + t_bb['h'])
    y_overlap = max(0, y_overlap_bot - y_overlap_top)
    smaller_h = min(r_bb['h'], t_bb['h'])
    if smaller_h <= 0:
        return False
    y_overlap_ratio = y_overlap / smaller_h
    if y_overlap_ratio < HIGHLIGHT_OVERLAP_RATIO:
        return False

    # Check X overlap
    x_overlap_left = max(r_bb['x'], t_bb['x'])
    x_overlap_right = min(r_bb['x'] + r_bb['w'], t_bb['x'] + t_bb['w'])
    x_overlap = max(0, x_overlap_right - x_overlap_left)
    smaller_w = min(r_bb['w'], t_bb['w'])
    if smaller_w <= 0:
        return False
    x_overlap_ratio = x_overlap / smaller_w
    if x_overlap_ratio < HIGHLIGHT_X_OVERLAP_RATIO:
        return False

    return True


def _find_rect_text_overlaps(children, rect_indices, text_indices):
    """Find RECTANGLE + TEXT pairs that form highlight overlaps.

    For each RECTANGLE, finds the first matching TEXT with valid overlap criteria.
    Each RECTANGLE and TEXT can only be used once.

    Args:
        children: List of sibling nodes (already filtered for visibility).
        rect_indices: List of indices pointing to leaf RECTANGLE nodes.
        text_indices: List of indices pointing to TEXT nodes.

    Returns:
        list: [{'rect_idx': i, 'text_idx': j, 'text_content': '...'}]
    """
    results = []
    used_rects = set()
    used_texts = set()

    for ri in rect_indices:
        rect = children[ri]
        r_bb = get_bbox(rect)
        if r_bb['w'] <= 0 or r_bb['h'] <= 0:
            continue
        if ri in used_rects:
            continue

        for ti in text_indices:
            if ti in used_texts:
                continue
            text_node = children[ti]
            t_bb = get_bbox(text_node)
            if t_bb['w'] <= 0 or t_bb['h'] <= 0:
                continue

            text_content = text_node.get('characters', '') or text_node.get('name', '')

            if _check_rect_text_overlap(r_bb, t_bb, text_content):
                results.append({
                    'rect_idx': ri,
                    'text_idx': ti,
                    'text_content': text_content,
                })
                used_rects.add(ri)
                used_texts.add(ti)
                break  # Move to next RECTANGLE

    return results


def detect_highlight_text(children):
    """Detect RECTANGLE + TEXT highlight pairs among siblings.

    Pattern: A RECTANGLE positioned behind a TEXT element at the same location
    acts as a text highlight/emphasis background. Common in Japanese web design
    for marking key phrases.

    Detection criteria for each RECTANGLE + TEXT pair:
    1. Y ranges overlap >= 80% (based on smaller element's height)
    2. X ranges also overlap significantly (>= 50% of smaller width)
    3. RECTANGLE height is 0.5-2.0x TEXT height
    4. TEXT content is short (<= 30 chars)
    5. RECTANGLE is a leaf node (no children)

    Args:
        children: List of sibling nodes.

    Returns:
        list: [{'rect_idx': i, 'text_idx': j, 'text_content': '...'}]

    Issue 190: Text highlighting pattern detection.
    """
    children = [c for c in children if c.get('visible') != False]
    if not children:
        return []

    # Collect RECTANGLE and TEXT indices
    rect_indices = []
    text_indices = []
    for i, child in enumerate(children):
        child_type = child.get('type', '')
        if child_type == 'RECTANGLE' and not child.get('children'):
            rect_indices.append(i)
        elif child_type == 'TEXT':
            text_indices.append(i)

    if not rect_indices or not text_indices:
        return []

    return _find_rect_text_overlaps(children, rect_indices, text_indices)

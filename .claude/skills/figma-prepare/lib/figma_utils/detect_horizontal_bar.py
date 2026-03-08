"""Horizontal bar detection for figma-prepare.

Detects news tickers, notification bars, announcement strips -- narrow Y-bands
containing horizontally distributed elements with a background RECTANGLE.

Issue 184: Horizontal bar (news ticker) grouping.
"""

import statistics

from .constants import (
    HORIZONTAL_BAR_MAX_HEIGHT,
    HORIZONTAL_BAR_MIN_ELEMENTS,
    HORIZONTAL_BAR_VARIANCE_RATIO,
)
from .geometry import get_bbox
from .metadata import get_text_children_content


def _cluster_by_y_band(bboxes, max_height):
    """Find the next Y-band cluster starting from elements sorted by Y-center.

    Sorts elements by Y-center and greedily expands a band from each unused
    starting element, collecting all elements that fit within max_height.

    Args:
        bboxes: List of bounding box dicts (parallel to children).
        max_height: Maximum Y-band height (HORIZONTAL_BAR_MAX_HEIGHT).

    Returns:
        list of int: Indices sorted by Y-center for iteration.
    """
    return sorted(range(len(bboxes)), key=lambda i: bboxes[i]['y'] + bboxes[i]['h'] / 2)


def _expand_y_band(start_pos, indexed, bboxes, max_height, used):
    """Expand a Y-band from a starting position, collecting fitting elements.

    Args:
        start_pos: Position in the indexed list to start from.
        indexed: Y-center-sorted list of element indices.
        bboxes: List of bounding box dicts.
        max_height: Maximum Y-band height.
        used: Set of already-used indices to skip.

    Returns:
        list of int: Element indices forming the band.
    """
    band_indices = [indexed[start_pos]]
    band_y_min = bboxes[indexed[start_pos]]['y']
    band_y_max = bboxes[indexed[start_pos]]['y'] + bboxes[indexed[start_pos]]['h']

    for j in range(start_pos + 1, len(indexed)):
        if indexed[j] in used:
            continue
        idx = indexed[j]
        el_y = bboxes[idx]['y']
        el_bottom = el_y + bboxes[idx]['h']
        new_y_min = min(band_y_min, el_y)
        new_y_max = max(band_y_max, el_bottom)
        if new_y_max - new_y_min <= max_height:
            band_indices.append(idx)
            band_y_min = new_y_min
            band_y_max = new_y_max

    return band_indices


def _infer_bar_name(band_nodes):
    """Infer a semantic name for a horizontal bar from its text content.

    Args:
        band_nodes: List of Figma nodes in the bar.

    Returns:
        str: 'news-bar', 'blog-bar', or 'horizontal-bar' (default).
    """
    texts = get_text_children_content(band_nodes, max_items=5)
    for t in texts:
        t_lower = t.lower()
        if '\u30cb\u30e5\u30fc\u30b9' in t_lower or 'news' in t_lower or '\u304a\u77e5\u3089\u305b' in t_lower:
            return 'news-bar'
        if '\u30d6\u30ed\u30b0' in t_lower or 'blog' in t_lower:
            return 'blog-bar'
    return 'horizontal-bar'


def _is_valid_horizontal_bar(band_indices, children, bboxes):
    """Validate that a Y-band cluster qualifies as a horizontal bar.

    Checks:
    1. At least 1 background RECTANGLE (leaf node) exists in the band.
    2. Elements are horizontally distributed (X variance > Y variance * ratio).

    Args:
        band_indices: List of element indices in the band.
        children: List of all sibling nodes.
        bboxes: List of bounding box dicts (parallel to children).

    Returns:
        bool: True if the band qualifies as a horizontal bar.
    """
    # Check for at least 1 background RECTANGLE (leaf node)
    has_rect_bg = any(
        children[idx].get('type') == 'RECTANGLE' and not children[idx].get('children')
        for idx in band_indices
    )
    if not has_rect_bg:
        return False

    # Check horizontal distribution: X variance > Y variance * HORIZONTAL_BAR_VARIANCE_RATIO
    band_bboxes = [bboxes[i] for i in band_indices]
    x_centers = [b['x'] + b['w'] / 2 for b in band_bboxes]
    y_centers = [b['y'] + b['h'] / 2 for b in band_bboxes]
    if len(x_centers) < 2:
        return False
    x_var = statistics.variance(x_centers)
    y_var = statistics.variance(y_centers)
    return x_var > y_var * HORIZONTAL_BAR_VARIANCE_RATIO


def detect_horizontal_bar(children, parent_bb):
    """Detect a horizontal bar pattern among siblings.

    Pattern: A narrow Y-band (< 100px height) containing 4+ elements that are
    horizontally distributed, with at least 1 background RECTANGLE. Common in
    news tickers, notification bars, announcement strips.

    Detection criteria:
    1. 4+ siblings fall within a narrow Y-range (< HORIZONTAL_BAR_MAX_HEIGHT)
    2. At least 1 RECTANGLE (leaf node) in the band acts as background
    3. Elements are horizontally distributed (X variance > Y variance * 3)

    Args:
        children: List of sibling nodes (with absoluteBoundingBox resolved).
        parent_bb: Parent bounding box dict with x, y, w, h.

    Returns:
        list: Grouping candidates with method='semantic', semantic_type='horizontal-bar'.

    Issue 184: Horizontal bar (news ticker) grouping.
    """
    children = [c for c in children if c.get('visible') != False]
    if len(children) < HORIZONTAL_BAR_MIN_ELEMENTS:
        return []

    bboxes = [get_bbox(c) for c in children]
    results = []
    used = set()

    # Sort indices by Y-center for band clustering
    indexed = _cluster_by_y_band(bboxes, HORIZONTAL_BAR_MAX_HEIGHT)

    for start in range(len(indexed)):
        if indexed[start] in used:
            continue

        band_indices = _expand_y_band(start, indexed, bboxes, HORIZONTAL_BAR_MAX_HEIGHT, used)

        if len(band_indices) < HORIZONTAL_BAR_MIN_ELEMENTS:
            continue

        if not _is_valid_horizontal_bar(band_indices, children, bboxes):
            continue

        band_nodes = [children[i] for i in band_indices]
        suggested_name = _infer_bar_name(band_nodes)

        for idx in band_indices:
            used.add(idx)

        results.append({
            'method': 'semantic',
            'semantic_type': 'horizontal-bar',
            'node_ids': [children[i].get('id', '') for i in band_indices],
            'node_names': [children[i].get('name', '') for i in band_indices],
            'count': len(band_indices),
            'suggested_name': suggested_name,
            'suggested_wrapper': 'bar',
        })

    return results

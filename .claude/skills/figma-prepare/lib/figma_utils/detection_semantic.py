"""Semantic structure detection functions for figma-prepare.

Detectors for horizontal bars, background-content layers, table rows,
and decoration patterns.
"""

import statistics

from .constants import (
    BG_DECORATION_MAX_AREA_RATIO,
    BG_LEFT_OVERFLOW_WIDTH_RATIO,
    BG_MIN_HEIGHT_RATIO,
    BG_WIDTH_RATIO,
    DECORATION_MAX_SIZE,
    DECORATION_MIN_SHAPES,
    DECORATION_SHAPE_RATIO,
    HORIZONTAL_BAR_MAX_HEIGHT,
    HORIZONTAL_BAR_MIN_ELEMENTS,
    HORIZONTAL_BAR_VARIANCE_RATIO,
    OVERFLOW_BG_MIN_WIDTH,
    TABLE_DIVIDER_MAX_HEIGHT,
    TABLE_MIN_ROWS,
    TABLE_ROW_WIDTH_RATIO,
)
from .geometry import get_bbox
from .metadata import get_text_children_content
from .naming import to_kebab


def is_decoration_pattern(node):
    """Check if a node is a decorative dot/shape pattern frame.

    Decorative patterns are small frames filled with multiple ELLIPSE, RECTANGLE,
    or VECTOR leaf nodes (e.g., dot grids, scattered circles). These get generic
    names like 'group-N' without this detection.

    Criteria:
    1. Node must be FRAME or GROUP with children
    2. Total size < DECORATION_MAX_SIZE x DECORATION_MAX_SIZE
    3. >= 60% of leaf descendants are ELLIPSE, RECTANGLE, or VECTOR
    4. At least DECORATION_MIN_SHAPES (3) shape leaf descendants

    Args:
        node: Figma node dict.

    Returns:
        bool: True if node is a decoration pattern.

    Issue 189: Small decorative frames containing dot patterns.
    """
    node_type = node.get('type', '')
    if node_type not in ('FRAME', 'GROUP'):
        return False

    children = [c for c in node.get('children', []) if c.get('visible') != False]
    if not children:
        return False

    # Size check
    bbox = node.get('absoluteBoundingBox') or {}
    w = bbox.get('width', 0)
    h = bbox.get('height', 0)
    if w > DECORATION_MAX_SIZE or h > DECORATION_MAX_SIZE:
        return False

    # Count leaf descendants by type
    shape_types = {'ELLIPSE', 'RECTANGLE', 'VECTOR'}

    def count_leaves(n):
        ch = [c for c in n.get('children', []) if c.get('visible') != False]
        if not ch:
            return (1 if n.get('type', '') in shape_types else 0, 1)
        shape_total = 0
        leaf_total = 0
        for c in ch:
            s, t = count_leaves(c)
            shape_total += s
            leaf_total += t
        return (shape_total, leaf_total)

    shape_count, total_leaves = count_leaves(node)

    if total_leaves == 0:
        return False
    if shape_count < DECORATION_MIN_SHAPES:
        return False
    if shape_count / total_leaves < DECORATION_SHAPE_RATIO:
        return False

    return True


def decoration_dominant_shape(node):
    """Determine the dominant shape type in a decoration pattern.

    Args:
        node: Figma node dict (assumed to be a decoration pattern).

    Returns:
        str: 'ELLIPSE', 'RECTANGLE', or 'VECTOR' -- whichever has the most leaf nodes.

    Issue 189: Used to distinguish 'decoration-dots' (ELLIPSE-dominant)
    from 'decoration-pattern' (RECTANGLE/VECTOR-dominant).
    """
    shape_types = {'ELLIPSE', 'RECTANGLE', 'VECTOR'}
    counts = {'ELLIPSE': 0, 'RECTANGLE': 0, 'VECTOR': 0}

    def count_shapes(n):
        ch = [c for c in n.get('children', []) if c.get('visible') != False]
        if not ch:
            t = n.get('type', '')
            if t in shape_types:
                counts[t] += 1
            return
        for c in ch:
            count_shapes(c)

    count_shapes(node)
    return max(counts, key=counts.get)


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


def _find_table_row_backgrounds(children, min_width):
    """Find full-width RECTANGLE leaf nodes that serve as table row backgrounds.

    Args:
        children: List of sibling nodes (already filtered for visibility).
        min_width: Minimum width threshold (parent_w * TABLE_ROW_WIDTH_RATIO).

    Returns:
        list: RECTANGLE nodes whose width >= min_width and have no children.
    """
    full_width_rects = []
    for c in children:
        if (c.get('type') == 'RECTANGLE'
                and not c.get('children')
                and get_bbox(c)['w'] >= min_width):
            full_width_rects.append(c)
    return full_width_rects


def _find_table_dividers(children, min_width):
    """Find full-width VECTOR/LINE elements that act as table dividers.

    Args:
        children: List of sibling nodes (already filtered for visibility).
        min_width: Minimum width threshold (parent_w * TABLE_ROW_WIDTH_RATIO).

    Returns:
        list: VECTOR/LINE nodes with width >= min_width and height <= TABLE_DIVIDER_MAX_HEIGHT.
    """
    dividers = []
    for c in children:
        if c.get('type') in ('VECTOR', 'LINE'):
            bb = get_bbox(c)
            if bb['w'] >= min_width and bb['h'] <= TABLE_DIVIDER_MAX_HEIGHT:
                dividers.append(c)
    return dividers


def _assign_members_to_rows(full_width_rects, children, rect_ids, divider_ids):
    """Assign non-rect, non-divider children to table rows by Y-center overlap.

    For each RECTANGLE, finds sibling nodes whose Y-center falls within
    [rect.y, rect.y + rect.h].

    Args:
        full_width_rects: List of background RECTANGLE nodes.
        children: All sibling nodes (already filtered for visibility).
        rect_ids: Set of RECTANGLE node IDs.
        divider_ids: Set of divider node IDs.

    Returns:
        tuple: (all_row_member_ids: set, row_count: int)
    """
    all_row_member_ids = set()
    row_count = 0
    for rect in full_width_rects:
        rect_bb = get_bbox(rect)
        rect_y_top = rect_bb['y']
        rect_y_bot = rect_bb['y'] + rect_bb['h']
        row_members = [rect]

        for c in children:
            c_id = c.get('id', '')
            if c_id in rect_ids or c_id in divider_ids:
                continue
            c_bb = get_bbox(c)
            c_cy = c_bb['y'] + c_bb['h'] / 2
            if rect_y_top <= c_cy <= rect_y_bot:
                row_members.append(c)

        # Only count as a row if there's at least one text/content element
        if len(row_members) > 1:
            row_count += 1
        for m in row_members:
            all_row_member_ids.add(m.get('id', ''))

    return all_row_member_ids, row_count


def _include_table_headings(children, all_row_member_ids, first_rect_y):
    """Include heading elements that appear above the first table row background.

    Scans children for FRAME/GROUP/TEXT/INSTANCE/COMPONENT nodes positioned
    entirely above first_rect_y and adds them to the member set.

    Args:
        children: List of sibling nodes (already filtered for visibility).
        all_row_member_ids: Set of node IDs already in the table (mutated in-place).
        first_rect_y: Y position of the topmost row background RECTANGLE.
    """
    for c in children:
        c_id = c.get('id', '')
        if c_id in all_row_member_ids:
            continue
        c_bb = get_bbox(c)
        # Heading must be above first row background
        if c_bb['y'] + c_bb['h'] <= first_rect_y:
            c_type = c.get('type', '')
            # Accept FRAME/GROUP/TEXT as potential headings
            if c_type in ('FRAME', 'GROUP', 'TEXT', 'INSTANCE', 'COMPONENT'):
                all_row_member_ids.add(c_id)


def _infer_table_name(children, first_rect_y):
    """Infer a table name slug from heading text above the first row.

    Args:
        children: List of sibling nodes (already filtered for visibility).
        first_rect_y: Y position of the topmost row background RECTANGLE.

    Returns:
        str: Kebab-case slug for the table name, or 'data' as fallback.
    """
    for c in children:
        c_bb = get_bbox(c)
        if c_bb['y'] + c_bb['h'] <= first_rect_y:
            texts = get_text_children_content([c], max_items=1)
            if not texts:
                texts = get_text_children_content(c.get('children', []), max_items=1)
            if texts:
                return to_kebab(texts[0])
    return 'data'


def detect_table_rows(children, parent_bb):
    """Detect table-like structure: alternating full-width background RECTANGLEs
    + divider VECTORs + text elements grouped by Y position into rows.

    Pattern detection:
    1. Find 3+ full-width RECTANGLE siblings (>=90% parent width, leaf, unnamed)
    2. Find full-width VECTOR/LINE dividers (>=90% parent width, height <= 2px)
    3. For each RECTANGLE, find TEXT siblings whose Y-center falls within
       [RECT.y, RECT.y + RECT.h]
    4. Group: heading element (if exists, before first RECTANGLE) + row groups
       + trailing dividers

    Args:
        children: List of sibling nodes.
        parent_bb: Bounding box of the parent node (dict with x, y, w, h).

    Returns:
        list: One grouping candidate per table, containing:
            - method: 'semantic'
            - semantic_type: 'table'
            - node_ids: All table-member node IDs (bg RECTs + dividers + texts + heading)
            - suggested_name: 'table-{slug}'
            - suggested_wrapper: 'table-container'
            - row_count: number of data rows

    Issue 181: Flat sibling elements forming table rows are not grouped.
    """
    children = [c for c in children if c.get('visible') != False]
    if not children or parent_bb.get('w', 0) <= 0:
        return []

    min_width = parent_bb['w'] * TABLE_ROW_WIDTH_RATIO

    # Step 1: Find full-width RECTANGLE leaves (row backgrounds)
    full_width_rects = _find_table_row_backgrounds(children, min_width)
    if len(full_width_rects) < TABLE_MIN_ROWS:
        return []

    # Step 2: Find full-width dividers (VECTOR/LINE, height <= 2px)
    dividers = _find_table_dividers(children, min_width)

    rect_ids = {c.get('id', '') for c in full_width_rects}
    divider_ids = {c.get('id', '') for c in dividers}

    # Step 3: Assign members to rows by Y-center overlap
    all_row_member_ids, row_count = _assign_members_to_rows(
        full_width_rects, children, rect_ids, divider_ids
    )
    if row_count < TABLE_MIN_ROWS:
        return []

    # Step 4: Include dividers in the table
    for d in dividers:
        all_row_member_ids.add(d.get('id', ''))

    # Step 5: Include heading elements above first row
    rects_sorted = sorted(full_width_rects, key=lambda c: get_bbox(c)['y'])
    first_rect_y = get_bbox(rects_sorted[0])['y']
    _include_table_headings(children, all_row_member_ids, first_rect_y)

    # Step 6: Infer name and build result
    slug = _infer_table_name(children, first_rect_y)
    ordered_members = [c for c in children if c.get('id', '') in all_row_member_ids]

    return [{
        'method': 'semantic',
        'semantic_type': 'table',
        'node_ids': [c.get('id', '') for c in ordered_members],
        'node_names': [c.get('name', '') for c in ordered_members],
        'count': len(ordered_members),
        'suggested_name': f'table-{slug}',
        'suggested_wrapper': 'table-container',
        'row_count': row_count,
    }]

"""Table row structure detection for figma-prepare.

Detects table-like structures: alternating full-width background RECTANGLEs,
divider VECTORs/LINEs, and text elements grouped by Y position into rows.

Issue 181: Flat sibling elements forming table rows are not grouped.
"""

from .constants import (
    TABLE_DIVIDER_MAX_HEIGHT,
    TABLE_MIN_ROWS,
    TABLE_ROW_WIDTH_RATIO,
)
from .geometry import get_bbox
from .metadata import get_text_children_content
from .naming import to_kebab


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

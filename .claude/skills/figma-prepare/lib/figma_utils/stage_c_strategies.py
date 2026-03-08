"""Stage C heuristic sub-grouping strategies.

Extracted from stage_c.py for maintainability.
Provides heuristic_sub_group() and its strategy helpers:
  _try_heading_split(), _try_column_split(), _try_spatial_split(), _try_yband_split().
"""

from .geometry import get_bbox, sort_by_y
from .enrichment import generate_enriched_table
from .stage_c_yaml import parse_enriched_table

__all__ = [
    'heuristic_sub_group',
]

# ---------------------------------------------------------------------------
# Module-level constants (only used in this file)
# ---------------------------------------------------------------------------

_HEADING_MAX_ELEMENTS = 3  # Max heading elements to try splitting (1, 2, or 3)
_HEADING_GAP_MIN = 10  # px — minimum vertical gap between heading and content


# ---------------------------------------------------------------------------
# Heuristic sub-grouping strategies
# ---------------------------------------------------------------------------

def heuristic_sub_group(group, sibling_nodes, root_node, page_width, page_height):
    """Apply heuristic sub-grouping to a group's sibling nodes.

    Returns list of sub_groups, or empty list if no meaningful split.
    """
    node_ids = group.get('node_ids', [])
    if len(node_ids) < 3:
        return []

    # Compute bounding box of all siblings
    bboxes = {}
    for node in sibling_nodes:
        nid = node.get('id', '')
        if not nid:
            continue
        bboxes[nid] = get_bbox(node)

    if not bboxes:
        return []

    min_x = min(b['x'] for b in bboxes.values())
    min_y = min(b['y'] for b in bboxes.values())
    max_right = max(b['x'] + b['w'] for b in bboxes.values())
    max_bottom = max(b['y'] + b['h'] for b in bboxes.values())
    group_width = max_right - min_x
    group_height = max_bottom - min_y

    if group_width <= 0 or group_height <= 0:
        return []

    # Generate enriched table to get Col column
    sibling_sorted = sort_by_y(sibling_nodes)
    enriched = generate_enriched_table(
        sibling_sorted,
        page_width=group_width if group_width > 0 else page_width,
        page_height=group_height if group_height > 0 else page_height,
        root_x=min_x,
        root_y=min_y,
    )

    rows = parse_enriched_table(enriched)
    if not rows:
        return []

    # Strategy 0: Heading separation (top heading elements vs content below)
    heading_groups = _try_heading_split(rows, bboxes, sibling_nodes, group['name'])
    if heading_groups:
        return heading_groups

    # Strategy 1: Column-based split (Col = L/R/F)
    col_groups = _try_column_split(rows, group['name'])
    if col_groups:
        return col_groups

    # Strategy 2: Spatial gap split (large Y gap between element clusters)
    spatial_groups = _try_spatial_split(rows, bboxes, group['name'])
    if spatial_groups:
        return spatial_groups

    # Strategy 3: Y-band clustering (elements at same Y -> horizontal row)
    yband_groups = _try_yband_split(rows, bboxes, group['name'])
    if yband_groups:
        return yband_groups

    return []


def _build_heading_items(rows, bboxes, sibling_nodes):
    """Build sorted items list with (id, y_top, y_bottom, type) for heading detection.

    Returns sorted items list, or empty list if insufficient data.
    """
    node_types = {}
    for node in sibling_nodes:
        nid = node.get('id', '')
        if nid:
            node_types[nid] = node.get('type', '')

    items = []
    for row in rows:
        nid = row.get('ID', '')
        if nid in bboxes:
            b = bboxes[nid]
            items.append((nid, b['y'], b['y'] + b['h'], node_types.get(nid, '')))

    if len(items) < 4:
        return []

    items.sort(key=lambda x: x[1])
    return items


def _find_heading_split_index(items):
    """Find the optimal heading split index (1-3 heading elements).

    Returns the heading size (number of heading elements), or None if no valid split.
    """
    for heading_size in range(1, min(_HEADING_MAX_ELEMENTS + 1, len(items) - 1)):
        heading_candidates = items[:heading_size]
        content_start = items[heading_size]

        heading_types = [c[3] for c in heading_candidates]
        has_text = any(t == 'TEXT' for t in heading_types)
        all_heading_like = all(
            t in ('TEXT', 'ELLIPSE', 'VECTOR', 'LINE') for t in heading_types
        )

        if not has_text or not all_heading_like:
            continue

        heading_max_h = max(c[2] - c[1] for c in heading_candidates)
        if heading_max_h > 60:
            continue

        heading_bottom = max(c[2] for c in heading_candidates)
        content_top = content_start[1]
        if content_top - heading_bottom < _HEADING_GAP_MIN:
            continue

        return heading_size

    return None


def _try_heading_split(rows, bboxes, sibling_nodes, parent_name):
    """Split top heading elements from content below (Issue #258).

    Detects a heading pattern at the top of a group:
    - 1-3 elements at the smallest Y positions
    - Heading elements are TEXT or small ELLIPSE/VECTOR (decorations)
    - Clear separation from content below (any gap or divider between)
    """
    if len(rows) < 4:
        return []

    items = _build_heading_items(rows, bboxes, sibling_nodes)
    if not items:
        return []

    best_split = _find_heading_split_index(items)
    if best_split is None:
        return []

    heading_ids = [items[i][0] for i in range(best_split)]
    content_ids = [items[i][0] for i in range(best_split, len(items))]

    if not heading_ids or len(content_ids) < 2:
        return []

    return [
        {
            'name': f'{parent_name}-heading',
            'pattern': 'single' if len(heading_ids) == 1 else 'list',
            'node_ids': heading_ids,
            'reason': f'heading separation ({len(heading_ids)} elements)',
        },
        {
            'name': f'{parent_name}-content',
            'pattern': 'list',
            'node_ids': content_ids,
            'reason': f'content below heading ({len(content_ids)} elements)',
        },
    ]


def _try_column_split(rows, parent_name):
    """Split by Col column (L/R/F). Returns sub_groups or empty list."""
    left_ids = []
    right_ids = []
    full_ids = []
    other_ids = []

    for row in rows:
        col = row.get('Col', '-')
        nid = row.get('ID', '')
        if not nid:
            continue
        if col == 'L':
            left_ids.append(nid)
        elif col == 'R':
            right_ids.append(nid)
        elif col == 'F':
            full_ids.append(nid)
        else:
            other_ids.append(nid)

    # Need both L and R to split
    if not left_ids or not right_ids:
        return []

    sub_groups = []

    if left_ids:
        sub_groups.append({
            'name': f'{parent_name}-left',
            'pattern': 'single' if len(left_ids) == 1 else 'list',
            'node_ids': left_ids,
            'reason': 'Col=L column split',
        })

    if right_ids:
        sub_groups.append({
            'name': f'{parent_name}-right',
            'pattern': 'single' if len(right_ids) == 1 else 'list',
            'node_ids': right_ids,
            'reason': 'Col=R column split',
        })

    # Full-width elements (dividers, backgrounds) -> separate group or absorb
    if full_ids:
        sub_groups.append({
            'name': f'{parent_name}-dividers',
            'pattern': 'single' if len(full_ids) == 1 else 'decoration',
            'node_ids': full_ids,
            'reason': 'Col=F full-width elements',
        })

    # Other/center elements
    if other_ids:
        sub_groups.append({
            'name': f'{parent_name}-center',
            'pattern': 'single' if len(other_ids) == 1 else 'list',
            'node_ids': other_ids,
            'reason': 'Col=C/- center elements',
        })

    return sub_groups


def _try_spatial_split(rows, bboxes, parent_name):
    """Split by large Y gap between element clusters."""
    SPATIAL_GAP_THRESHOLD = 100  # px

    # Sort by Y position
    items = []
    for row in rows:
        nid = row.get('ID', '')
        if nid in bboxes:
            items.append((nid, bboxes[nid]['y']))

    if len(items) < 3:
        return []

    items.sort(key=lambda x: x[1])

    # Find largest Y gap
    gaps = []
    for i in range(len(items) - 1):
        y1_bottom = bboxes[items[i][0]]['y'] + bboxes[items[i][0]]['h']
        y2_top = items[i + 1][1]
        gap = y2_top - y1_bottom
        gaps.append((i, gap))

    if not gaps:
        return []

    max_gap_idx, max_gap = max(gaps, key=lambda x: x[1])

    if max_gap < SPATIAL_GAP_THRESHOLD:
        return []

    # Split at the largest gap
    top_ids = [items[j][0] for j in range(max_gap_idx + 1)]
    bottom_ids = [items[j][0] for j in range(max_gap_idx + 1, len(items))]

    if not top_ids or not bottom_ids:
        return []

    return [
        {
            'name': f'{parent_name}-upper',
            'pattern': 'single' if len(top_ids) == 1 else 'list',
            'node_ids': top_ids,
            'reason': f'spatial split (gap={int(max_gap)}px)',
        },
        {
            'name': f'{parent_name}-lower',
            'pattern': 'single' if len(bottom_ids) == 1 else 'list',
            'node_ids': bottom_ids,
            'reason': f'spatial split (gap={int(max_gap)}px)',
        },
    ]


def _try_yband_split(rows, bboxes, parent_name):
    """Split by Y-band clustering (elements at same Y position -> horizontal row).

    Detects icon+title pairs, label+value pairs at the same horizontal row.
    """
    YBAND_TOLERANCE = 20  # px -- elements within this Y range form a band

    # Collect items with Y center position
    items = []
    for row in rows:
        nid = row.get('ID', '')
        if nid in bboxes:
            b = bboxes[nid]
            y_center = b['y'] + b['h'] / 2
            items.append((nid, y_center))

    if len(items) < 3:
        return []

    items.sort(key=lambda x: x[1])

    # Group into Y-bands: greedy merge within tolerance
    bands = []
    current_band = [items[0]]
    for i in range(1, len(items)):
        # Compare with the first element in current band (anchor)
        if items[i][1] - current_band[0][1] <= YBAND_TOLERANCE:
            current_band.append(items[i])
        else:
            bands.append(current_band)
            current_band = [items[i]]
    bands.append(current_band)

    # Need 2+ distinct bands AND at least one band with 2+ elements
    if len(bands) < 2:
        return []

    has_multi_element_band = any(len(band) >= 2 for band in bands)
    if not has_multi_element_band:
        return []

    # All bands must be non-trivial split (not just 1 element per band = no grouping benefit)
    # If every band has exactly 1 element, this is just a vertical list -- no split needed
    if all(len(band) == 1 for band in bands):
        return []

    sub_groups = []
    for idx, band in enumerate(bands):
        band_ids = [item[0] for item in band]
        if len(band) >= 2:
            label = f'{parent_name}-row-{idx + 1}'
            reason = f'Y-band cluster ({len(band)} elements, y\u2248{int(band[0][1])})'
        else:
            label = f'{parent_name}-row-{idx + 1}'
            reason = f'Y-band single (y\u2248{int(band[0][1])})'

        sub_groups.append({
            'name': label,
            'pattern': 'single' if len(band_ids) == 1 else 'list',
            'node_ids': band_ids,
            'reason': reason,
        })

    return sub_groups

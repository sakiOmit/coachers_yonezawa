"""Core detection functions for figma-prepare.

Heading detection, heading-content pair detection, zone bbox computation,
loose element absorption, and re-exports from detection_patterns and
detection_semantic for backward compatibility.
"""

from .constants import (
    HEADING_MAX_CHILDREN,
    HEADING_MAX_HEIGHT_RATIO,
    HEADING_SOFT_HEIGHT_RATIO,
    HEADING_TEXT_RATIO,
    LOOSE_ABSORPTION_DISTANCE,
    LOOSE_ELEMENT_MAX_HEIGHT,
)
from .geometry import filter_visible_children, get_bbox

# Re-export everything from sub-modules for backward compatibility.
# All internal modules that do `from .detection import X` will still work.
from .detection_patterns import (  # noqa: F401
    detect_repeating_tuple,
    detect_consecutive_similar,
    detect_highlight_text,
    detect_en_jp_label_pairs,
    _check_rect_text_overlap,
    _find_rect_text_overlaps,
    _is_en_label,
    _is_jp_text,
    _pair_distance,
)
from .detection_semantic import (  # noqa: F401
    is_decoration_pattern,
    decoration_dominant_shape,
    detect_horizontal_bar,
    detect_bg_content_layers,
    detect_table_rows,
    _cluster_by_y_band,
    _expand_y_band,
    _infer_bar_name,
    _is_valid_horizontal_bar,
    _find_bg_rectangle,
    _classify_decorations,
    _find_table_row_backgrounds,
    _find_table_dividers,
    _assign_members_to_rows,
    _include_table_headings,
    _infer_table_name,
)


def is_heading_like(node):
    """Check if a node looks like a section heading (small, text-heavy, decorative).

    Heading frames typically contain: title text + subtitle text + decorative
    elements (dots, vectors). They are small relative to content sections.

    Args:
        node: Figma node dict with children.

    Returns:
        bool: True if node appears to be a heading frame.
    """
    children = filter_visible_children(node)
    if not children:
        return False
    if len(children) > HEADING_MAX_CHILDREN:
        return False

    # Count leaf descendants by type
    def count_leaves(n):
        ch = filter_visible_children(n)
        if not ch:
            return {n.get('type', 'UNKNOWN'): 1}
        counts = {}
        for c in ch:
            for t, cnt in count_leaves(c).items():
                counts[t] = counts.get(t, 0) + cnt
        return counts

    leaf_counts = count_leaves(node)
    total_leaves = sum(leaf_counts.values())
    if total_leaves == 0:
        return False

    # Issue 175: ELLIPSE-dominated frames are decoration, not headings.
    # A heading MUST have at least as many TEXT nodes as ELLIPSE nodes.
    ellipse_count = leaf_counts.get('ELLIPSE', 0)
    text_count = leaf_counts.get('TEXT', 0)
    if ellipse_count > text_count:
        return False

    text_vector_count = (text_count
                         + leaf_counts.get('VECTOR', 0)
                         + ellipse_count)
    return (text_vector_count / total_leaves) >= HEADING_TEXT_RATIO


def detect_heading_content_pairs(children):
    """Detect heading-like frame followed by larger content frame.

    Pattern: a small "heading-like" frame (mostly text/vector, small height
    relative to siblings) followed by a larger "content" frame.

    Args:
        children: List of sibling nodes.

    Returns:
        list of pairs: [{'heading_idx': i, 'content_idx': j, 'children': [h, c]}]
    """
    if len(children) < 2:
        return []

    pairs = []
    used = set()

    for i in range(len(children) - 1):
        if i in used:
            continue

        h = children[i]
        c = children[i + 1]

        h_bb = get_bbox(h)
        c_bb = get_bbox(c)
        if not h_bb or not c_bb:
            continue

        # Three-tier height ratio logic (Issue 205):
        #   < 40% (HEADING_MAX_HEIGHT_RATIO): Clearly a heading — auto-pair
        #   40-80% (soft zone): Ambiguous height ratio, but if is_heading_like()
        #     passes below, treat as heading. This rescues heading frames with
        #     decorative elements (borders, backgrounds) that inflate height.
        #   >= 80% (HEADING_SOFT_HEIGHT_RATIO): Too tall to be a heading — skip
        if h_bb['h'] >= c_bb['h'] * HEADING_MAX_HEIGHT_RATIO:
            if h_bb['h'] >= c_bb['h'] * HEADING_SOFT_HEIGHT_RATIO:
                continue

        if not is_heading_like(h):
            continue

        # Content must be a substantial frame
        c_type = c.get('type', '')
        if c_type not in ('FRAME', 'GROUP', 'COMPONENT', 'INSTANCE', 'SECTION'):
            continue
        if not c.get('children'):
            continue

        pairs.append({
            'heading_idx': i,
            'content_idx': i + 1,
            'children': [h, c]
        })
        used.add(i)
        used.add(i + 1)

    return pairs


def _compute_zone_bboxes(children, candidate_groups):
    """Compute vertical bounding box for each candidate group from its member nodes.

    Args:
        children: list of sibling nodes.
        candidate_groups: list of dicts, each with 'node_ids' list.

    Returns:
        list of dicts: [{'y_top': float, 'y_bot': float,
                         'representative_idx': int, 'member_indices': set}]
    """
    child_id_to_idx = {ch.get('id', ''): idx for idx, ch in enumerate(children)}
    zone_bboxes = []
    for cg in candidate_groups:
        member_indices = [child_id_to_idx[nid] for nid in cg.get('node_ids', [])
                          if nid in child_id_to_idx]
        if not member_indices:
            continue
        y_tops = []
        y_bots = []
        for mi in member_indices:
            mbb = get_bbox(children[mi])
            if mbb:
                y_tops.append(mbb['y'])
                y_bots.append(mbb['y'] + mbb['h'])
        if y_tops and y_bots:
            zone_bboxes.append({
                'y_top': min(y_tops),
                'y_bot': max(y_bots),
                'representative_idx': member_indices[0],
                'member_indices': set(member_indices),
            })
    return zone_bboxes


def _classify_loose_element(child, bb):
    """Check if a child element qualifies as a "loose" element for absorption.

    Loose elements are LINE nodes, small leaf shapes, or small rectangles
    that float between grouped sections.

    Args:
        child: Figma node dict.
        bb: Bounding box dict with x, y, w, h.

    Returns:
        tuple: (is_loose: bool, reason: str)
    """
    child_type = child.get('type', '')

    # 1. LINE type (always loose)
    if child_type == 'LINE':
        return True, 'LINE element'
    # 2. Small height element (divider-like) without children
    if bb['h'] <= LOOSE_ELEMENT_MAX_HEIGHT and not child.get('children'):
        return True, f'small leaf (h={bb["h"]}px)'
    # 3. Small shape element (RECTANGLE/VECTOR)
    if bb['h'] <= LOOSE_ELEMENT_MAX_HEIGHT and child_type in ('RECTANGLE', 'VECTOR'):
        return True, f'small shape (h={bb["h"]}px)'

    return False, ''


def _find_nearest_group(i, bb, zone_bboxes, group_indices_set, children):
    """Find the nearest group for a loose element using zone-level and member-level checks.

    Two-pass approach (Issue 167 fix):
    1. Zone-level: Check if the element's Y-center falls within a zone's bbox.
    2. Member-level: Check distance to individual group members.

    Args:
        i: Index of the loose element in children.
        bb: Bounding box of the loose element.
        zone_bboxes: Pre-computed zone bounding boxes (may be empty).
        group_indices_set: Set of indices already in groups.
        children: List of all sibling nodes.

    Returns:
        tuple: (best_group_idx, best_distance, zone_matched)
    """
    best_group_idx = None
    best_distance = float('inf')
    zone_matched = False

    # --- Pass 1: Zone-level bounding box check ---
    # If the loose element's Y-center falls within any zone's vertical
    # extent, absorb it into that zone (distance=0).
    if zone_bboxes:
        elem_cy = bb['y'] + bb['h'] / 2
        for zb in zone_bboxes:
            if i in zb['member_indices']:
                continue  # skip if already a member
            # Check if element center is within zone bbox
            if zb['y_top'] <= elem_cy <= zb['y_bot']:
                # Element is inside the zone's vertical span
                if 0.0 < best_distance:
                    best_distance = 0.0
                    best_group_idx = zb['representative_idx']
                    zone_matched = True
            else:
                # Vertical distance to zone bbox edges
                if elem_cy < zb['y_top']:
                    dist = zb['y_top'] - (bb['y'] + bb['h'])
                else:
                    dist = bb['y'] - zb['y_bot']
                dist = max(0.0, dist)
                if dist < best_distance:
                    best_distance = dist
                    best_group_idx = zb['representative_idx']
                    zone_matched = (dist < LOOSE_ABSORPTION_DISTANCE)

    # --- Pass 2: Member-level fallback ---
    # Also check individual members; a closer member overrides zone result.
    for gi in group_indices_set:
        g_bb = get_bbox(children[gi])
        if not g_bb:
            continue

        # Vertical distance between element and group member
        if bb['y'] + bb['h'] <= g_bb['y']:
            dist = g_bb['y'] - (bb['y'] + bb['h'])
        elif g_bb['y'] + g_bb['h'] <= bb['y']:
            dist = bb['y'] - (g_bb['y'] + g_bb['h'])
        else:
            dist = 0  # overlapping

        if dist < best_distance:
            best_distance = dist
            best_group_idx = gi

    return best_group_idx, best_distance, zone_matched


def find_absorbable_elements(children, group_indices_set, candidate_groups=None):
    """Find loose elements (dividers, small frames) that should be absorbed
    into nearby groups.

    Loose elements are LINE nodes, small leaf shapes, or small rectangles
    that float between grouped sections. They should be merged into the
    nearest existing group.

    Two-pass approach (Issue 167 fix):
    1. Zone-level: If candidate_groups are provided, check if the loose
       element's Y-center falls within a zone's bounding box (y_top..y_bot).
       Elements inside a zone get distance=0 (overlap). This handles
       root-level dividers that sit between zone members but within the
       zone's vertical span.
    2. Member-level fallback: Check distance to individual group members
       using LOOSE_ABSORPTION_DISTANCE (original behavior).

    Args:
        children: list of sibling nodes.
        group_indices_set: set of indices already in groups.
        candidate_groups: optional list of candidate group dicts, each with
            'node_ids' (list of child node IDs). When provided, enables
            zone-level bounding box matching for root-level absorption.

    Returns:
        list of absorptions: [{'element_idx': i, 'target_group_idx': j,
                                'distance': float, 'reason': '...'}]
    """
    absorptions = []

    # Pre-compute zone bounding boxes if candidate groups provided
    zone_bboxes = _compute_zone_bboxes(children, candidate_groups) if candidate_groups else []

    for i, child in enumerate(children):
        if i in group_indices_set:
            continue

        bb = get_bbox(child)
        if not bb:
            continue

        is_loose, reason = _classify_loose_element(child, bb)
        if not is_loose:
            continue

        best_group_idx, best_distance, zone_matched = _find_nearest_group(
            i, bb, zone_bboxes, group_indices_set, children
        )

        # Accept if:
        # - zone_matched (element center is within a zone's vertical span), OR
        # - best_distance < LOOSE_ABSORPTION_DISTANCE (member-level proximity)
        if best_group_idx is not None and (zone_matched or best_distance < LOOSE_ABSORPTION_DISTANCE):
            absorptions.append({
                'element_idx': i,
                'target_group_idx': best_group_idx,
                'distance': best_distance,
                'reason': reason
            })

    return absorptions

"""Semantic and pattern detection functions for figma-prepare."""

import re
import statistics

from .constants import (
    BG_DECORATION_MAX_AREA_RATIO,
    BG_LEFT_OVERFLOW_WIDTH_RATIO,
    BG_MIN_HEIGHT_RATIO,
    BG_WIDTH_RATIO,
    CONSECUTIVE_PATTERN_MIN,
    DECORATION_MAX_SIZE,
    DECORATION_MIN_SHAPES,
    DECORATION_SHAPE_RATIO,
    EN_JP_PAIR_MAX_DISTANCE,
    EN_LABEL_MAX_WORDS,
    HEADING_MAX_CHILDREN,
    HEADING_MAX_HEIGHT_RATIO,
    HEADING_SOFT_HEIGHT_RATIO,
    HEADING_TEXT_RATIO,
    HIGHLIGHT_HEIGHT_RATIO_MAX,
    HIGHLIGHT_HEIGHT_RATIO_MIN,
    HIGHLIGHT_OVERLAP_RATIO,
    HIGHLIGHT_TEXT_MAX_LEN,
    HIGHLIGHT_X_OVERLAP_RATIO,
    HORIZONTAL_BAR_MAX_HEIGHT,
    HORIZONTAL_BAR_MIN_ELEMENTS,
    HORIZONTAL_BAR_VARIANCE_RATIO,
    JACCARD_THRESHOLD,
    LOOSE_ABSORPTION_DISTANCE,
    LOOSE_ELEMENT_MAX_HEIGHT,
    OVERFLOW_BG_MIN_WIDTH,
    TABLE_DIVIDER_MAX_HEIGHT,
    TABLE_MIN_ROWS,
    TABLE_ROW_WIDTH_RATIO,
    TUPLE_MAX_SIZE,
    TUPLE_PATTERN_MIN,
)
from .geometry import get_bbox
from .metadata import get_text_children_content
from .naming import to_kebab
from .scoring import structure_hash, structure_similarity


def detect_repeating_tuple(children):
    """Detect repeating tuple patterns in flat sibling lists.

    Blog cards often consist of N separated sibling elements (e.g., IMAGE +
    FRAME + INSTANCE) repeated K times, producing N*K flat siblings. Standard
    structure_hash detection fails because each element within a tuple has a
    different type.

    This function detects such patterns by examining the sequence of element
    types and finding repeating subsequences of length 2..TUPLE_MAX_SIZE that
    repeat >= TUPLE_PATTERN_MIN times consecutively.

    Args:
        children: List of Figma node dicts with at least 'type', 'name', 'id'.

    Returns:
        list of detected tuple groups:
        [{'tuple_size': N, 'start_idx': S, 'count': C, 'children_indices': [...]}]
        - tuple_size: number of elements per tuple
        - start_idx: index of first element in the pattern
        - count: number of repetitions
        - children_indices: flat list of all element indices in the pattern

    Issue 186: Separated card patterns (IMAGE + FRAME + INSTANCE x 3).
    """
    children = [c for c in children if c.get('visible') != False]
    if len(children) < TUPLE_PATTERN_MIN * 2:
        # Need at least min_reps * 2 elements (smallest tuple_size is 2)
        return []

    types = [c.get('type', '') for c in children]
    n = len(types)
    results = []
    covered = set()  # Track indices already assigned to a tuple group

    # Try tuple sizes from largest to smallest (prefer larger tuples)
    for tuple_size in range(min(TUPLE_MAX_SIZE, n // TUPLE_PATTERN_MIN), 1, -1):
        # Slide a window across the type sequence
        start = 0
        while start + tuple_size * TUPLE_PATTERN_MIN <= n:
            if start in covered:
                start += 1
                continue

            reference = types[start:start + tuple_size]
            # Tuple must contain at least 2 distinct types (otherwise
            # detect_consecutive_similar handles homogeneous sequences)
            if len(set(reference)) < 2:
                start += 1
                continue
            reps = 1
            pos = start + tuple_size

            while pos + tuple_size <= n:
                candidate = types[pos:pos + tuple_size]
                if candidate == reference:
                    reps += 1
                    pos += tuple_size
                else:
                    break

            if reps >= TUPLE_PATTERN_MIN:
                indices = list(range(start, start + tuple_size * reps))
                # Check no overlap with already covered indices
                if not any(i in covered for i in indices):
                    results.append({
                        'tuple_size': tuple_size,
                        'start_idx': start,
                        'count': reps,
                        'children_indices': indices,
                    })
                    covered.update(indices)
                    start = start + tuple_size * reps
                    continue

            start += 1

    return results


def detect_consecutive_similar(children, min_count=None, similarity_threshold=None):
    """Detect runs of 3+ consecutive siblings with similar structure_hash.

    Unlike detect_pattern_groups which clusters ALL matching patterns regardless
    of position, this function only groups elements that are adjacent siblings.
    This is important for top-level sections where menu-1, menu-2, menu-3 should
    be grouped but non-adjacent similar frames should not.

    Args:
        children: List of child nodes.
        min_count: Minimum consecutive siblings to form a group (default: 3).
        similarity_threshold: Jaccard similarity threshold (default: 0.7).

    Returns:
        list of groups: [{'indices': [0,1,2], 'children': [...], 'hash': '...'}]
    """
    if min_count is None:
        min_count = CONSECUTIVE_PATTERN_MIN
    if similarity_threshold is None:
        similarity_threshold = JACCARD_THRESHOLD

    if len(children) < min_count:
        return []

    hashes = [structure_hash(c) for c in children]
    groups = []
    i = 0
    while i < len(children):
        run = [i]
        base_hash = hashes[i]
        j = i + 1
        while j < len(children):
            sim = structure_similarity(base_hash, hashes[j])
            if sim >= similarity_threshold:
                run.append(j)
                j += 1
            else:
                break
        if len(run) >= min_count:
            groups.append({
                'indices': run,
                'children': [children[idx] for idx in run],
                'hash': base_hash
            })
            i = j  # skip past the run
        else:
            i += 1
    return groups


def is_heading_like(node):
    """Check if a node looks like a section heading (small, text-heavy, decorative).

    Heading frames typically contain: title text + subtitle text + decorative
    elements (dots, vectors). They are small relative to content sections.

    Args:
        node: Figma node dict with children.

    Returns:
        bool: True if node appears to be a heading frame.
    """
    children = [c for c in node.get('children', []) if c.get('visible') != False]
    if not children:
        return False
    if len(children) > HEADING_MAX_CHILDREN:
        return False

    # Count leaf descendants by type
    def count_leaves(n):
        ch = [c for c in n.get('children', []) if c.get('visible') != False]
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
        if 'ニュース' in t_lower or 'news' in t_lower or 'お知らせ' in t_lower:
            return 'news-bar'
        if 'ブログ' in t_lower or 'blog' in t_lower:
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


def _is_en_label(text):
    """Check if text is a short uppercase ASCII label.

    Args:
        text: Text string to check.

    Returns:
        bool: True if text is a short (1-3 word) uppercase ASCII label.

    Issue 185: EN+JP label pair detection.
    """
    ascii_only = re.sub(r'[^\x00-\x7f]', '', text).strip()
    if not ascii_only or ascii_only != text.strip():
        return False
    words = ascii_only.split()
    if len(words) < 1 or len(words) > EN_LABEL_MAX_WORDS:
        return False
    # Must be uppercase (allow minor punctuation)
    alpha_chars = re.sub(r'[^a-zA-Z]', '', ascii_only)
    if not alpha_chars:
        return False
    return alpha_chars == alpha_chars.upper()


def _is_jp_text(text):
    """Check if text contains non-ASCII (Japanese) characters.

    Args:
        text: Text string to check.

    Returns:
        bool: True if text contains non-ASCII characters.

    Issue 185: EN+JP label pair detection.
    """
    non_ascii = re.sub(r'[\x00-\x7f]', '', text).strip()
    return len(non_ascii) > 0


def _pair_distance(node_a, node_b):
    """Compute minimum distance between two nodes (Y-range or X-range proximity).

    Args:
        node_a: First Figma node dict with absoluteBoundingBox.
        node_b: Second Figma node dict with absoluteBoundingBox.

    Returns:
        float: Minimum edge-to-edge distance between the two nodes.

    Issue 185: EN+JP label pair detection.
    """
    bb_a = get_bbox(node_a)
    bb_b = get_bbox(node_b)
    # Y distance
    if bb_a['y'] + bb_a['h'] < bb_b['y']:
        dy = bb_b['y'] - (bb_a['y'] + bb_a['h'])
    elif bb_b['y'] + bb_b['h'] < bb_a['y']:
        dy = bb_a['y'] - (bb_b['y'] + bb_b['h'])
    else:
        dy = 0
    # X distance
    if bb_a['x'] + bb_a['w'] < bb_b['x']:
        dx = bb_b['x'] - (bb_a['x'] + bb_a['w'])
    elif bb_b['x'] + bb_b['w'] < bb_a['x']:
        dx = bb_a['x'] - (bb_b['x'] + bb_b['w'])
    else:
        dx = 0
    return min(dx, dy) if dx > 0 and dy > 0 else max(dx, dy)


def detect_en_jp_label_pairs(children):
    """Detect English + Japanese label pairs among sibling TEXT nodes.

    Pattern: An uppercase ASCII text (e.g., "COMPANY") paired with a
    Japanese text (e.g., "会社情報") at similar Y or X position.

    Args:
        children: List of sibling nodes.

    Returns:
        list of pairs: [{'en_idx': i, 'jp_idx': j, 'en_text': '...', 'jp_text': '...'}]

    Issue 185: EN+JP label pairs get generic names. Detect them for
    semantic renaming (en-label-* / heading-*).
    """
    children = [c for c in children if c.get('visible') != False]
    if len(children) < 2:
        return []

    # Collect TEXT nodes with their indices
    text_nodes = []
    for i, child in enumerate(children):
        if child.get('type') != 'TEXT':
            continue
        content = child.get('characters', '') or child.get('name', '')
        if not content or not content.strip():
            continue
        text_nodes.append((i, child, content.strip()))

    if len(text_nodes) < 2:
        return []

    # Find all EN labels and JP texts
    en_indices = [(i, node, text) for i, node, text in text_nodes if _is_en_label(text)]
    jp_indices = [(i, node, text) for i, node, text in text_nodes if _is_jp_text(text)]

    pairs = []
    used_en = set()
    used_jp = set()

    for en_i, en_node, en_text in en_indices:
        best_jp = None
        best_dist = float('inf')
        for jp_i, jp_node, jp_text in jp_indices:
            if jp_i in used_jp:
                continue
            dist = _pair_distance(en_node, jp_node)
            if dist <= EN_JP_PAIR_MAX_DISTANCE and dist < best_dist:
                best_dist = dist
                best_jp = (jp_i, jp_node, jp_text)
        if best_jp and en_i not in used_en:
            jp_i, jp_node, jp_text = best_jp
            pairs.append({
                'en_idx': en_i,
                'jp_idx': jp_i,
                'en_text': en_text,
                'jp_text': jp_text,
            })
            used_en.add(en_i)
            used_jp.add(jp_i)

    return pairs


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

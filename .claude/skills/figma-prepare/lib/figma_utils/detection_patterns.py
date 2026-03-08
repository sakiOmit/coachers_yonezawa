"""Pattern-based detection functions for figma-prepare.

Detectors for repeating tuples, consecutive similar elements,
highlight text overlaps, and EN+JP label pairs.
"""

import re

from .constants import (
    CONSECUTIVE_PATTERN_MIN,
    EN_JP_PAIR_MAX_DISTANCE,
    EN_LABEL_MAX_WORDS,
    HIGHLIGHT_HEIGHT_RATIO_MAX,
    HIGHLIGHT_HEIGHT_RATIO_MIN,
    HIGHLIGHT_OVERLAP_RATIO,
    HIGHLIGHT_TEXT_MAX_LEN,
    HIGHLIGHT_X_OVERLAP_RATIO,
    JACCARD_THRESHOLD,
    TUPLE_MAX_SIZE,
    TUPLE_PATTERN_MIN,
)
from .geometry import get_bbox
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

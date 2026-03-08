"""Scoring, structure hashing, and layout inference for figma-prepare."""

import statistics
from collections import Counter

from .constants import CV_THRESHOLD, ROW_TOLERANCE


def alignment_bonus(a_bb, b_bb, tolerance=2):
    """Check if two bounding boxes share an alignment axis.

    Returns 0.5 if any edge or center aligns within tolerance, else 1.0.
    A return of 0.5 means effective distance is halved (strong alignment signal).
    """
    a_cx = a_bb['x'] + a_bb['w'] / 2
    b_cx = b_bb['x'] + b_bb['w'] / 2
    a_cy = a_bb['y'] + a_bb['h'] / 2
    b_cy = b_bb['y'] + b_bb['h'] / 2

    checks = [
        abs(a_bb['x'] - b_bb['x']),                           # left edge
        abs((a_bb['x'] + a_bb['w']) - (b_bb['x'] + b_bb['w'])),  # right edge
        abs(a_cx - b_cx),                                      # center X
        abs(a_bb['y'] - b_bb['y']),                            # top edge
        abs((a_bb['y'] + a_bb['h']) - (b_bb['y'] + b_bb['h'])),  # bottom edge
        abs(a_cy - b_cy),                                      # center Y
    ]
    if any(c <= tolerance for c in checks):
        return 0.5
    return 1.0


def size_similarity_bonus(a_bb, b_bb, ratio_threshold=0.20):
    """Check if two bounding boxes have similar dimensions.

    Returns 0.7 if both width and height differ by <= ratio_threshold, else 1.0.
    """
    if a_bb['w'] <= 0 or a_bb['h'] <= 0 or b_bb['w'] <= 0 or b_bb['h'] <= 0:
        return 1.0
    w_ratio = abs(a_bb['w'] - b_bb['w']) / max(a_bb['w'], b_bb['w'])
    h_ratio = abs(a_bb['h'] - b_bb['h']) / max(a_bb['h'], b_bb['h'])
    if w_ratio <= ratio_threshold and h_ratio <= ratio_threshold:
        return 0.7
    return 1.0


def _raw_distance(a_bb, b_bb):
    """Calculate minimum distance between two bounding boxes."""
    if a_bb['x'] + a_bb['w'] < b_bb['x']:
        dx = b_bb['x'] - (a_bb['x'] + a_bb['w'])
    elif b_bb['x'] + b_bb['w'] < a_bb['x']:
        dx = a_bb['x'] - (b_bb['x'] + b_bb['w'])
    else:
        dx = 0

    if a_bb['y'] + a_bb['h'] < b_bb['y']:
        dy = b_bb['y'] - (a_bb['y'] + a_bb['h'])
    elif b_bb['y'] + b_bb['h'] < a_bb['y']:
        dy = a_bb['y'] - (b_bb['y'] + b_bb['h'])
    else:
        dy = 0

    return (dx * dx + dy * dy) ** 0.5


def compute_grouping_score(a_bb, b_bb, gap=24):
    """Compute grouping affinity score between two bounding boxes.

    Combines raw distance with alignment and size similarity bonuses.
    Returns 0.0-1.0. Score > 0.5 indicates grouping candidate.

    Backward compatible: raw distance <= gap always yields score >= 0.5.
    Issue 136: Guard against gap <= 0 to prevent ZeroDivisionError.
    """
    if gap <= 0:
        # With zero gap, only overlapping/touching elements score 1.0
        raw = _raw_distance(a_bb, b_bb)
        return 1.0 if raw == 0 else 0.0
    raw = _raw_distance(a_bb, b_bb)
    effective = raw * alignment_bonus(a_bb, b_bb) * size_similarity_bonus(a_bb, b_bb)
    return max(0.0, 1.0 - effective / (gap * 2))


def structure_hash(node):
    """Calculate structure hash from child types and count.

    Issue 128: Moved from detect-grouping-candidates.sh to share with
    structure_similarity (which parses the hash format produced here).

    Format: "TYPE:[CHILD_TYPE1,CHILD_TYPE2,...]" (sorted child types).
    Leaf nodes return just "TYPE".
    """
    children = [c for c in node.get('children', []) if c.get('visible') != False]
    if not children:
        return node.get('type', 'UNKNOWN')
    child_types = sorted(c.get('type', '') for c in children)
    return f"{node.get('type', 'UNKNOWN')}:[{','.join(child_types)}]"


def structure_similarity(hash_a, hash_b):
    """Compute Jaccard similarity between two structure hashes.

    Structure hash format: "TYPE:[CHILD_TYPE1,CHILD_TYPE2,...]"
    Treats child type lists as multisets for comparison.
    Returns 0.0-1.0.
    """
    def _parse_children(h):
        bracket = h.find('[')
        if bracket < 0:
            return []
        inner = h[bracket + 1:h.rfind(']')]
        return inner.split(',') if inner else []

    a_children = _parse_children(hash_a)
    b_children = _parse_children(hash_b)

    if not a_children and not b_children:
        return 1.0 if hash_a == hash_b else 0.0

    # Multiset Jaccard
    ca = Counter(a_children)
    cb = Counter(b_children)
    all_keys = set(ca) | set(cb)
    intersection = sum(min(ca[k], cb[k]) for k in all_keys)
    union = sum(max(ca[k], cb[k]) for k in all_keys)
    return intersection / union if union > 0 else 0.0


def detect_regular_spacing(children_bboxes, axis='auto'):
    """Detect if children are regularly spaced along an axis.

    Args:
        children_bboxes: List of bbox dicts with x, y, w, h.
        axis: 'x', 'y', or 'auto' (auto-detect from variance).

    Returns:
        bool: True if coefficient of variation of gaps < 0.25.
    """
    if len(children_bboxes) < 3:
        return False

    if axis == 'auto':
        xs = [b['x'] for b in children_bboxes]
        ys = [b['y'] for b in children_bboxes]
        x_range = max(xs) - min(xs) if xs else 0
        y_range = max(ys) - min(ys) if ys else 0
        axis = 'x' if x_range > y_range else 'y'

    if axis == 'x':
        sorted_bb = sorted(children_bboxes, key=lambda b: b['x'])
        gaps = [sorted_bb[i+1]['x'] - (sorted_bb[i]['x'] + sorted_bb[i]['w'])
                for i in range(len(sorted_bb) - 1)]
    else:
        sorted_bb = sorted(children_bboxes, key=lambda b: b['y'])
        gaps = [sorted_bb[i+1]['y'] - (sorted_bb[i]['y'] + sorted_bb[i]['h'])
                for i in range(len(sorted_bb) - 1)]

    # Filter out negative gaps (overlapping elements)
    gaps = [g for g in gaps if g >= 0]
    if len(gaps) < 2:
        return False

    mean_gap = statistics.mean(gaps)
    if mean_gap <= 0:
        return True  # Zero gap = perfectly regular (edge-to-edge placement)
    std_gap = statistics.stdev(gaps)
    cv = std_gap / mean_gap
    return cv < CV_THRESHOLD


def infer_direction_two_elements(c1_bb, c2_bb):
    """Infer layout direction for exactly two elements.

    Uses direct dx vs dy comparison instead of variance (which is
    meaningless for n=2).
    """
    c1_cx = c1_bb['x'] + c1_bb['w'] / 2
    c2_cx = c2_bb['x'] + c2_bb['w'] / 2
    c1_cy = c1_bb['y'] + c1_bb['h'] / 2
    c2_cy = c2_bb['y'] + c2_bb['h'] / 2

    dx = abs(c1_cx - c2_cx)
    dy = abs(c1_cy - c2_cy)
    return 'HORIZONTAL' if dx > dy else 'VERTICAL'


def detect_wrap(children_bboxes, direction, row_tolerance=None):
    """Detect if children wrap to multiple rows/columns.

    Args:
        children_bboxes: List of bbox dicts.
        direction: 'HORIZONTAL' or 'VERTICAL'.
        row_tolerance: Max Y (or X) difference to be considered same row.
            Defaults to ROW_TOLERANCE (Issue 131).

    Returns:
        bool: True if HORIZONTAL with 4+ elements wrapping to 2+ rows.
    """
    if row_tolerance is None or row_tolerance <= 0:
        row_tolerance = ROW_TOLERANCE
    if direction != 'HORIZONTAL' or len(children_bboxes) < 4:
        return False

    # Issue 251: Use distance-based grouping instead of rounding to avoid
    # false row splits when Y values straddle a rounding boundary
    sorted_ys = sorted(set(b['y'] for b in children_bboxes))
    row_count = 1
    for i in range(1, len(sorted_ys)):
        if sorted_ys[i] - sorted_ys[i - 1] > row_tolerance:
            row_count += 1
    return row_count >= 2


def detect_space_between(children_bboxes, direction, frame_bb, tolerance=4):
    """Detect SPACE_BETWEEN alignment.

    Returns True if first element touches start edge and last element
    touches end edge of the frame.
    """
    if len(children_bboxes) < 2:
        return False

    if direction in ('HORIZONTAL', 'WRAP'):
        sorted_bb = sorted(children_bboxes, key=lambda b: b['x'])
        start_touch = abs(sorted_bb[0]['x'] - frame_bb['x']) <= tolerance
        end_touch = abs((sorted_bb[-1]['x'] + sorted_bb[-1]['w']) -
                        (frame_bb['x'] + frame_bb['w'])) <= tolerance
    else:
        sorted_bb = sorted(children_bboxes, key=lambda b: b['y'])
        start_touch = abs(sorted_bb[0]['y'] - frame_bb['y']) <= tolerance
        end_touch = abs((sorted_bb[-1]['y'] + sorted_bb[-1]['h']) -
                        (frame_bb['y'] + frame_bb['h'])) <= tolerance

    return start_touch and end_touch


def compute_gap_consistency(gaps):
    """Compute coefficient of variation for gap values.

    Returns float: CoV = std / mean. 0.0 means perfectly uniform.
    Returns 1.0 for empty/single gap or zero mean.
    """
    if len(gaps) < 2:
        return 0.0 if len(gaps) == 1 else 1.0

    mean_val = statistics.mean(gaps)
    if mean_val <= 0:
        return 1.0
    return statistics.stdev(gaps) / mean_val

"""Decoration pattern detection for figma-prepare.

Detects small decorative frames containing dot grids, scattered shapes, etc.

Issue 189: Small decorative frames containing dot patterns.
"""

from .constants import (
    DECORATION_MAX_SIZE,
    DECORATION_MIN_SHAPES,
    DECORATION_SHAPE_RATIO,
)


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

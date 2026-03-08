"""Semantic grouping detection for figma-prepare Phase 2.

Contains card/navigation/grid detection and semantic group assembly.
Extracted from grouping_engine.py for modularity.
"""

from collections import defaultdict

from .constants import (
    GRID_SIZE_SIMILARITY,
    HEADER_TEXT_MAX_WIDTH,
    ROW_TOLERANCE,
)
from .geometry import get_bbox


def is_card_like(node):
    """Detect card-like structure: FRAME/COMPONENT/INSTANCE with 2-6 children including IMAGE+TEXT."""
    if node.get('type') not in ('FRAME', 'COMPONENT', 'INSTANCE'):
        return False
    children = [c for c in node.get('children', []) if c.get('visible') != False]
    if not (2 <= len(children) <= 6):
        return False
    types = [c.get('type', '') for c in children]
    has_image = 'RECTANGLE' in types or 'IMAGE' in types
    has_text = 'TEXT' in types
    # Also check one level down for text
    if not has_text:
        for c in children:
            if c.get('type') in ('FRAME', 'GROUP'):
                sub_types = [sc.get('type', '') for sc in c.get('children', []) if sc.get('visible') != False]
                if 'TEXT' in sub_types:
                    has_text = True
                    break
    return has_image and has_text


def is_navigation_like(children):
    """Detect navigation-like pattern: 4+ horizontal text-sized elements."""
    if len(children) < 4:
        return False
    bboxes = [get_bbox(c) for c in children]
    xs = [b['x'] for b in bboxes]
    ys = [b['y'] for b in bboxes]
    x_range = max(xs) - min(xs) if xs else 0
    y_range = max(ys) - min(ys) if ys else 0
    if x_range <= y_range:
        return False  # not horizontal
    # Check all elements are narrow (text-like) — Issue 141: use named constant
    return all(b['w'] < HEADER_TEXT_MAX_WIDTH for b in bboxes)


def is_grid_like(children):
    """Detect grid-like pattern: 2+ rows x 2+ columns of similar-sized elements."""
    if len(children) < 4:
        return False
    bboxes = [get_bbox(c) for c in children]

    # Group by Y position (row detection)
    # Issue 131: Use shared ROW_TOLERANCE constant
    rows = defaultdict(list)
    for b in bboxes:
        row_key = round(b['y'] / ROW_TOLERANCE)
        rows[row_key].append(b)

    if len(rows) < 2:
        return False

    # Check each row has 2+ elements
    if not all(len(r) >= 2 for r in rows.values()):
        return False

    # Check size similarity (20% threshold)
    widths = [b['w'] for b in bboxes]
    heights = [b['h'] for b in bboxes]
    if max(widths) <= 0 or max(heights) <= 0:
        return False
    w_ratio = (max(widths) - min(widths)) / max(widths)
    h_ratio = (max(heights) - min(heights)) / max(heights)
    return w_ratio <= GRID_SIZE_SIMILARITY and h_ratio <= GRID_SIZE_SIMILARITY


def detect_semantic_groups(children):
    """Structural semantic detection (fills-independent, Issue 29/30 safe)."""
    result = []

    # Card detection: find 3+ card-like siblings
    cards = [c for c in children if is_card_like(c)]
    if len(cards) >= 3:
        result.append({
            'method': 'semantic',
            'semantic_type': 'card-list',
            'node_ids': [c.get('id', '') for c in cards],
            'node_names': [c.get('name', '') for c in cards],
            'count': len(cards),
            'suggested_name': 'card-list',
            'suggested_wrapper': 'card-container',
        })

    # Navigation detection
    if is_navigation_like(children):
        result.append({
            'method': 'semantic',
            'semantic_type': 'navigation',
            'node_ids': [c.get('id', '') for c in children],
            'node_names': [c.get('name', '') for c in children],
            'count': len(children),
            'suggested_name': 'nav-items',
            'suggested_wrapper': 'nav-container',
        })

    # Grid detection
    if is_grid_like(children):
        result.append({
            'method': 'semantic',
            'semantic_type': 'grid',
            'node_ids': [c.get('id', '') for c in children],
            'node_names': [c.get('name', '') for c in children],
            'count': len(children),
            'suggested_name': 'grid-items',
            'suggested_wrapper': 'grid-container',
        })

    return result

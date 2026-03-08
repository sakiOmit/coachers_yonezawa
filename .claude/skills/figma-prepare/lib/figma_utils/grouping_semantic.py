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
from .geometry import filter_visible_children, get_bbox

__all__ = [
    "detect_semantic_groups",
    "detect_variant_groups",
    "is_card_like",
    "is_grid_like",
    "is_navigation_like",
]


def is_card_like(node):
    """Detect card-like structure: FRAME/COMPONENT/INSTANCE with 2-6 children including IMAGE+TEXT."""
    if node.get('type') not in ('FRAME', 'COMPONENT', 'INSTANCE'):
        return False
    children = filter_visible_children(node)
    if not (2 <= len(children) <= 6):
        return False
    types = [c.get('type', '') for c in children]
    has_image = 'RECTANGLE' in types or 'IMAGE' in types
    has_text = 'TEXT' in types
    # Also check one level down for text
    if not has_text:
        for c in children:
            if c.get('type') in ('FRAME', 'GROUP'):
                sub_types = [sc.get('type', '') for sc in filter_visible_children(c)]
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
            'score': 0.9,
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
            'score': 0.9,
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
            'score': 0.9,
            'semantic_type': 'grid',
            'node_ids': [c.get('id', '') for c in children],
            'node_names': [c.get('name', '') for c in children],
            'count': len(children),
            'suggested_name': 'grid-items',
            'suggested_wrapper': 'grid-container',
        })

    return result


def detect_variant_groups(children):
    """Detect groups of INSTANCE nodes sharing the same componentId.

    Figma component variants (e.g., Button/Primary, Button/Secondary) share
    the same componentId but may have different internal structure. Standard
    structure_hash matching fails for these because internal nodes differ.

    This detector groups INSTANCEs by componentId, bypassing structure comparison.

    Args:
        children: List of visible sibling nodes.

    Returns:
        List of candidate dicts: [{'method': 'variant', 'node_ids': [...],
                                    'semantic_type': 'variant', 'score': 0.95,
                                    'suggested_name': 'variant-group-N'}]
    """
    component_groups = defaultdict(list)
    for child in children:
        if child.get('type') == 'INSTANCE':
            comp_id = child.get('componentId')
            if comp_id:
                component_groups[comp_id].append(child)

    candidates = []
    idx = 0
    for comp_id, nodes in component_groups.items():
        if len(nodes) >= 2:  # At least 2 instances of same component
            node_ids = [n.get('id', '') for n in nodes if n.get('id')]
            if len(node_ids) >= 2:
                # Try to infer name from component name
                comp_name = nodes[0].get('name', '')
                # Component instances often have names like "Button/Primary"
                slug = comp_name.split('/')[0].strip().lower().replace(' ', '-') if '/' in comp_name else ''
                suggested = f'variant-{slug}-list' if slug else f'variant-group-{idx}'

                candidates.append({
                    'method': 'variant',
                    'node_ids': node_ids,
                    'semantic_type': 'variant',
                    'score': 0.95,  # High confidence: same componentId
                    'suggested_name': suggested,
                })
                idx += 1

    return candidates

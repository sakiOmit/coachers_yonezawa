"""Enriched table generation for figma-prepare."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .constants import (
    BG_WIDTH_RATIO,
    FLAG_BG_FULL_WIDTH_RATIO,
    FLAG_OVERFLOW_X_RATIO,
    FLAG_OVERFLOW_Y_RATIO,
    FLAG_TINY_MAX_SIZE,
    UNNAMED_RE,
)
from .detection import is_decoration_pattern
from .geometry import FigmaNode, filter_visible_children, get_bbox
from .metadata import is_off_canvas


def _collect_text_preview(node, max_depth=3, max_len=30):
    """Recursively collect text content for preview.

    Returns first meaningful text found in descendants, truncated to max_len.
    """
    if node.get('type') == 'TEXT':
        text = node.get('characters', '') or node.get('name', '')
        if text and not UNNAMED_RE.match(text):
            return text[:max_len]
    if max_depth <= 0:
        return ''
    for c in filter_visible_children(node):
        result = _collect_text_preview(c, max_depth - 1, max_len)
        if result:
            return result
    return ''


def _compute_child_types(children):
    """Compute compact child type summary like '2REC+1TEX+1FRA'.

    Uses 3-letter abbreviations sorted alphabetically.
    """
    children = [c for c in children if c.get('visible') != False]
    TYPE_ABBR = {
        'BOOLEAN_OPERATION': 'BOO',
        'COMPONENT': 'CMP',
        'COMPONENT_SET': 'CMS',
        'ELLIPSE': 'ELL',
        'FRAME': 'FRA',
        'GROUP': 'GRP',
        'IMAGE': 'IMG',  # Issue 199: Missing IMAGE type abbreviation
        'INSTANCE': 'INS',
        'LINE': 'LIN',
        'POLYGON': 'POL',
        'RECTANGLE': 'REC',
        'SECTION': 'SEC',
        'STAR': 'STA',
        'TEXT': 'TEX',
        'VECTOR': 'VEC',
    }
    counts = Counter()
    for c in children:
        abbr = TYPE_ABBR.get(c.get('type', ''), 'OTH')
        counts[abbr] += 1
    if not counts:
        return '-'
    return '+'.join(f'{v}{k}' for k, v in sorted(counts.items()))


def _compute_flags(node, page_width, page_height, root_x=0, root_y=0):
    """Compute machine-readable flags for a node.

    Flags:
    - off-canvas: positioned outside viewport (Issue 182)
    - hidden: visible==false (Issue 187)
    - overflow: extends beyond page bounds
    - bg-full: full-width leaf rectangle (background candidate)
    - bg-wide: width > 80% of page but not full-width
    - decoration: small frame with dot/shape pattern (Issue 189)
    - tiny: very small element (< 50x50)
    """
    flags = []
    bb = get_bbox(node)
    node_type = node.get('type', '')
    children = filter_visible_children(node)
    is_leaf = len(children) == 0

    # Visibility
    if node.get('visible') is False:
        flags.append('hidden')

    # Off-canvas
    if page_width > 0 and is_off_canvas(node, page_width, root_x=root_x):
        flags.append('off-canvas')

    # Overflow (extends beyond page on right or bottom)
    # Use root-relative coordinates for correct detection
    rel_x = bb['x'] - root_x
    if page_width > 0:
        right_edge = rel_x + bb['w']
        if right_edge > page_width * FLAG_OVERFLOW_X_RATIO:
            flags.append('overflow')
        rel_y = bb['y'] - root_y
        if page_height > 0 and rel_y + bb['h'] > page_height * FLAG_OVERFLOW_Y_RATIO:
            flags.append('overflow-y')

    # Background candidates
    if is_leaf and node_type in ('RECTANGLE', 'VECTOR', 'ELLIPSE'):
        if page_width > 0:
            width_ratio = bb['w'] / page_width
            if width_ratio >= FLAG_BG_FULL_WIDTH_RATIO:
                flags.append('bg-full')
            elif width_ratio >= BG_WIDTH_RATIO:
                flags.append('bg-wide')

    # Decoration pattern
    if not is_leaf and is_decoration_pattern(node):
        flags.append('decoration')

    # Tiny element
    if bb['w'] > 0 and bb['h'] > 0 and bb['w'] < FLAG_TINY_MAX_SIZE and bb['h'] < FLAG_TINY_MAX_SIZE:
        flags.append('tiny')

    return flags


def _compute_method_tag(node_id, stage_a_candidates):
    """Return method tag for a node if it's in any Stage A candidate.

    Format: "method@score" (e.g., "proximity@0.7") or "-" if not in any candidate.

    Args:
        node_id: Figma node ID string.
        stage_a_candidates: List of candidate dicts with 'method', 'score', 'node_ids'.

    Returns:
        str: Method tag like "proximity@0.7" or "-".
    """
    if not stage_a_candidates:
        return '-'
    for cand in stage_a_candidates:
        if node_id in cand.get('node_ids', []):
            method = cand.get('method', '?')
            score = cand.get('score', 0)
            return f"{method}@{score:.1f}"
    return '-'


def generate_enriched_table(children: list[FigmaNode], page_width: float = 1440, page_height: float = 0,
                            root_x: float = 0, root_y: float = 0,
                            stage_a_candidates: list[dict[str, Any]] | None = None) -> str:
    """Generate enriched Markdown table for Phase B Claude reasoning.

    Produces the enriched format:
    | # | ID | Name | Type | X | Y | Col | W x H | Leaf? | ChildTypes | Flags | Method | Text |

    Col column (Issue 256): L=left, R=right, F=full-width, C=center, -=no columns detected.
    Method column: Stage A detection method and score (e.g., "proximity@0.7") or "-".

    This format provides Claude with enough structural information to detect
    patterns like cards, tables, background layers, etc. without needing
    rule-based Phase A detectors.

    Issue 194: Phase B Claude推論のネストレベル拡張

    Args:
        children: List of Figma child nodes (with absoluteBoundingBox).
        page_width: Page width for flag computation (default: 1440).
        page_height: Page height for overflow detection (default: 0 = skip).
        root_x: Artboard X offset for root-relative coordinate calculation (default: 0).
        root_y: Artboard Y offset for root-relative coordinate calculation (default: 0).
        stage_a_candidates: Optional list of Stage A candidate dicts for Method column.

    Returns:
        str: Markdown table string.
    """
    if stage_a_candidates:
        header = '| # | ID | Name | Type | X | Y | Col | W x H | Leaf? | ChildTypes | Flags | Method | Text |'
        separator = '|---|-----|------|------|---|---|-----|-------|-------|------------|-------|--------|------|'
    else:
        header = '| # | ID | Name | Type | X | Y | Col | W x H | Leaf? | ChildTypes | Flags | Text |'
        separator = '|---|-----|------|------|---|---|-----|-------|-------|------------|-------|------|'
    rows = [header, separator]

    # Pre-compute column classification (Issue 256)
    # Detect two-column layout by X-coordinate clustering
    x_positions = []
    x_right_edges = []
    for child in children:
        cbb = get_bbox(child)
        x_positions.append(int(cbb['x']))
        x_right_edges.append(int(cbb['x'] + cbb['w']))

    # Determine if two-column layout exists
    col_midpoint = None
    if len(x_positions) >= 2:
        x_min = min(x_positions)
        x_max = max(x_right_edges)
        x_span = x_max - x_min
        if x_span > 0:
            # Check if elements cluster into left/right groups
            mid = x_min + x_span / 2
            left_count = sum(1 for xr in x_right_edges if xr <= mid + x_span * 0.1)
            right_count = sum(1 for xp in x_positions if xp >= mid - x_span * 0.1)
            # Need elements on both sides for two-column detection
            if left_count >= 1 and right_count >= 1 and left_count + right_count > len(x_positions) * 0.3:
                col_midpoint = mid

    for i, child in enumerate(children):
        bb = get_bbox(child)
        x = int(bb['x'])
        y = int(bb['y'])
        w = int(bb['w'])
        h = int(bb['h'])
        node_type = child.get('type', '')
        name = (child.get('name', '') or '')[:35]
        node_id = child.get('id', '')
        child_nodes = filter_visible_children(child)
        is_leaf = len(child_nodes) == 0
        leaf_str = 'Y' if is_leaf else 'N'

        # Column classification (Issue 256)
        if col_midpoint is not None:
            right_edge = x + w
            if right_edge <= col_midpoint:
                col = 'L'
            elif x >= col_midpoint:
                col = 'R'
            elif w >= (max(x_right_edges) - min(x_positions)) * 0.8:
                col = 'F'  # Full-width (dividers, backgrounds)
            else:
                col = 'C'  # Center / spanning both
        else:
            col = '-'

        # Child types summary
        child_types = _compute_child_types(child_nodes)

        # Flags
        flags = _compute_flags(child, page_width, page_height, root_x=root_x, root_y=root_y)
        flags_str = ','.join(flags) if flags else '-'

        # Text preview
        text = _collect_text_preview(child)
        if not text:
            text = '-'

        if stage_a_candidates:
            method_tag = _compute_method_tag(node_id, stage_a_candidates)
            row = f'| {i+1} | {node_id} | {name} | {node_type} | {x} | {y} | {col} | {w}x{h} | {leaf_str} | {child_types} | {flags_str} | {method_tag} | {text} |'
        else:
            row = f'| {i+1} | {node_id} | {name} | {node_type} | {x} | {y} | {col} | {w}x{h} | {leaf_str} | {child_types} | {flags_str} | {text} |'
        rows.append(row)

    return '\n'.join(rows)

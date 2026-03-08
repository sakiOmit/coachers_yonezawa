"""Tree-walking grouping detection for figma-prepare Phase 2.

Contains the recursive walk_and_detect() and node protection logic.
Extracted from grouping_engine.py for modularity.
"""

from .constants import (
    FLAT_THRESHOLD,
    UNNAMED_RE,
)
from .detection import (
    detect_bg_content_layers,
    detect_consecutive_similar,
    detect_heading_content_pairs,
    detect_highlight_text,
    detect_horizontal_bar,
    detect_repeating_tuple,
    detect_table_rows,
    is_decoration_pattern,
)
from .geometry import get_bbox
from .grouping_proximity import detect_proximity_groups
from .grouping_semantic import detect_semantic_groups, detect_variant_groups
from .metadata import get_text_children_content, is_off_canvas
from .naming import to_kebab

__all__ = [
    "walk_and_detect",
]


def _is_protected_node(node):
    """Check if a node's internal structure should be protected from regrouping.

    Issue #221: Preserve designer-intentional groupings.
    Protected types:
    - GROUP with a meaningful name (designer explicitly grouped these elements)
    - COMPONENT / INSTANCE (reusable component structure must not be altered)
    """
    node_type = node.get('type', '')
    node_name = node.get('name', '')
    if node_type in ('COMPONENT', 'INSTANCE'):
        return True
    if node_type == 'GROUP' and node_name and not UNNAMED_RE.match(node_name):
        return True
    return False


def _append_with_parent(groups, parent_id, parent_name, all_candidates):
    """Stamp parent_id/parent_name on each group dict and append to all_candidates."""
    for g in groups:
        g['parent_id'] = parent_id
        g['parent_name'] = parent_name
        all_candidates.append(g)


def _run_zone_detectors(children, parent_id, parent_name, page_bb, disabled, all_candidates):
    """Run root-level zone detectors: header/footer, horizontal bar, vertical zone.

    Issue 85, 86, 184. Mutates all_candidates in place.
    """
    if 'header-footer' not in disabled:
        from .grouping_zones import detect_header_footer_groups
        _append_with_parent(detect_header_footer_groups(children, page_bb),
                            parent_id, parent_name, all_candidates)

    if 'horizontal-bar' not in disabled:
        _append_with_parent(detect_horizontal_bar(children, page_bb),
                            parent_id, parent_name, all_candidates)

    if 'zone' not in disabled:
        from .grouping_zones import detect_vertical_zone_groups
        _append_with_parent(detect_vertical_zone_groups(children, page_bb),
                            parent_id, parent_name, all_candidates)


def _run_consecutive_detectors(children, parent_id, parent_name, disabled, all_candidates):
    """Run root-level consecutive pattern and heading-content pair detectors.

    Issue 165, 166. Mutates all_candidates in place.
    """
    if 'consecutive' not in disabled:
        for cg in detect_consecutive_similar(children):
            node_ids = [children[idx].get('id', '') for idx in cg['indices']]
            if len(node_ids) >= 2:
                all_candidates.append({
                    'node_ids': node_ids,
                    'parent_id': parent_id,
                    'parent_name': parent_name,
                    'suggested_name': f"list-{to_kebab(children[cg['indices'][0]].get('name', 'item'))}",
                    'method': 'consecutive',
                    'score': 0.85,
                    'priority': 2.5,
                    'count': len(node_ids),
                    'structure_hash': cg['hash'],
                })

    if 'heading-content' not in disabled:
        for pair in detect_heading_content_pairs(children):
            h = children[pair['heading_idx']]
            c = children[pair['content_idx']]
            h_texts = get_text_children_content([h], max_items=2)
            if not h_texts:
                h_texts = get_text_children_content(h.get('children', []), max_items=2)
            slug = to_kebab(h_texts[0]) if h_texts else 'section'
            all_candidates.append({
                'node_ids': [h.get('id', ''), c.get('id', '')],
                'parent_id': parent_id,
                'parent_name': parent_name,
                'suggested_name': f'section-{slug}',
                'method': 'heading-content',
                'score': 0.7,
                'priority': 3.5,
                'count': 2,
                'structure_hash': '',
            })


def _run_structural_detectors(children, node, parent_id, parent_name, is_root, disabled, all_candidates):
    """Run bg-content, table, tuple, and highlight detectors.

    Issue 180, 181, 186, 190. Mutates all_candidates in place.
    """
    node_bb = get_bbox(node)

    # Issue 180: Background-content layer detection (non-root level)
    if not is_root and 'bg-content' not in disabled:
        _append_with_parent(detect_bg_content_layers(children, node_bb),
                            parent_id, parent_name, all_candidates)

    # Issue 181: Table row structure detection (all levels)
    if 'table' not in disabled:
        _append_with_parent(detect_table_rows(children, node_bb),
                            parent_id, parent_name, all_candidates)

    # Issue 186: Repeating tuple pattern detection (all levels)
    if 'tuple' not in disabled:
        for tg in detect_repeating_tuple(children):
            node_ids = [children[idx].get('id', '') for idx in tg['children_indices']]
            first_child = children[tg['children_indices'][0]]
            texts = get_text_children_content([first_child], max_items=1)
            if not texts:
                texts = get_text_children_content(first_child.get('children', []), max_items=1)
            slug = to_kebab(texts[0]) if texts else 'item'
            all_candidates.append({
                'node_ids': node_ids, 'parent_id': parent_id,
                'parent_name': parent_name,
                'suggested_name': f'card-list-{slug}',
                'method': 'tuple', 'score': 0.85,
                'count': len(node_ids),
                'tuple_size': tg['tuple_size'],
                'repetitions': tg['count'],
                'suggested_wrapper': 'card-container',
            })

    # Issue 190: Highlight text pattern detection (non-root level)
    if not is_root and 'highlight' not in disabled:
        for hl in detect_highlight_text(children):
            r_id = children[hl['rect_idx']].get('id', '')
            t_id = children[hl['text_idx']].get('id', '')
            text_content = hl['text_content']
            slug = to_kebab(text_content[:20]) if text_content else 'text'
            all_candidates.append({
                'node_ids': [r_id, t_id], 'parent_id': parent_id,
                'parent_name': parent_name,
                'suggested_name': f'highlight-{slug}',
                'method': 'highlight', 'score': 0.8,
                'semantic_type': 'highlight', 'count': 2,
            })


def _run_stage_a_detectors(children, parent_id, parent_name, is_root, disabled, all_candidates):
    """Run Stage A general detectors: semantic, pattern, spacing, proximity.

    Issue #222: At non-root levels with few children, only semantic runs.
    Issue 229: Respect disabled detectors. Mutates all_candidates in place.
    """
    # Import here to avoid circular imports — these are in grouping_engine.py
    from .grouping_engine import detect_pattern_groups, detect_spacing_groups

    run_all = is_root or len(children) >= FLAT_THRESHOLD
    semantic = detect_semantic_groups(children) if 'semantic' not in disabled else []
    variants = detect_variant_groups(children) if 'variant' not in disabled else []
    patterns = detect_pattern_groups(children) if run_all and 'pattern' not in disabled else []
    spacing = detect_spacing_groups(children) if run_all and 'spacing' not in disabled else []
    proximity = detect_proximity_groups(children) if run_all and 'proximity' not in disabled else []

    _append_with_parent(semantic + variants + patterns + spacing + proximity,
                        parent_id, parent_name, all_candidates)


def _recurse_children(children, is_root, all_candidates, disabled):
    """Recurse into child nodes for deeper grouping detection.

    Skips decoration patterns at non-root levels (Issue #3).
    """
    for child in children:
        # Skip: decoration patterns have no meaningful sub-structure (Issue #3 / Issue 240)
        if not is_root and is_decoration_pattern(child):
            continue
        walk_and_detect(child, all_candidates, is_root=False, disabled=disabled)


def _filter_children(node, is_root):
    """Filter visible children, excluding off-canvas at root level.

    Issue 187 (hidden filter), Issue 182 (off-canvas filter).
    Returns (children, page_bb) tuple. page_bb is only meaningful when is_root=True.
    """
    raw = node.get('children', [])
    if not raw:
        return [], None

    if is_root:
        page_bb = get_bbox(node)
        pw = page_bb['w'] if page_bb else 0
        rx = page_bb['x'] if page_bb else 0
        ry = page_bb['y'] if page_bb else 0
        children = [c for c in raw
                    if c.get('visible') != False
                    and not (pw > 0 and is_off_canvas(c, pw, root_x=rx, root_y=ry))]
        return children, page_bb

    return [c for c in raw if c.get('visible') != False], None


def walk_and_detect(node, all_candidates=None, is_root=True, disabled=None):
    """Walk tree and detect grouping candidates at each level.

    Args:
        node: Figma node to process.
        all_candidates: Accumulator list (created if None).
        is_root: Whether this is the root-level call.
        disabled: Set of detector method names to skip (Issue 229).
    """
    if all_candidates is None:
        all_candidates = []
    if disabled is None:
        disabled = set()

    if node.get('visible') == False:
        return all_candidates

    children, page_bb = _filter_children(node, is_root)
    if not children:
        return all_candidates

    # Issue #221: Protected nodes — recurse but don't detect at this level
    if not is_root and _is_protected_node(node):
        for child in children:
            walk_and_detect(child, all_candidates, is_root=False, disabled=disabled)
        return all_candidates

    parent_id = node.get('id', '')
    parent_name = node.get('name', '')

    if is_root:
        _run_zone_detectors(children, parent_id, parent_name, page_bb, disabled, all_candidates)
        _run_consecutive_detectors(children, parent_id, parent_name, disabled, all_candidates)

    _run_stage_a_detectors(children, parent_id, parent_name, is_root, disabled, all_candidates)
    _run_structural_detectors(children, node, parent_id, parent_name, is_root, disabled, all_candidates)
    _recurse_children(children, is_root, all_candidates, disabled)

    return all_candidates

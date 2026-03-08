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
from .grouping_semantic import detect_semantic_groups
from .metadata import get_text_children_content, is_off_canvas
from .naming import to_kebab


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


def walk_and_detect(node, all_candidates=None, is_root=True, disabled=None):
    """Walk tree and detect grouping candidates at each level.

    Args:
        node: Figma node to process.
        all_candidates: Accumulator list (created if None).
        is_root: Whether this is the root-level call.
        disabled: Set of detector method names to skip (Issue 229).
    """
    # Import here to avoid circular imports — these are in grouping_engine.py
    from .grouping_engine import detect_pattern_groups, detect_spacing_groups

    if all_candidates is None:
        all_candidates = []
    if disabled is None:
        disabled = set()

    # Issue 187: Skip hidden nodes entirely
    if node.get('visible') == False:
        return all_candidates

    children = node.get('children', [])
    if not children:
        return all_candidates

    # Issue 187: Filter out hidden children before detection
    # Issue 182: Filter out off-canvas children at root level
    if is_root:
        page_bb_pre = get_bbox(node)
        page_width = page_bb_pre['w'] if page_bb_pre else 0
        root_x = page_bb_pre['x'] if page_bb_pre else 0
        root_y = page_bb_pre['y'] if page_bb_pre else 0
        children = [c for c in children
                    if c.get('visible') != False
                    and not (page_width > 0 and is_off_canvas(c, page_width, root_x=root_x, root_y=root_y))]
    else:
        children = [c for c in children if c.get('visible') != False]

    if not children:
        return all_candidates

    # Issue #221: Skip grouping detection for protected nodes (but still recurse deeper)
    # If this non-root node is a designer-intentional GROUP or COMPONENT/INSTANCE,
    # don't propose regrouping its children — preserve the original structure.
    if not is_root and _is_protected_node(node):
        for child in children:
            walk_and_detect(child, all_candidates, is_root=False, disabled=disabled)
        return all_candidates

    parent_id = node.get('id', '')
    parent_name = node.get('name', '')

    # Issue 85, 86: Root-level-only detectors
    if is_root:
        page_bb = page_bb_pre  # reuse bbox computed above (Issue 198)
        # Issue 85: Header/footer detection (Issue 229: respect disabled)
        if 'header-footer' not in disabled:
            from .grouping_zones import detect_header_footer_groups
            header_footer = detect_header_footer_groups(children, page_bb)
            for g in header_footer:
                g['parent_id'] = parent_id
                g['parent_name'] = parent_name
                all_candidates.append(g)
        # Issue 184: Horizontal bar detection (before zone detection)
        if 'horizontal-bar' not in disabled:
            h_bars = detect_horizontal_bar(children, page_bb)
            for g in h_bars:
                g['parent_id'] = parent_id
                g['parent_name'] = parent_name
                all_candidates.append(g)
        # Issue 86: Vertical zone detection (mixed-type sections)
        if 'zone' not in disabled:
            from .grouping_zones import detect_vertical_zone_groups
            vertical_zones = detect_vertical_zone_groups(children, page_bb)
            for g in vertical_zones:
                g['parent_id'] = parent_id
                g['parent_name'] = parent_name
                all_candidates.append(g)

        # Issue 165: Consecutive pattern groups (root level only)
        if 'consecutive' not in disabled:
            consecutive_groups = detect_consecutive_similar(children)
            for cg in consecutive_groups:
                node_ids = [children[idx].get('id', '') for idx in cg['indices']]
                if len(node_ids) >= 2:
                    # Infer name from common structure
                    suggested_name = f"list-{to_kebab(children[cg['indices'][0]].get('name', 'item'))}"
                    all_candidates.append({
                        'node_ids': node_ids,
                        'parent_id': parent_id,
                        'parent_name': parent_name,
                        'suggested_name': suggested_name,
                        'method': 'consecutive',
                        'priority': 2.5,
                        'count': len(node_ids),
                        'structure_hash': cg['hash'],
                    })

        # Issue 166: Heading-content pairs (root level only)
        if 'heading-content' not in disabled:
            hc_pairs = detect_heading_content_pairs(children)
            for pair in hc_pairs:
                h = children[pair['heading_idx']]
                c = children[pair['content_idx']]
                h_id = h.get('id', '')
                c_id = c.get('id', '')
                # Name from heading text
                h_texts = get_text_children_content([h], max_items=2)
                if not h_texts:
                    # Try children of heading frame
                    h_texts = get_text_children_content(h.get('children', []), max_items=2)
                slug = to_kebab(h_texts[0]) if h_texts else 'section'
                all_candidates.append({
                    'node_ids': [h_id, c_id],
                    'parent_id': parent_id,
                    'parent_name': parent_name,
                    'suggested_name': f'section-{slug}',
                    'method': 'heading-content',
                    'priority': 3.5,
                    'count': 2,
                    'structure_hash': '',
                })

    # Detect at this level (all Stage A methods)
    # Issue #222: At non-root levels, only run proximity/pattern/semantic if
    # the parent has many children (flat structure needing organization).
    # Well-structured nodes with few children don't need aggressive grouping.
    # Additionally, named non-root FRAMEs with few children are considered
    # well-structured and skip all general detection methods.
    # Issue 229: Respect disabled detectors
    if is_root or len(children) >= FLAT_THRESHOLD:
        semantic = detect_semantic_groups(children) if 'semantic' not in disabled else []
        patterns = detect_pattern_groups(children) if 'pattern' not in disabled else []
        spacing = detect_spacing_groups(children) if 'spacing' not in disabled else []
        proximity = detect_proximity_groups(children) if 'proximity' not in disabled else []
    else:
        semantic = detect_semantic_groups(children) if 'semantic' not in disabled else []
        patterns = []
        spacing = []
        proximity = []

    for g in semantic + patterns + spacing + proximity:
        g['parent_id'] = parent_id
        g['parent_name'] = parent_name
        all_candidates.append(g)

    # Issue 180: Background-content layer detection (non-root level)
    if not is_root and 'bg-content' not in disabled:
        bg_content = detect_bg_content_layers(children, get_bbox(node))
        for g in bg_content:
            g['parent_id'] = parent_id
            g['parent_name'] = parent_name
            all_candidates.append(g)

    # Issue 181: Table row structure detection (all levels)
    if 'table' not in disabled:
        table_groups = detect_table_rows(children, get_bbox(node))
        for g in table_groups:
            g['parent_id'] = parent_id
            g['parent_name'] = parent_name
            all_candidates.append(g)

    # Issue 186: Repeating tuple pattern detection (all levels)
    if 'tuple' not in disabled:
        tuple_groups = detect_repeating_tuple(children)
        for tg in tuple_groups:
            node_ids = [children[idx].get('id', '') for idx in tg['children_indices']]
            # Derive name from first child's text content or fall back
            first_child = children[tg['children_indices'][0]]
            texts = get_text_children_content([first_child], max_items=1)
            if not texts:
                texts = get_text_children_content(first_child.get('children', []), max_items=1)
            slug = to_kebab(texts[0]) if texts else 'item'
            all_candidates.append({
                'node_ids': node_ids,
                'parent_id': parent_id,
                'parent_name': parent_name,
                'suggested_name': f'card-list-{slug}',
                'method': 'tuple',
                'count': len(node_ids),
                'tuple_size': tg['tuple_size'],
                'repetitions': tg['count'],
                'suggested_wrapper': 'card-container',
            })

    # Issue 190: Highlight text pattern detection (non-root level)
    if not is_root and 'highlight' not in disabled:
        highlights = detect_highlight_text(children)
        for hl in highlights:
            rect_node = children[hl['rect_idx']]
            text_node = children[hl['text_idx']]
            r_id = rect_node.get('id', '')
            t_id = text_node.get('id', '')
            text_content = hl['text_content']
            slug = to_kebab(text_content[:20]) if text_content else 'text'
            all_candidates.append({
                'node_ids': [r_id, t_id],
                'parent_id': parent_id,
                'parent_name': parent_name,
                'suggested_name': f'highlight-{slug}',
                'method': 'highlight',
                'semantic_type': 'highlight',
                'count': 2,
            })

    # Recurse (skip decoration patterns — Issue #3)
    for child in children:
        if not is_root and is_decoration_pattern(child):
            continue  # No value in grouping elements inside a decoration frame
        walk_and_detect(child, all_candidates, is_root=False, disabled=disabled)

    return all_candidates

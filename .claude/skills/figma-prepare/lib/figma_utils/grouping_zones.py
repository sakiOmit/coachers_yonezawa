"""Header/footer and vertical zone grouping detection for figma-prepare Phase 2.

Contains zone-based grouping logic for page-level structure detection.
Extracted from grouping_engine.py for modularity.
"""

from .constants import (
    FOOTER_ZONE_HEIGHT,
    FOOTER_ZONE_MARGIN,
    HEADER_LOGO_MAX_HEIGHT,
    HEADER_LOGO_MAX_WIDTH,
    HEADER_MAX_ELEMENT_HEIGHT,
    HEADER_NAV_MIN_TEXTS,
    HEADER_TEXT_MAX_WIDTH,
    HEADER_ZONE_HEIGHT,
    HERO_ZONE_DISTANCE,
    LARGE_BG_WIDTH_RATIO,
    SECTION_ROOT_WIDTH,
    ZONE_OVERLAP_ITEM,
    ZONE_OVERLAP_ZONE,
)
from .geometry import get_bbox
from .grouping_semantic import is_card_like, is_grid_like, is_navigation_like
from .metadata import get_text_children_content


def detect_header_footer_groups(root_children, page_bb):
    """Detect header/footer grouping at the page root level (Issue 85).

    Identifies flat elements near the top/bottom of the page that should be
    grouped into HEADER/FOOTER wrappers. Works by:
    1. Finding elements in the header zone (top 120px of page)
    2. Checking if they contain nav-like TEXT elements + logo (VECTOR/IMAGE)
    3. Finding elements in the footer zone (bottom 250px of page)
    4. Only suggests grouping if 2+ elements are found in a zone

    Only runs on root-level children (not recursive).
    """
    if len(root_children) < 3:
        return []

    result = []
    page_top = page_bb['y']
    page_bottom = page_bb['y'] + page_bb['h']
    header_zone_max = page_top + HEADER_ZONE_HEIGHT  # Issue 123: use named constant
    footer_zone_min = page_bottom - FOOTER_ZONE_HEIGHT  # Issue 123: use named constant

    # Classify elements by zone
    header_candidates = []
    footer_candidates = []
    for c in root_children:
        bb = get_bbox(c)
        el_top = bb['y']
        el_bottom = bb['y'] + bb['h']

        # Skip elements that are already named HEADER/FOOTER (already grouped)
        name_upper = c.get('name', '').upper()
        if name_upper in ('HEADER', 'FOOTER', 'NAV', 'NAVIGATION'):
            continue

        # Header zone: element starts within header zone
        if el_top < header_zone_max and bb['h'] < HEADER_MAX_ELEMENT_HEIGHT:
            header_candidates.append(c)

        # Footer zone: element bottom is near or past footer zone
        # Footer zone: element bottom is in footer zone, and element top is
        # at most FOOTER_ZONE_MARGIN above the zone start (catches elements
        # that span slightly above the footer zone boundary)
        if el_bottom > footer_zone_min and el_top > footer_zone_min - FOOTER_ZONE_MARGIN:
            footer_candidates.append(c)

    # Header grouping: need 2+ elements, at least one nav-like TEXT or VECTOR/IMAGE
    if len(header_candidates) >= 2:
        has_nav_text = False
        has_logo = False
        nav_texts = []
        for c in header_candidates:
            t = c.get('type', '')
            if t == 'TEXT':
                bb = get_bbox(c)
                if bb['w'] < HEADER_TEXT_MAX_WIDTH:  # Issue 134: text-like width
                    nav_texts.append(c)
            elif t in ('VECTOR', 'IMAGE', 'RECTANGLE'):
                bb = get_bbox(c)
                if bb['w'] < HEADER_LOGO_MAX_WIDTH and bb['h'] < HEADER_LOGO_MAX_HEIGHT:  # Issue 134: logo-like size
                    has_logo = True
            elif t in ('FRAME', 'GROUP', 'INSTANCE', 'COMPONENT'):
                # Check if it contains nav-like elements
                sub_children = [sc for sc in c.get('children', []) if sc.get('visible') != False]
                sub_texts = [sc for sc in sub_children if sc.get('type') == 'TEXT']
                if len(sub_texts) >= HEADER_NAV_MIN_TEXTS:  # Issue 134
                    has_nav_text = True
                # Could be a logo wrapper
                if len(sub_children) <= 2:
                    has_logo = True

        if len(nav_texts) >= HEADER_NAV_MIN_TEXTS:  # Issue 134
            has_nav_text = True

        # Require either nav texts or logo for header detection
        if has_nav_text or (has_logo and len(header_candidates) >= 2):
            result.append({
                'method': 'semantic',
                'semantic_type': 'header',
                'node_ids': [c.get('id', '') for c in header_candidates],
                'node_names': [c.get('name', '') for c in header_candidates],
                'count': len(header_candidates),
                'suggested_name': 'header',
                'suggested_wrapper': 'header',
            })

    # Footer grouping: need 2+ elements
    if len(footer_candidates) >= 2:
        result.append({
            'method': 'semantic',
            'semantic_type': 'footer',
            'node_ids': [c.get('id', '') for c in footer_candidates],
            'node_names': [c.get('name', '') for c in footer_candidates],
            'count': len(footer_candidates),
            'suggested_name': 'footer',
            'suggested_wrapper': 'footer',
        })

    return result


def infer_zone_semantic_name(zone_nodes, page_bb, zone_counters):
    """Infer a semantic name for a vertical zone based on child structure (Issue 91).

    Analyzes the types, sizes, and content of zone members to classify:
    - section-hero: Large background (IMAGE/RECTANGLE) + prominent text at page top
    - section-cards-N: 3+ card-like children
    - section-nav-N: Navigation-like horizontal text elements
    - section-grid-N: Grid layout of similar-sized elements
    - section-content-N: Default fallback

    Args:
        zone_nodes: List of nodes in this zone.
        page_bb: Page bounding box for position-based heuristics.
        zone_counters: Dict tracking how many of each type have been seen (mutated).

    Returns:
        str: Semantic section name.
    """
    # Collect zone-level stats
    bboxes = [get_bbox(n) for n in zone_nodes]
    zone_top = min(b['y'] for b in bboxes)
    page_top = page_bb['y']

    # Hero detection: near page top + has large background + text
    is_near_top = abs(zone_top - page_top) < HERO_ZONE_DISTANCE  # Issue 135
    has_large_bg = False
    has_text = False
    for n, bb in zip(zone_nodes, bboxes):
        t = n.get('type', '')
        # Large background: RECTANGLE/IMAGE covering >LARGE_BG_WIDTH_RATIO of page width
        # Issue 183: Also detect oversized elements (width > SECTION_ROOT_WIDTH)
        if t in ('RECTANGLE', 'IMAGE') and (bb['w'] > page_bb['w'] * LARGE_BG_WIDTH_RATIO or bb['w'] > SECTION_ROOT_WIDTH):
            has_large_bg = True
        if t == 'TEXT':
            has_text = True
        # Check children of FRAME/GROUP for text
        if t in ('FRAME', 'GROUP', 'INSTANCE', 'COMPONENT'):
            child_texts = get_text_children_content([c for c in n.get('children', []) if c.get('visible') != False], max_items=3)
            if child_texts:
                has_text = True
            # Nested large background
            for child in [c for c in n.get('children', []) if c.get('visible') != False]:
                ct = child.get('type', '')
                cbb = get_bbox(child)
                if ct in ('RECTANGLE', 'IMAGE') and (cbb['w'] > page_bb['w'] * LARGE_BG_WIDTH_RATIO or cbb['w'] > SECTION_ROOT_WIDTH):  # Issue 183
                    has_large_bg = True

    if is_near_top and has_large_bg and has_text:
        zone_counters['hero'] = zone_counters.get('hero', 0) + 1
        return f"section-hero-{zone_counters['hero']}"

    # Card list detection: 3+ card-like elements
    cards = [n for n in zone_nodes if is_card_like(n)]
    if len(cards) >= 3:
        zone_counters['cards'] = zone_counters.get('cards', 0) + 1
        return f"section-cards-{zone_counters['cards']}"

    # Grid detection
    if len(zone_nodes) >= 4 and is_grid_like(zone_nodes):
        zone_counters['grid'] = zone_counters.get('grid', 0) + 1
        return f"section-grid-{zone_counters['grid']}"

    # Navigation detection
    if is_navigation_like(zone_nodes):
        zone_counters['nav'] = zone_counters.get('nav', 0) + 1
        return f"section-nav-{zone_counters['nav']}"

    # Fallback: content with counter
    zone_counters['content'] = zone_counters.get('content', 0) + 1
    return f"section-content-{zone_counters['content']}"


def detect_vertical_zone_groups(root_children, page_bb):
    """Detect groups of elements occupying the same vertical zone (Issue 86).

    Groups elements whose Y ranges overlap significantly, suggesting they
    belong to the same visual section. Works by:
    1. For each element, compute its Y range [top, bottom]
    2. Greedily merge elements whose Y ranges overlap by >= 50%
    3. Only report groups of 2+ elements that are not already detected
    4. Infer semantic name from child structure (Issue 91)

    Skip elements already named with semantic names (HEADER, FOOTER, CTA, etc.)
    Only runs on root-level children.
    """
    if len(root_children) < 4:
        return []

    # Build list of (index, y_top, y_bottom, node)
    items = []
    skip_names = {'HEADER', 'FOOTER', 'NAV', 'NAVIGATION'}
    for i, c in enumerate(root_children):
        name_upper = c.get('name', '').upper()
        if name_upper in skip_names:
            continue
        bb = get_bbox(c)
        if bb['h'] <= 0:
            continue
        items.append((i, bb['y'], bb['y'] + bb['h'], c))

    if len(items) < 2:
        return []

    # Sort by Y top
    items.sort(key=lambda x: x[1])

    # Greedy zone merging
    zones = []  # list of [zone_top, zone_bottom, [nodes]]
    for idx, y_top, y_bot, node in items:
        merged = False
        for z in zones:
            z_top, z_bot = z[0], z[1]
            # Compute overlap
            overlap_top = max(y_top, z_top)
            overlap_bot = min(y_bot, z_bot)
            overlap = max(0, overlap_bot - overlap_top)
            item_height = y_bot - y_top
            # Issue 121: Merge if element overlaps >= ZONE_OVERLAP_ITEM with zone,
            # or zone overlaps >= ZONE_OVERLAP_ZONE with element.
            # Asymmetric thresholds: items need strong overlap (50%), but zones
            # can expand with weaker overlap (30%) to absorb adjacent small elements.
            if item_height > 0 and (overlap / item_height >= ZONE_OVERLAP_ITEM or overlap / (z_bot - z_top) >= ZONE_OVERLAP_ZONE):
                z[0] = min(z_top, y_top)
                z[1] = max(z_bot, y_bot)
                z[2].append(node)
                merged = True
                break
        if not merged:
            zones.append([y_top, y_bot, [node]])

    # Filter: only zones with 2+ elements that aren't already a single frame
    result = []
    zone_counters = {}  # Track semantic name counters across zones (Issue 91)
    for z_top, z_bot, nodes in zones:
        if len(nodes) < 2:
            continue
        semantic_name = infer_zone_semantic_name(nodes, page_bb, zone_counters)
        result.append({
            'method': 'zone',
            'semantic_type': 'vertical-zone',
            'node_ids': [n.get('id', '') for n in nodes],
            'node_names': [n.get('name', '') for n in nodes],
            'count': len(nodes),
            'suggested_name': semantic_name,
            'suggested_wrapper': 'section',
        })

    return result

#!/usr/bin/env bash
# Phase 2: Detect Grouping Candidates
#
# Usage: bash detect-grouping-candidates.sh <metadata.json> [--output grouping-plan.yaml] [--skip-root] [--disable-detectors bg-content,table,highlight]
# Input: Figma get_metadata output (JSON)
# Output: JSON/YAML with grouping candidates
# Exit: 0=success, 1=error

set -euo pipefail

if [[ $# -lt 1 ]] || [[ ! -f "$1" ]]; then
  echo '{"error": "Usage: detect-grouping-candidates.sh <metadata.json> [--output file.yaml] [--skip-root] [--disable-detectors list]"}' >&2
  exit 1
fi

INPUT_FILE="$1"

OUTPUT_FILE=""
SKIP_ROOT=""
DISABLE_DETECTORS=""
# Parse optional flags (order-independent)
shift  # consume the positional metadata.json argument
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      OUTPUT_FILE="${2:-}"
      shift 2
      ;;
    --skip-root)
      SKIP_ROOT="1"
      shift
      ;;
    --disable-detectors)
      DISABLE_DETECTORS="${2:-}"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 -c "
import json, sys, os
from collections import defaultdict
sys.setrecursionlimit(3000)  # Guard against deeply nested Figma files (Issue 48)
sys.path.insert(0, os.path.join(sys.argv[1], 'lib'))
from figma_utils import (resolve_absolute_coords, get_bbox, get_root_node, load_metadata, UNNAMED_RE, yaml_str,
    compute_grouping_score, structure_hash, structure_similarity, detect_regular_spacing,
    get_text_children_content, to_kebab, ROW_TOLERANCE, SECTION_ROOT_WIDTH,
    detect_consecutive_similar, detect_heading_content_pairs,
    find_absorbable_elements, is_heading_like, is_off_canvas,
    detect_bg_content_layers, BG_WIDTH_RATIO,
    detect_table_rows, TABLE_MIN_ROWS,
    detect_repeating_tuple, TUPLE_PATTERN_MIN, TUPLE_MAX_SIZE,
    detect_highlight_text, HIGHLIGHT_OVERLAP_RATIO,
    detect_horizontal_bar, HORIZONTAL_BAR_MAX_HEIGHT, HORIZONTAL_BAR_MIN_ELEMENTS,
    CONSECUTIVE_PATTERN_MIN, LOOSE_ELEMENT_MAX_HEIGHT, LOOSE_ABSORPTION_DISTANCE,
    OFF_CANVAS_MARGIN, SPATIAL_SPLIT_MIN_NON_LEAF,
    PROXIMITY_GAP, REPEATED_PATTERN_MIN, JACCARD_THRESHOLD, SPATIAL_GAP_THRESHOLD,
    HEADER_ZONE_HEIGHT, FOOTER_ZONE_HEIGHT, ZONE_OVERLAP_ITEM, ZONE_OVERLAP_ZONE,
    HEADER_MAX_ELEMENT_HEIGHT, FOOTER_ZONE_MARGIN,
    HEADER_TEXT_MAX_WIDTH, HEADER_LOGO_MAX_WIDTH, HEADER_LOGO_MAX_HEIGHT, HEADER_NAV_MIN_TEXTS,
    HERO_ZONE_DISTANCE, LARGE_BG_WIDTH_RATIO,
    GRID_SIZE_SIMILARITY, FLAT_THRESHOLD, STAGE_A_ONLY_DETECTORS,
    is_decoration_pattern, deduplicate_candidates, METHOD_PRIORITY)

class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py:
            return
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1

    def groups(self):
        groups = defaultdict(list)
        for i in range(len(self.parent)):
            groups[self.find(i)].append(i)
        return {k: v for k, v in groups.items() if len(v) >= 2}

def detect_proximity_groups(children):
    \"\"\"Detect groups of nearby elements using Union-Find with scoring.\"\"\"
    n = len(children)
    if n < 2:
        return []

    bboxes = [get_bbox(c) for c in children]
    uf = UnionFind(n)
    for i in range(n):
        for j in range(i + 1, n):
            score = compute_grouping_score(bboxes[i], bboxes[j], PROXIMITY_GAP)
            if score > 0.5:
                uf.union(i, j)

    result = []
    # Issue 127: Use sequential counter instead of UF internal root index
    for group_idx, (root, indices) in enumerate(uf.groups().items(), 1):
        if len(indices) >= 2:
            group_nodes = [children[i] for i in indices]
            result.append({
                'method': 'proximity',
                'node_ids': [n.get('id', '') for n in group_nodes],
                'node_names': [n.get('name', '') for n in group_nodes],
                'count': len(indices),
                'suggested_name': f'group-{group_idx}',
            })
    return result

def detect_pattern_groups(children):
    \"\"\"Detect repeated patterns using fuzzy structure hash matching.\"\"\"
    hashes = [(structure_hash(c), c) for c in children]

    # Greedy clustering by Jaccard similarity
    clusters = []  # list of (representative_hash, [nodes])
    for h, child in hashes:
        matched = False
        for cluster in clusters:
            if structure_similarity(cluster[0], h) >= JACCARD_THRESHOLD:
                cluster[1].append(child)
                matched = True
                break
        if not matched:
            clusters.append((h, [child]))

    result = []
    for rep_hash, nodes in clusters:
        if len(nodes) >= REPEATED_PATTERN_MIN:
            # Issue 87: For leaf nodes (no children), split by spatial proximity
            # to avoid grouping distant TEXT elements (e.g. nav labels + content text)
            sub_groups = _split_by_spatial_gap(nodes)
            for sg in sub_groups:
                if len(sg) < REPEATED_PATTERN_MIN:
                    continue
                node_hashes = set(structure_hash(n) for n in sg)
                is_fuzzy = len(node_hashes) > 1
                result.append({
                    'method': 'pattern',
                    'structure_hash': rep_hash,
                    'node_ids': [n.get('id', '') for n in sg],
                    'node_names': [n.get('name', '') for n in sg],
                    'count': len(sg),
                    'suggested_name': 'list-items',
                    'suggested_wrapper': 'list-container',
                    'fuzzy_match': is_fuzzy,
                })
    return result

def _split_by_spatial_gap(nodes, gap_threshold=SPATIAL_GAP_THRESHOLD):
    \"\"\"Split a group of nodes into sub-groups by large spatial gaps (Issue 87, 88).

    Sorts by primary axis (Y for vertical spread, X for horizontal) and
    splits where consecutive gap exceeds threshold.

    For leaf nodes: always attempt splitting (Issue 87).
    For non-leaf nodes: only split if group is large (6+) to catch
    multi-section card grids (Issue 88).
    \"\"\"
    if len(nodes) <= REPEATED_PATTERN_MIN:
        return [nodes]
    all_leaf = all(len(n.get('children', [])) == 0 for n in nodes)
    # Issue 88/206: Non-leaf elements are often structurally cohesive (e.g. a
    # few card frames belonging to one section). With 5 or fewer non-leaf nodes,
    # splitting risks breaking a single logical group. At 6+ nodes, different
    # sections' card groups may have been merged, so spatial-gap splitting
    # becomes worthwhile to separate them.
    if not all_leaf and len(nodes) < SPATIAL_SPLIT_MIN_NON_LEAF:
        return [nodes]

    bboxes = [get_bbox(n) for n in nodes]
    # Determine primary axis for splitting
    # For grid-like layouts (multiple rows of items), use Y to split by rows
    xs = [b['x'] for b in bboxes]
    ys = [b['y'] for b in bboxes]

    # Detect rows by Y coordinate (Issue 88: grid-aware splitting)
    # Issue 131: Use shared ROW_TOLERANCE constant
    y_rows = set(round(y / ROW_TOLERANCE) for y in ys)
    is_grid = len(y_rows) >= 2  # multiple Y rows → grid layout

    if is_grid:
        # Grid: sort by Y (row), then X within row → split by row gaps
        sorted_pairs = sorted(zip(bboxes, nodes), key=lambda p: (round(p[0]['y'] / ROW_TOLERANCE), p[0]['x']))
        def gap_fn(a, b):
            # Only count gap when moving to a new row
            if round(a['y'] / ROW_TOLERANCE) == round(b['y'] / ROW_TOLERANCE):
                return 0  # same row
            return b['y'] - (a['y'] + a['h'])
    else:
        x_range = max(xs) - min(xs) if xs else 0
        y_range = max(ys) - min(ys) if ys else 0
        if y_range >= x_range:
            sorted_pairs = sorted(zip(bboxes, nodes), key=lambda p: p[0]['y'])
            def gap_fn(a, b): return b['y'] - (a['y'] + a['h'])
        else:
            sorted_pairs = sorted(zip(bboxes, nodes), key=lambda p: p[0]['x'])
            def gap_fn(a, b): return b['x'] - (a['x'] + a['w'])

    groups = [[sorted_pairs[0][1]]]
    for i in range(1, len(sorted_pairs)):
        g = gap_fn(sorted_pairs[i-1][0], sorted_pairs[i][0])
        if g > gap_threshold:
            groups.append([])
        groups[-1].append(sorted_pairs[i][1])
    return groups

def detect_spacing_groups(children):
    \"\"\"Detect groups of regularly-spaced elements.\"\"\"
    if len(children) < 3:
        return []

    bboxes = [get_bbox(c) for c in children]
    if not detect_regular_spacing(bboxes):
        return []

    return [{
        'method': 'spacing',
        'node_ids': [c.get('id', '') for c in children],
        'node_names': [c.get('name', '') for c in children],
        'count': len(children),
        'suggested_name': 'list-regular',
        'suggested_wrapper': 'list-container',
    }]

def is_card_like(node):
    \"\"\"Detect card-like structure: FRAME/COMPONENT/INSTANCE with 2-6 children including IMAGE+TEXT.\"\"\"
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
    \"\"\"Detect navigation-like pattern: 4+ horizontal text-sized elements.\"\"\"
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
    \"\"\"Detect grid-like pattern: 2+ rows x 2+ columns of similar-sized elements.\"\"\"
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
    \"\"\"Structural semantic detection (fills-independent, Issue 29/30 safe).\"\"\"
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

def detect_header_footer_groups(root_children, page_bb):
    \"\"\"Detect header/footer grouping at the page root level (Issue 85).

    Identifies flat elements near the top/bottom of the page that should be
    grouped into HEADER/FOOTER wrappers. Works by:
    1. Finding elements in the header zone (top 120px of page)
    2. Checking if they contain nav-like TEXT elements + logo (VECTOR/IMAGE)
    3. Finding elements in the footer zone (bottom 250px of page)
    4. Only suggests grouping if 2+ elements are found in a zone

    Only runs on root-level children (not recursive).
    \"\"\"
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
    \"\"\"Infer a semantic name for a vertical zone based on child structure (Issue 91).

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
    \"\"\"
    # Collect zone-level stats
    types = [n.get('type', '') for n in zone_nodes]
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
        return f\"section-hero-{zone_counters['hero']}\"

    # Card list detection: 3+ card-like elements
    cards = [n for n in zone_nodes if is_card_like(n)]
    if len(cards) >= 3:
        zone_counters['cards'] = zone_counters.get('cards', 0) + 1
        return f\"section-cards-{zone_counters['cards']}\"

    # Grid detection
    if len(zone_nodes) >= 4 and is_grid_like(zone_nodes):
        zone_counters['grid'] = zone_counters.get('grid', 0) + 1
        return f\"section-grid-{zone_counters['grid']}\"

    # Navigation detection
    if is_navigation_like(zone_nodes):
        zone_counters['nav'] = zone_counters.get('nav', 0) + 1
        return f\"section-nav-{zone_counters['nav']}\"

    # Fallback: content with counter
    zone_counters['content'] = zone_counters.get('content', 0) + 1
    return f\"section-content-{zone_counters['content']}\"

def detect_vertical_zone_groups(root_children, page_bb):
    \"\"\"Detect groups of elements occupying the same vertical zone (Issue 86).

    Groups elements whose Y ranges overlap significantly, suggesting they
    belong to the same visual section. Works by:
    1. For each element, compute its Y range [top, bottom]
    2. Greedily merge elements whose Y ranges overlap by >= 50%
    3. Only report groups of 2+ elements that are not already detected
    4. Infer semantic name from child structure (Issue 91)

    Skip elements already named with semantic names (HEADER, FOOTER, CTA, etc.)
    Only runs on root-level children.
    \"\"\"
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
    zones = []  # list of (zone_top, zone_bottom, [nodes])
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

def _is_protected_node(node):
    \"\"\"Check if a node's internal structure should be protected from regrouping.

    Issue #221: Preserve designer-intentional groupings.
    Protected types:
    - GROUP with a meaningful name (designer explicitly grouped these elements)
    - COMPONENT / INSTANCE (reusable component structure must not be altered)
    \"\"\"
    node_type = node.get('type', '')
    node_name = node.get('name', '')
    if node_type in ('COMPONENT', 'INSTANCE'):
        return True
    if node_type == 'GROUP' and node_name and not UNNAMED_RE.match(node_name):
        return True
    return False

def walk_and_detect(node, all_candidates=None, is_root=True, disabled=None):
    \"\"\"Walk tree and detect grouping candidates at each level.

    Args:
        node: Figma node to process.
        all_candidates: Accumulator list (created if None).
        is_root: Whether this is the root-level call.
        disabled: Set of detector method names to skip (Issue 229).
    \"\"\"
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
                    suggested_name = f\"list-{to_kebab(children[cg['indices'][0]].get('name', 'item'))}\"
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

# deduplicate_candidates and METHOD_PRIORITY imported from figma_utils (Issue 236)

try:
    # Issue 229: Parse --disable-detectors flag
    DISABLE_DETECTORS = sys.argv[5] if len(sys.argv) > 5 else ''
    disabled = set(d.strip() for d in DISABLE_DETECTORS.split(',') if d.strip()) if DISABLE_DETECTORS else set()

    # Validate detector names against known methods
    ALL_DETECTOR_METHODS = {'proximity', 'pattern', 'spacing', 'semantic', 'zone', 'tuple',
                             'consecutive', 'heading-content', 'highlight', 'bg-content',
                             'table', 'horizontal-bar', 'header-footer'}
    unknown = disabled - ALL_DETECTOR_METHODS
    if unknown:
        print(json.dumps({'warning': f'Unknown detector names ignored: {sorted(unknown)}'}), file=sys.stderr)
        disabled = disabled & ALL_DETECTOR_METHODS

    # Guard Stage A-only detectors from being disabled
    forced_a = disabled & STAGE_A_ONLY_DETECTORS
    if forced_a:
        print(json.dumps({'warning': f'Stage A-only detectors cannot be disabled: {sorted(forced_a)}. Ignoring.'}), file=sys.stderr)
        disabled = disabled - STAGE_A_ONLY_DETECTORS

    data = load_metadata(sys.argv[2])
    root = get_root_node(data)
    resolve_absolute_coords(root)
    candidates = walk_and_detect(root, disabled=disabled)
    candidates = deduplicate_candidates(candidates, root_id=root.get('id', ''))

    # Issue 167: Absorb loose elements into nearest existing group (post-dedup)
    root_children = root.get('children', [])
    if root_children and candidates:
        # Build set of indices already in root-level groups
        root_id_str = root.get('id', '')
        child_id_to_idx = {ch.get('id', ''): idx for idx, ch in enumerate(root_children)}
        grouped_indices = set()
        root_candidates = [c for c in candidates if c.get('parent_id') == root_id_str]
        for cand in root_candidates:
            for nid in cand.get('node_ids', []):
                if nid in child_id_to_idx:
                    grouped_indices.add(child_id_to_idx[nid])

        absorptions = find_absorbable_elements(root_children, grouped_indices, candidate_groups=root_candidates)
        for ab in absorptions:
            elem = root_children[ab['element_idx']]
            elem_id = elem.get('id', '')
            # Find which candidate contains the target group member
            target_child = root_children[ab['target_group_idx']]
            target_id = target_child.get('id', '')
            for cand in root_candidates:
                if target_id in cand.get('node_ids', []):
                    cand['node_ids'].append(elem_id)
                    cand['count'] = len(cand['node_ids'])
                    break

    output_file = sys.argv[3] if len(sys.argv) > 3 else ''
    skip_root = sys.argv[4] if len(sys.argv) > 4 else ''

    # Issue 178: Filter out root-level candidates when --skip-root is set
    root_skipped = 0
    if skip_root:
        root_name = root.get('name', '')
        before_count = len(candidates)
        candidates = [c for c in candidates if c.get('parent_name', '') != root_name]
        root_skipped = before_count - len(candidates)

    if output_file:
        with open(output_file, 'w') as f:
            f.write('# Figma Grouping Plan\\n')
            f.write(f'# Total candidates: {len(candidates)}\\n')
            if root_skipped:
                f.write(f'# Root-level candidates skipped: {root_skipped}\\n')
            f.write('# Generated by /figma-prepare Phase 2\\n')
            f.write('# Review before applying with --apply\\n\\n')
            f.write('candidates:\\n')
            for i, c in enumerate(candidates):
                f.write(f'  - index: {i}\\n')
                f.write(f'    method: {yaml_str(c[\"method\"])}\\n')
                f.write(f'    parent: {yaml_str(c.get(\"parent_name\", \"\"))}\\n')
                if 'node_ids' in c:
                    f.write(f'    node_ids: {json.dumps(c[\"node_ids\"])}\\n')
                    f.write(f'    count: {c[\"count\"]}\\n')
                if 'suggested_name' in c:
                    f.write(f'    suggested_name: {yaml_str(c[\"suggested_name\"])}\\n')
                if 'structure_hash' in c:
                    f.write(f'    structure_hash: {yaml_str(c[\"structure_hash\"])}\\n')
                if 'suggested_wrapper' in c:
                    f.write(f'    suggested_wrapper: {yaml_str(c[\"suggested_wrapper\"])}\\n')
                if c.get('fuzzy_match'):
                    f.write(f'    fuzzy_match: true\\n')
                if 'semantic_type' in c:
                    f.write(f'    semantic_type: {yaml_str(c[\"semantic_type\"])}\\n')
                if 'bg_node_ids' in c:
                    f.write(f'    bg_node_ids: {json.dumps(c[\"bg_node_ids\"])}\\n')
                if 'row_count' in c:
                    f.write(f'    row_count: {c[\"row_count\"]}\\n')
                if 'tuple_size' in c:
                    f.write(f'    tuple_size: {c[\"tuple_size\"]}\\n')
                if 'repetitions' in c:
                    f.write(f'    repetitions: {c[\"repetitions\"]}\\n')
        result = {
            'total': len(candidates),
            'output': output_file,
            'status': 'dry-run'
        }
        if root_skipped:
            result['root_skipped'] = root_skipped
        if disabled:
            result['disabled_detectors'] = sorted(disabled)
        print(json.dumps(result, indent=2))
    else:
        result = {
            'total': len(candidates),
            'candidates': candidates,
            'status': 'dry-run'
        }
        if root_skipped:
            result['root_skipped'] = root_skipped
        if disabled:
            result['disabled_detectors'] = sorted(disabled)
        print(json.dumps(result, indent=2, ensure_ascii=False))

except Exception as e:
    print(json.dumps({'error': str(e)}), file=sys.stderr)
    sys.exit(1)
" "${SCRIPT_DIR}/.." "$INPUT_FILE" "$OUTPUT_FILE" "$SKIP_ROOT" "$DISABLE_DETECTORS"

"""Shared utilities for figma-prepare scripts.

Common functions extracted to avoid duplication across
analyze-structure, detect-grouping-candidates, generate-rename-map,
infer-autolayout, prepare-sectioning-context, and enrich-metadata scripts.

Issue 24: resolve_absolute_coords was duplicated in 5 scripts.
Issue 52: snap() extracted from infer-autolayout.sh.
Issue 53: is_section_root() extracted from analyze-structure.sh.
"""

import json
import re
import statistics
from collections import Counter

# --- Constants ---

GRID_SNAP = 4  # px — gap/padding snap unit (figma-prepare.md)
SECTION_ROOT_WIDTH = 1440  # Figma page-level frame width
ROW_TOLERANCE = 20  # px — Y-coordinate grouping tolerance for WRAP/grid row detection (Issue 131)
CV_THRESHOLD = 0.25  # Coefficient of variation threshold for regular spacing detection (Issue 138)
FLAT_THRESHOLD = 15  # children — flat structure detection threshold (Issue 140)
DEEP_NESTING_THRESHOLD = 6  # levels — deep nesting detection threshold (Issue 140)


def yaml_str(value):
    """Safely encode a string for YAML double-quoted output.

    Uses json.dumps which properly escapes double quotes, backslashes,
    and other special characters. Output includes surrounding quotes.
    """
    return json.dumps(str(value), ensure_ascii=False)


UNNAMED_RE = re.compile(
    r'^(Rectangle|Ellipse|Line|Vector|Frame|Group|Component|Instance|Text|Polygon|Star|Image)\s*\d*$',
    re.IGNORECASE
)


def resolve_absolute_coords(node, parent_x=0, parent_y=0):
    """Convert parent-relative coordinates to absolute coordinates.

    get_metadata returns parent-relative x/y in absoluteBoundingBox.
    This function accumulates parent offsets to compute true absolute coords.

    Issue 67: Mutates in-place. A marker '_abs_resolved' prevents
    double-call from corrupting coordinates.
    """
    if node.get('_abs_resolved'):
        return
    bbox = node.get('absoluteBoundingBox') or {}
    abs_x = parent_x + bbox.get('x', 0)
    abs_y = parent_y + bbox.get('y', 0)
    bbox['x'] = abs_x
    bbox['y'] = abs_y
    node['absoluteBoundingBox'] = bbox
    node['_abs_resolved'] = True
    for child in node.get('children', []):
        resolve_absolute_coords(child, abs_x, abs_y)


def get_bbox(node):
    """Get bounding box from node.

    Returns dict with short keys: x, y, w, h.
    """
    bbox = node.get('absoluteBoundingBox') or {}
    return {
        'x': bbox.get('x', 0),
        'y': bbox.get('y', 0),
        'w': bbox.get('width', 0),
        'h': bbox.get('height', 0),
    }


def get_root_node(data):
    """Extract root node from various data formats."""
    if 'document' in data:
        return data['document']
    elif 'node' in data:
        return data['node']
    return data


def is_unnamed(name):
    """Check if a node name matches unnamed (auto-generated) pattern."""
    return bool(UNNAMED_RE.match(name))


def get_text_children_content(children, max_items=None, filter_unnamed=False):
    """Extract text content from TEXT children.

    Prefers enriched 'characters' field over 'name' (Issue 38).

    Args:
        children: List of child nodes.
        max_items: If set, limit results to this many items.
        filter_unnamed: If True, skip children whose content matches UNNAMED_RE.

    Issue 49: Unified from generate-rename-map.sh get_text_children_content
    and prepare-sectioning-context.sh get_text_children_preview.
    """
    texts = []
    for c in children:
        if c.get('type') == 'TEXT':
            content = c.get('characters', '') or c.get('name', '')
            if not content:
                continue
            # Issue 62: filter_unnamed skips nodes where the *resolved content*
            # (characters or name) matches an auto-generated pattern, but only
            # when characters is absent (i.e., we fell back to name).
            # If characters is present, the text is real content even if the
            # node name is auto-generated (e.g., name="Text 2", characters="お問い合わせ").
            if filter_unnamed and not c.get('characters', '') and UNNAMED_RE.match(content):
                continue
            texts.append(content)
    if max_items is not None:
        return texts[:max_items]
    return texts


def snap(value, grid=GRID_SNAP):
    """Snap a numeric value to the nearest grid multiple.

    Issue 52: Extracted from infer-autolayout.sh to share with other scripts.

    Args:
        value: Numeric value to snap.
        grid: Grid size (default: GRID_SNAP = 4px).

    Returns:
        int: Snapped value.
    """
    if grid <= 0:
        return round(value)
    return round(value / grid) * grid


def is_section_root(node):
    """Detect section-level frames (width ~1440, direct children of page).

    Issue 53: Extracted from analyze-structure.sh to share with other scripts.

    Args:
        node: Figma node dict.

    Returns:
        bool: True if node is a section root frame.
    """
    bbox = node.get('absoluteBoundingBox') or {}
    width = bbox.get('width', 0)
    # Issue 116: Include COMPONENT/INSTANCE/SECTION types as section roots
    # (consistent with Issue 69/72 type extensions in other scripts)
    return node.get('type') in ('FRAME', 'COMPONENT', 'INSTANCE', 'SECTION') and abs(width - SECTION_ROOT_WIDTH) < 10


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
    children = node.get('children', [])
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
    gaps = [g for g in gaps if g > 0]
    if len(gaps) < 2:
        return False

    mean_gap = statistics.mean(gaps)
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
    if row_tolerance is None:
        row_tolerance = ROW_TOLERANCE
    if direction != 'HORIZONTAL' or len(children_bboxes) < 4:
        return False

    ys = sorted(set(round(b['y'] / row_tolerance) for b in children_bboxes))
    return len(ys) >= 2


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


JP_KEYWORD_MAP = {
    # Navigation / Actions
    'お問い合わせ': 'contact',
    '問い合わせ': 'contact',
    'お知らせ': 'news',
    '新着情報': 'news',
    '会社概要': 'company',
    '採用情報': 'recruit',
    'アクセス': 'access',
    'よくある質問': 'faq',
    'プライバシー': 'privacy',
    '利用規約': 'terms',
    'サイトマップ': 'sitemap',
    'ホーム': 'home',
    'トップ': 'top',
    'ログイン': 'login',
    '検索': 'search',
    '詳しく': 'more',
    '一覧': 'list',
    '特徴': 'features',
    '実績': 'works',
    'サービス': 'service',
    '料金': 'pricing',
    'メニュー': 'menu',
    'プラン': 'plan',
    'コンセプト': 'concept',
    # Food / Catering domain
    'ケータリング': 'catering',
    'フィンガーフード': 'finger-food',
    'フード': 'food',
    'イベント': 'event',
    'パーティー': 'party',
    'パーティ': 'party',
    # Business domain
    '企業': 'corporate',
    'オフィス': 'office',
    'スタッフ': 'staff',
    # Section types
    'ヒーロー': 'hero',
    'フッター': 'footer',
    'ヘッダー': 'header',
    'ナビゲーション': 'nav',
    'ギャラリー': 'gallery',
    'テスティモニアル': 'testimonial',
    'ブログ': 'blog',
    'カテゴリ': 'category',
    'カテゴリー': 'category',
    # Common words
    'ビジョン': 'vision',
    'ミッション': 'mission',
    '代表': 'representative',
    '紹介': 'introduction',
    'ご挨拶': 'greeting',
    '歴史': 'history',
    '沿革': 'history',
    '強み': 'strength',
    '理念': 'philosophy',
    '事業内容': 'business',
    '事業': 'business',
    '求人': 'job',
    '募集': 'recruit',
}


def to_kebab(text):
    """Convert text to kebab-case safe name.

    Non-ASCII-only text is matched against JP_KEYWORD_MAP for known
    Japanese terms. If no keyword matches, returns 'content' as a
    generic label. The downstream AI (via get_design_context) will
    assign final semantic names using the node's characters field.

    Issue 45: Extracted from generate-rename-map.sh to avoid duplication.
    Issue 47: Added CamelCase splitting (e.g. CamelCase → camel-case).
    Issue 170: Added JP_KEYWORD_MAP for Japanese keyword → English slug.
    """
    text = text.strip()
    if not text:
        return ''
    # Extract ASCII portion
    ascii_part = re.sub(r'[^\x00-\x7f]', '', text).strip()
    if not ascii_part:
        # Issue 170: Try JP_KEYWORD_MAP before falling back to 'content'
        slug = _jp_keyword_lookup(text)
        return slug if slug else 'content'
    # Split CamelCase before lowercasing (Issue 47)
    ascii_part = re.sub(r'([a-z])([A-Z])', r'\1 \2', ascii_part)
    ascii_part = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', ascii_part)
    # ASCII logic
    ascii_part = re.sub(r'[^\w\s-]', '', ascii_part.lower())
    ascii_part = re.sub(r'[\s_]+', '-', ascii_part)
    ascii_part = re.sub(r'-+', '-', ascii_part).strip('-')
    return ascii_part[:40] if ascii_part else 'content'


def _jp_keyword_lookup(text):
    """Look up Japanese text in JP_KEYWORD_MAP.

    Searches for known keywords in the text. Returns the first match
    found (longest match preferred to avoid partial hits).
    Returns empty string if no match.

    Issue 170: Extracted to share between to_kebab and generate-rename-map.
    """
    if not text:
        return ''
    # Sort by descending length so longer keywords match first
    # (e.g., "フィンガーフード" before "フード")
    for jp, en in sorted(JP_KEYWORD_MAP.items(), key=lambda kv: -len(kv[0])):
        if jp in text:
            return en
    return ''


# === Issue 165: Consecutive pattern detection ===
CONSECUTIVE_PATTERN_MIN = 3  # Minimum consecutive siblings with similar structure


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
        similarity_threshold = 0.7  # JACCARD_THRESHOLD

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


# === Issue 166: Heading-content pair detection ===
HEADING_MAX_HEIGHT_RATIO = 0.4  # Heading must be < 40% of content height
HEADING_MAX_CHILDREN = 5  # Heading frames typically have few children
HEADING_TEXT_RATIO = 0.5  # At least 50% of leaf descendants should be TEXT/VECTOR


def is_heading_like(node):
    """Check if a node looks like a section heading (small, text-heavy, decorative).

    Heading frames typically contain: title text + subtitle text + decorative
    elements (dots, vectors). They are small relative to content sections.

    Args:
        node: Figma node dict with children.

    Returns:
        bool: True if node appears to be a heading frame.
    """
    children = node.get('children', [])
    if not children:
        return False
    if len(children) > HEADING_MAX_CHILDREN:
        return False

    # Count leaf descendants by type
    def count_leaves(n):
        ch = n.get('children', [])
        if not ch:
            return {n.get('type', 'UNKNOWN'): 1}
        counts = {}
        for c in ch:
            for t, cnt in count_leaves(c).items():
                counts[t] = counts.get(t, 0) + cnt
        return counts

    leaf_counts = count_leaves(node)
    total_leaves = sum(leaf_counts.values())
    if total_leaves == 0:
        return False

    # Issue 175: ELLIPSE-dominated frames are decoration, not headings.
    # A heading MUST have at least as many TEXT nodes as ELLIPSE nodes.
    ellipse_count = leaf_counts.get('ELLIPSE', 0)
    text_count = leaf_counts.get('TEXT', 0)
    if ellipse_count > text_count:
        return False

    text_vector_count = (text_count
                         + leaf_counts.get('VECTOR', 0)
                         + ellipse_count)
    return (text_vector_count / total_leaves) >= HEADING_TEXT_RATIO


def detect_heading_content_pairs(children):
    """Detect heading-like frame followed by larger content frame.

    Pattern: a small "heading-like" frame (mostly text/vector, small height
    relative to siblings) followed by a larger "content" frame.

    Args:
        children: List of sibling nodes.

    Returns:
        list of pairs: [{'heading_idx': i, 'content_idx': j, 'children': [h, c]}]
    """
    if len(children) < 2:
        return []

    pairs = []
    used = set()

    for i in range(len(children) - 1):
        if i in used:
            continue

        h = children[i]
        c = children[i + 1]

        h_bb = get_bbox(h)
        c_bb = get_bbox(c)
        if not h_bb or not c_bb:
            continue

        # Heading must be shorter than content
        if h_bb['h'] >= c_bb['h'] * HEADING_MAX_HEIGHT_RATIO:
            # Only if heading is genuinely small
            if h_bb['h'] >= c_bb['h'] * 0.8:
                continue

        if not is_heading_like(h):
            continue

        # Content must be a substantial frame
        c_type = c.get('type', '')
        if c_type not in ('FRAME', 'GROUP', 'COMPONENT', 'INSTANCE', 'SECTION'):
            continue
        if not c.get('children'):
            continue

        pairs.append({
            'heading_idx': i,
            'content_idx': i + 1,
            'children': [h, c]
        })
        used.add(i)
        used.add(i + 1)

    return pairs


# === Issue 167: Loose element absorption ===
LOOSE_ELEMENT_MAX_HEIGHT = 20  # Small elements (dividers, spacers)
LOOSE_ABSORPTION_DISTANCE = 200  # Max distance to absorb into a group (member-level)


def _compute_zone_bboxes(children, candidate_groups):
    """Compute vertical bounding box for each candidate group from its member nodes.

    Args:
        children: list of sibling nodes.
        candidate_groups: list of dicts, each with 'node_ids' list.

    Returns:
        list of dicts: [{'y_top': float, 'y_bot': float,
                         'representative_idx': int, 'member_indices': set}]
    """
    child_id_to_idx = {ch.get('id', ''): idx for idx, ch in enumerate(children)}
    zone_bboxes = []
    for cg in candidate_groups:
        member_indices = [child_id_to_idx[nid] for nid in cg.get('node_ids', [])
                          if nid in child_id_to_idx]
        if not member_indices:
            continue
        y_tops = []
        y_bots = []
        for mi in member_indices:
            mbb = get_bbox(children[mi])
            if mbb:
                y_tops.append(mbb['y'])
                y_bots.append(mbb['y'] + mbb['h'])
        if y_tops and y_bots:
            zone_bboxes.append({
                'y_top': min(y_tops),
                'y_bot': max(y_bots),
                'representative_idx': member_indices[0],
                'member_indices': set(member_indices),
            })
    return zone_bboxes


def find_absorbable_elements(children, group_indices_set, candidate_groups=None):
    """Find loose elements (dividers, small frames) that should be absorbed
    into nearby groups.

    Loose elements are LINE nodes, small leaf shapes, or small rectangles
    that float between grouped sections. They should be merged into the
    nearest existing group.

    Two-pass approach (Issue 167 fix):
    1. Zone-level: If candidate_groups are provided, check if the loose
       element's Y-center falls within a zone's bounding box (y_top..y_bot).
       Elements inside a zone get distance=0 (overlap). This handles
       root-level dividers that sit between zone members but within the
       zone's vertical span.
    2. Member-level fallback: Check distance to individual group members
       using LOOSE_ABSORPTION_DISTANCE (original behavior).

    Args:
        children: list of sibling nodes.
        group_indices_set: set of indices already in groups.
        candidate_groups: optional list of candidate group dicts, each with
            'node_ids' (list of child node IDs). When provided, enables
            zone-level bounding box matching for root-level absorption.

    Returns:
        list of absorptions: [{'element_idx': i, 'target_group_idx': j,
                                'distance': float, 'reason': '...'}]
    """
    absorptions = []

    # Pre-compute zone bounding boxes if candidate groups provided
    zone_bboxes = _compute_zone_bboxes(children, candidate_groups) if candidate_groups else []

    for i, child in enumerate(children):
        if i in group_indices_set:
            continue

        bb = get_bbox(child)
        if not bb:
            continue

        child_type = child.get('type', '')

        # Criteria for "loose" element:
        # 1. LINE type (always loose)
        # 2. Small height element (divider-like) without children
        # 3. Small shape element (RECTANGLE/VECTOR)
        is_loose = False
        reason = ''

        if child_type == 'LINE':
            is_loose = True
            reason = 'LINE element'
        elif bb['h'] <= LOOSE_ELEMENT_MAX_HEIGHT and not child.get('children'):
            is_loose = True
            reason = f'small leaf (h={bb["h"]}px)'
        elif bb['h'] <= LOOSE_ELEMENT_MAX_HEIGHT and child_type in ('RECTANGLE', 'VECTOR'):
            is_loose = True
            reason = f'small shape (h={bb["h"]}px)'

        if not is_loose:
            continue

        # --- Pass 1: Zone-level bounding box check ---
        # If the loose element's Y-center falls within any zone's vertical
        # extent, absorb it into that zone (distance=0).
        best_group_idx = None
        best_distance = float('inf')
        zone_matched = False

        if zone_bboxes:
            elem_cy = bb['y'] + bb['h'] / 2
            for zb in zone_bboxes:
                if i in zb['member_indices']:
                    continue  # skip if already a member
                # Check if element center is within zone bbox
                if zb['y_top'] <= elem_cy <= zb['y_bot']:
                    # Element is inside the zone's vertical span
                    if 0.0 < best_distance:
                        best_distance = 0.0
                        best_group_idx = zb['representative_idx']
                        zone_matched = True
                else:
                    # Vertical distance to zone bbox edges
                    if elem_cy < zb['y_top']:
                        dist = zb['y_top'] - (bb['y'] + bb['h'])
                    else:
                        dist = bb['y'] - zb['y_bot']
                    dist = max(0.0, dist)
                    if dist < best_distance:
                        best_distance = dist
                        best_group_idx = zb['representative_idx']
                        zone_matched = (dist < LOOSE_ABSORPTION_DISTANCE)

        # --- Pass 2: Member-level fallback ---
        # Also check individual members; a closer member overrides zone result.
        for gi in group_indices_set:
            g_bb = get_bbox(children[gi])
            if not g_bb:
                continue

            # Vertical distance between element and group member
            if bb['y'] + bb['h'] <= g_bb['y']:
                dist = g_bb['y'] - (bb['y'] + bb['h'])
            elif g_bb['y'] + g_bb['h'] <= bb['y']:
                dist = bb['y'] - (g_bb['y'] + g_bb['h'])
            else:
                dist = 0  # overlapping

            if dist < best_distance:
                best_distance = dist
                best_group_idx = gi

        # Accept if:
        # - zone_matched (element center is within a zone's vertical span), OR
        # - best_distance < LOOSE_ABSORPTION_DISTANCE (member-level proximity)
        if best_group_idx is not None and (zone_matched or best_distance < LOOSE_ABSORPTION_DISTANCE):
            absorptions.append({
                'element_idx': i,
                'target_group_idx': best_group_idx,
                'distance': best_distance,
                'reason': reason
            })

    return absorptions

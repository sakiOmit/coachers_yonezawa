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
OFF_CANVAS_MARGIN = 1.5  # multiplier — elements with x > page_width * OFF_CANVAS_MARGIN are off-canvas (Issue 182)


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
    """Extract root node from various data formats.

    Supports:
    - {'document': {...}} — direct format
    - {'node': {...}} — alternative direct format
    - {'nodes': {'38:718': {'document': {...}}}} — Figma REST API format
    - Raw node data — fallback
    """
    # Figma REST API format: nodes.{nodeId}.document
    if 'nodes' in data and isinstance(data['nodes'], dict):
        for node_id, node_data in data['nodes'].items():
            if isinstance(node_data, dict) and 'document' in node_data:
                return node_data['document']
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


def is_off_canvas(node, page_width):
    """Check if a node is positioned completely outside the viewport.

    An element is considered off-canvas if:
    - Its left edge (x) is beyond page_width * OFF_CANVAS_MARGIN, OR
    - Its right edge (x + w) is less than 0 (completely to the left)

    These are typically unused assets or elements placed outside the
    visible design area.

    Issue 182: Elements outside viewport should not affect scoring or grouping.

    Args:
        node: Figma node dict.
        page_width: Width of the page/artboard (typically 1440px).

    Returns:
        bool: True if the node is completely off-canvas.
    """
    if page_width <= 0:
        return False
    bb = get_bbox(node)
    if not bb or bb['w'] == 0:
        return False
    # Right edge is left of viewport
    if bb['x'] + bb['w'] < 0:
        return True
    # Left edge is beyond off-canvas margin
    if bb['x'] > page_width * OFF_CANVAS_MARGIN:
        return True
    return False


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
    '事業紹介': 'business',
    '事業': 'business',
    '求人': 'job',
    '募集': 'recruit',
    '会社情報': 'company-info',
    '採用ブログ': 'recruit-blog',
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


# === Issue 186: Repeating tuple pattern detection ===
TUPLE_PATTERN_MIN = 3  # Minimum repetitions to detect a tuple pattern
TUPLE_MAX_SIZE = 5  # Maximum elements per tuple


def detect_repeating_tuple(children):
    """Detect repeating tuple patterns in flat sibling lists.

    Blog cards often consist of N separated sibling elements (e.g., IMAGE +
    FRAME + INSTANCE) repeated K times, producing N*K flat siblings. Standard
    structure_hash detection fails because each element within a tuple has a
    different type.

    This function detects such patterns by examining the sequence of element
    types and finding repeating subsequences of length 2..TUPLE_MAX_SIZE that
    repeat >= TUPLE_PATTERN_MIN times consecutively.

    Args:
        children: List of Figma node dicts with at least 'type', 'name', 'id'.

    Returns:
        list of detected tuple groups:
        [{'tuple_size': N, 'start_idx': S, 'count': C, 'children_indices': [...]}]
        - tuple_size: number of elements per tuple
        - start_idx: index of first element in the pattern
        - count: number of repetitions
        - children_indices: flat list of all element indices in the pattern

    Issue 186: Separated card patterns (IMAGE + FRAME + INSTANCE x 3).
    """
    if len(children) < TUPLE_PATTERN_MIN * 2:
        # Need at least min_reps * 2 elements (smallest tuple_size is 2)
        return []

    types = [c.get('type', '') for c in children]
    n = len(types)
    results = []
    covered = set()  # Track indices already assigned to a tuple group

    # Try tuple sizes from largest to smallest (prefer larger tuples)
    for tuple_size in range(min(TUPLE_MAX_SIZE, n // TUPLE_PATTERN_MIN), 1, -1):
        # Slide a window across the type sequence
        start = 0
        while start + tuple_size * TUPLE_PATTERN_MIN <= n:
            if start in covered:
                start += 1
                continue

            reference = types[start:start + tuple_size]
            # Tuple must contain at least 2 distinct types (otherwise
            # detect_consecutive_similar handles homogeneous sequences)
            if len(set(reference)) < 2:
                start += 1
                continue
            reps = 1
            pos = start + tuple_size

            while pos + tuple_size <= n:
                candidate = types[pos:pos + tuple_size]
                if candidate == reference:
                    reps += 1
                    pos += tuple_size
                else:
                    break

            if reps >= TUPLE_PATTERN_MIN:
                indices = list(range(start, start + tuple_size * reps))
                # Check no overlap with already covered indices
                if not any(i in covered for i in indices):
                    results.append({
                        'tuple_size': tuple_size,
                        'start_idx': start,
                        'count': reps,
                        'children_indices': indices,
                    })
                    covered.update(indices)
                    start = start + tuple_size * reps
                    continue

            start += 1

    return results


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


# === Issue 189: Decoration dot pattern detection ===
DECORATION_MAX_SIZE = 200  # Max width/height for decoration frame
DECORATION_SHAPE_RATIO = 0.6  # Min ratio of shape children (ELLIPSE/RECTANGLE/VECTOR)
DECORATION_MIN_SHAPES = 3  # Min number of shape leaf children


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

    children = node.get('children', [])
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
        ch = n.get('children', [])
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
        ch = n.get('children', [])
        if not ch:
            t = n.get('type', '')
            if t in shape_types:
                counts[t] += 1
            return
        for c in ch:
            count_shapes(c)

    count_shapes(node)
    return max(counts, key=counts.get)


# === Issue 190: Highlight text pattern detection ===
HIGHLIGHT_OVERLAP_RATIO = 0.8  # Min Y-overlap ratio for highlight detection
HIGHLIGHT_TEXT_MAX_LEN = 30  # Max text length for highlight
HIGHLIGHT_HEIGHT_RATIO_MIN = 0.5  # Min RECT height / TEXT height ratio
HIGHLIGHT_HEIGHT_RATIO_MAX = 2.0  # Max RECT height / TEXT height ratio


def detect_highlight_text(children):
    """Detect RECTANGLE + TEXT highlight pairs among siblings.

    Pattern: A RECTANGLE positioned behind a TEXT element at the same location
    acts as a text highlight/emphasis background. Common in Japanese web design
    for marking key phrases.

    Detection criteria for each RECTANGLE + TEXT pair:
    1. Y ranges overlap >= 80% (based on smaller element's height)
    2. X ranges also overlap significantly (>= 50% of smaller width)
    3. RECTANGLE height is 0.5-2.0x TEXT height
    4. TEXT content is short (<= 30 chars)
    5. RECTANGLE is a leaf node (no children)

    Args:
        children: List of sibling nodes.

    Returns:
        list: [{'rect_idx': i, 'text_idx': j, 'text_content': '...'}]

    Issue 190: Text highlighting pattern detection.
    """
    if not children:
        return []

    # Collect RECTANGLE and TEXT indices
    rect_indices = []
    text_indices = []
    for i, child in enumerate(children):
        child_type = child.get('type', '')
        if child_type == 'RECTANGLE' and not child.get('children'):
            rect_indices.append(i)
        elif child_type == 'TEXT':
            text_indices.append(i)

    if not rect_indices or not text_indices:
        return []

    results = []
    used_rects = set()
    used_texts = set()

    for ri in rect_indices:
        rect = children[ri]
        r_bb = get_bbox(rect)
        if r_bb['w'] <= 0 or r_bb['h'] <= 0:
            continue
        if ri in used_rects:
            continue

        for ti in text_indices:
            if ti in used_texts:
                continue
            text_node = children[ti]
            t_bb = get_bbox(text_node)
            if t_bb['w'] <= 0 or t_bb['h'] <= 0:
                continue

            # Check text length
            text_content = text_node.get('characters', '') or text_node.get('name', '')
            if len(text_content) > HIGHLIGHT_TEXT_MAX_LEN:
                continue

            # Check height ratio
            if t_bb['h'] <= 0:
                continue
            height_ratio = r_bb['h'] / t_bb['h']
            if height_ratio < HIGHLIGHT_HEIGHT_RATIO_MIN or height_ratio > HIGHLIGHT_HEIGHT_RATIO_MAX:
                continue

            # Check Y overlap
            y_overlap_top = max(r_bb['y'], t_bb['y'])
            y_overlap_bot = min(r_bb['y'] + r_bb['h'], t_bb['y'] + t_bb['h'])
            y_overlap = max(0, y_overlap_bot - y_overlap_top)
            smaller_h = min(r_bb['h'], t_bb['h'])
            if smaller_h <= 0:
                continue
            y_overlap_ratio = y_overlap / smaller_h
            if y_overlap_ratio < HIGHLIGHT_OVERLAP_RATIO:
                continue

            # Check X overlap
            x_overlap_left = max(r_bb['x'], t_bb['x'])
            x_overlap_right = min(r_bb['x'] + r_bb['w'], t_bb['x'] + t_bb['w'])
            x_overlap = max(0, x_overlap_right - x_overlap_left)
            smaller_w = min(r_bb['w'], t_bb['w'])
            if smaller_w <= 0:
                continue
            x_overlap_ratio = x_overlap / smaller_w
            if x_overlap_ratio < 0.5:
                continue

            results.append({
                'rect_idx': ri,
                'text_idx': ti,
                'text_content': text_content,
            })
            used_rects.add(ri)
            used_texts.add(ti)
            break  # Move to next RECTANGLE

    return results


# === Issue 180: Background-content layer detection ===
BG_WIDTH_RATIO = 0.8  # Background RECTANGLE must cover >=80% of parent width
BG_MIN_HEIGHT_RATIO = 0.3  # Background must be >=30% of parent height
BG_DECORATION_MAX_AREA_RATIO = 0.05  # Small same-positioned elements are decoration


def detect_bg_content_layers(children, parent_bb):
    """Detect background RECTANGLE + decoration vs content elements.

    Pattern: A full-width RECTANGLE (>=80% parent width) acts as a background layer.
    Small sibling elements (VECTOR, ELLIPSE) that overlap the RECTANGLE's position
    are treated as decoration (same visual layer). Everything else is content.

    Only triggers when:
    1. There is exactly 1 full-width RECTANGLE among siblings (leaf node, no children)
    2. The RECTANGLE covers >=30% of parent height (not just a thin divider)
    3. There are >=2 non-decoration siblings (content elements)

    Args:
        children: List of sibling nodes.
        parent_bb: Parent bounding box dict with x, y, w, h.

    Returns:
        list: Grouping candidates. Each has:
            - method: 'semantic'
            - semantic_type: 'bg-content'
            - node_ids: IDs of content-layer elements
            - bg_node_ids: IDs of bg-layer elements (RECTANGLE + decorations)
            - suggested_name: 'content-layer'
            - suggested_wrapper: 'content-group'
    """
    if not children or not parent_bb or parent_bb['w'] <= 0 or parent_bb['h'] <= 0:
        return []

    # Step 1: Find full-width RECTANGLE siblings (leaf node)
    bg_candidates = []
    for i, child in enumerate(children):
        if child.get('type') != 'RECTANGLE':
            continue
        # Must be a leaf node (no children)
        if child.get('children'):
            continue
        bb = get_bbox(child)
        if bb['w'] <= 0 or bb['h'] <= 0:
            continue
        # Width >= 80% of parent width
        if bb['w'] < parent_bb['w'] * BG_WIDTH_RATIO:
            continue
        # Height >= 30% of parent height (not a thin divider)
        if bb['h'] < parent_bb['h'] * BG_MIN_HEIGHT_RATIO:
            continue
        bg_candidates.append((i, child, bb))

    # Must be exactly 1 bg candidate (ambiguous if multiple)
    if len(bg_candidates) != 1:
        return []

    bg_idx, bg_node, bg_bb = bg_candidates[0]
    bg_area = bg_bb['w'] * bg_bb['h']

    # Step 2: Find decoration elements (small VECTOR/ELLIPSE overlapping the bg)
    decoration_indices = set()
    decoration_indices.add(bg_idx)

    for i, child in enumerate(children):
        if i == bg_idx:
            continue
        child_type = child.get('type', '')
        if child_type not in ('VECTOR', 'ELLIPSE'):
            continue
        # Must be a leaf node
        if child.get('children'):
            continue
        cb = get_bbox(child)
        if cb['w'] <= 0 or cb['h'] <= 0:
            continue
        child_area = cb['w'] * cb['h']
        # "small" = area < 5% of bg RECTANGLE area
        if bg_area > 0 and child_area / bg_area >= BG_DECORATION_MAX_AREA_RATIO:
            continue
        # Must overlap the bg RECTANGLE's bounding box
        overlap_x = max(0, min(bg_bb['x'] + bg_bb['w'], cb['x'] + cb['w']) - max(bg_bb['x'], cb['x']))
        overlap_y = max(0, min(bg_bb['y'] + bg_bb['h'], cb['y'] + cb['h']) - max(bg_bb['y'], cb['y']))
        if overlap_x > 0 and overlap_y > 0:
            decoration_indices.add(i)

    # Step 3: Content = everything else
    content_indices = [i for i in range(len(children)) if i not in decoration_indices]

    # Must have >= 2 content elements
    if len(content_indices) < 2:
        return []

    content_ids = [children[i].get('id', '') for i in content_indices]
    content_names = [children[i].get('name', '') for i in content_indices]
    bg_ids = [children[i].get('id', '') for i in sorted(decoration_indices)]
    bg_names = [children[i].get('name', '') for i in sorted(decoration_indices)]

    return [{
        'method': 'semantic',
        'semantic_type': 'bg-content',
        'node_ids': content_ids,
        'node_names': content_names,
        'bg_node_ids': bg_ids,
        'bg_node_names': bg_names,
        'count': len(content_ids),
        'suggested_name': 'content-layer',
        'suggested_wrapper': 'content-group',
    }]


# === Issue 185: EN+JP label pair detection ===
EN_LABEL_MAX_WORDS = 3  # Max words for English label (e.g., "OUR BUSINESS")
EN_JP_PAIR_MAX_DISTANCE = 200  # px — max distance between EN and JP label pair


def detect_en_jp_label_pairs(children):
    """Detect English + Japanese label pairs among sibling TEXT nodes.

    Pattern: An uppercase ASCII text (e.g., "COMPANY") paired with a
    Japanese text (e.g., "会社情報") at similar Y or X position.

    Args:
        children: List of sibling nodes.

    Returns:
        list of pairs: [{'en_idx': i, 'jp_idx': j, 'en_text': '...', 'jp_text': '...'}]

    Issue 185: EN+JP label pairs get generic names. Detect them for
    semantic renaming (en-label-* / heading-*).
    """
    if len(children) < 2:
        return []

    # Collect TEXT nodes with their indices
    text_nodes = []
    for i, child in enumerate(children):
        if child.get('type') != 'TEXT':
            continue
        content = child.get('characters', '') or child.get('name', '')
        if not content or not content.strip():
            continue
        text_nodes.append((i, child, content.strip()))

    if len(text_nodes) < 2:
        return []

    def _is_en_label(text):
        """Check if text is a short uppercase ASCII label."""
        ascii_only = re.sub(r'[^\x00-\x7f]', '', text).strip()
        if not ascii_only or ascii_only != text.strip():
            return False
        words = ascii_only.split()
        if len(words) < 1 or len(words) > EN_LABEL_MAX_WORDS:
            return False
        # Must be uppercase (allow minor punctuation)
        alpha_chars = re.sub(r'[^a-zA-Z]', '', ascii_only)
        if not alpha_chars:
            return False
        return alpha_chars == alpha_chars.upper()

    def _is_jp_text(text):
        """Check if text contains non-ASCII (Japanese) characters."""
        non_ascii = re.sub(r'[\x00-\x7f]', '', text).strip()
        return len(non_ascii) > 0

    def _pair_distance(node_a, node_b):
        """Compute minimum distance between two nodes (Y-range or X-range proximity)."""
        bb_a = get_bbox(node_a)
        bb_b = get_bbox(node_b)
        # Y distance
        if bb_a['y'] + bb_a['h'] < bb_b['y']:
            dy = bb_b['y'] - (bb_a['y'] + bb_a['h'])
        elif bb_b['y'] + bb_b['h'] < bb_a['y']:
            dy = bb_a['y'] - (bb_b['y'] + bb_b['h'])
        else:
            dy = 0
        # X distance
        if bb_a['x'] + bb_a['w'] < bb_b['x']:
            dx = bb_b['x'] - (bb_a['x'] + bb_a['w'])
        elif bb_b['x'] + bb_b['w'] < bb_a['x']:
            dx = bb_a['x'] - (bb_b['x'] + bb_b['w'])
        else:
            dx = 0
        return min(dx, dy) if dx > 0 and dy > 0 else max(dx, dy)

    # Find all EN labels and JP texts
    en_indices = [(i, node, text) for i, node, text in text_nodes if _is_en_label(text)]
    jp_indices = [(i, node, text) for i, node, text in text_nodes if _is_jp_text(text)]

    pairs = []
    used_en = set()
    used_jp = set()

    for en_i, en_node, en_text in en_indices:
        best_jp = None
        best_dist = float('inf')
        for jp_i, jp_node, jp_text in jp_indices:
            if jp_i in used_jp:
                continue
            dist = _pair_distance(en_node, jp_node)
            if dist <= EN_JP_PAIR_MAX_DISTANCE and dist < best_dist:
                best_dist = dist
                best_jp = (jp_i, jp_node, jp_text)
        if best_jp and en_i not in used_en:
            jp_i, jp_node, jp_text = best_jp
            pairs.append({
                'en_idx': en_i,
                'jp_idx': jp_i,
                'en_text': en_text,
                'jp_text': jp_text,
            })
            used_en.add(en_i)
            used_jp.add(jp_i)

    return pairs


# === Issue 193: CTA square button detection ===
CTA_SQUARE_RATIO_MIN = 0.8  # Min width/height ratio for square CTA
CTA_SQUARE_RATIO_MAX = 1.2  # Max width/height ratio for square CTA
CTA_Y_THRESHOLD = 100  # px — max Y position from top for CTA placement

# === Issue 192: Side panel detection ===
SIDE_PANEL_MAX_WIDTH = 80  # px — max width for side panel
SIDE_PANEL_HEIGHT_RATIO = 3.0  # Min height/width ratio for side panel


# === Issue 181: Table row structure detection ===
TABLE_MIN_ROWS = 3  # Minimum background RECTANGLEs to form a table
TABLE_ROW_WIDTH_RATIO = 0.9  # Row bg RECTANGLE must cover >=90% of parent width
TABLE_DIVIDER_MAX_HEIGHT = 2  # px — divider VECTORs are <=2px height


def detect_table_rows(children, parent_bb):
    """Detect table-like structure: alternating full-width background RECTANGLEs
    + divider VECTORs + text elements grouped by Y position into rows.

    Pattern detection:
    1. Find 3+ full-width RECTANGLE siblings (>=90% parent width, leaf, unnamed)
    2. Find full-width VECTOR/LINE dividers (>=90% parent width, height <= 2px)
    3. For each RECTANGLE, find TEXT siblings whose Y-center falls within
       [RECT.y, RECT.y + RECT.h]
    4. Group: heading element (if exists, before first RECTANGLE) + row groups
       + trailing dividers

    Args:
        children: List of sibling nodes.
        parent_bb: Bounding box of the parent node (dict with x, y, w, h).

    Returns:
        list: One grouping candidate per table, containing:
            - method: 'semantic'
            - semantic_type: 'table'
            - node_ids: All table-member node IDs (bg RECTs + dividers + texts + heading)
            - suggested_name: 'table-{slug}'
            - suggested_wrapper: 'table-container'
            - row_count: number of data rows

    Issue 181: Flat sibling elements forming table rows are not grouped.
    """
    if not children or parent_bb.get('w', 0) <= 0:
        return []

    min_width = parent_bb['w'] * TABLE_ROW_WIDTH_RATIO

    # Step 1: Find full-width RECTANGLE leaves (row backgrounds)
    full_width_rects = []
    for c in children:
        if (c.get('type') == 'RECTANGLE'
                and not c.get('children')
                and get_bbox(c)['w'] >= min_width):
            full_width_rects.append(c)

    if len(full_width_rects) < TABLE_MIN_ROWS:
        return []

    # Step 2: Find full-width dividers (VECTOR/LINE, height <= 2px)
    dividers = []
    for c in children:
        if c.get('type') in ('VECTOR', 'LINE'):
            bb = get_bbox(c)
            if bb['w'] >= min_width and bb['h'] <= TABLE_DIVIDER_MAX_HEIGHT:
                dividers.append(c)

    rect_ids = {c.get('id', '') for c in full_width_rects}
    divider_ids = {c.get('id', '') for c in dividers}

    # Step 3: For each RECTANGLE, find TEXT siblings whose Y-center
    # falls within [rect.y, rect.y + rect.h]
    all_row_member_ids = set()
    row_count = 0
    for rect in full_width_rects:
        rect_bb = get_bbox(rect)
        rect_y_top = rect_bb['y']
        rect_y_bot = rect_bb['y'] + rect_bb['h']
        row_members = [rect]

        for c in children:
            c_id = c.get('id', '')
            if c_id in rect_ids or c_id in divider_ids:
                continue
            c_bb = get_bbox(c)
            c_cy = c_bb['y'] + c_bb['h'] / 2
            if rect_y_top <= c_cy <= rect_y_bot:
                row_members.append(c)

        # Only count as a row if there's at least one text/content element
        if len(row_members) > 1:
            row_count += 1
        for m in row_members:
            all_row_member_ids.add(m.get('id', ''))

    # Need at least TABLE_MIN_ROWS actual content rows
    if row_count < TABLE_MIN_ROWS:
        return []

    # Step 4: Include dividers in the table
    for d in dividers:
        all_row_member_ids.add(d.get('id', ''))

    # Step 5: Check for heading element before first RECTANGLE (by Y position)
    rects_sorted = sorted(full_width_rects, key=lambda c: get_bbox(c)['y'])
    first_rect_y = get_bbox(rects_sorted[0])['y']
    for c in children:
        c_id = c.get('id', '')
        if c_id in all_row_member_ids:
            continue
        c_bb = get_bbox(c)
        # Heading must be above first row background
        if c_bb['y'] + c_bb['h'] <= first_rect_y:
            c_type = c.get('type', '')
            # Accept FRAME/GROUP/TEXT as potential headings
            if c_type in ('FRAME', 'GROUP', 'TEXT', 'INSTANCE', 'COMPONENT'):
                all_row_member_ids.add(c_id)

    # Step 6: Infer name from heading or first text content
    slug = ''
    # Try heading text first (elements above first rect)
    for c in children:
        c_bb = get_bbox(c)
        if c_bb['y'] + c_bb['h'] <= first_rect_y:
            texts = get_text_children_content([c], max_items=1)
            if not texts:
                texts = get_text_children_content(c.get('children', []), max_items=1)
            if texts:
                slug = to_kebab(texts[0])
                break

    if not slug:
        slug = 'data'

    suggested_name = f'table-{slug}'

    # Collect all member node IDs and names preserving child order
    ordered_members = [c for c in children if c.get('id', '') in all_row_member_ids]
    ordered_ids = [c.get('id', '') for c in ordered_members]
    ordered_names = [c.get('name', '') for c in ordered_members]

    return [{
        'method': 'semantic',
        'semantic_type': 'table',
        'node_ids': ordered_ids,
        'node_names': ordered_names,
        'count': len(ordered_ids),
        'suggested_name': suggested_name,
        'suggested_wrapper': 'table-container',
        'row_count': row_count,
    }]


# --- Enriched Children Table (Issue 194) ---

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
    for c in node.get('children', []):
        result = _collect_text_preview(c, max_depth - 1, max_len)
        if result:
            return result
    return ''


def _compute_child_types(children):
    """Compute compact child type summary like '2REC+1TEX+1FRA'.

    Uses 3-letter abbreviations sorted alphabetically.
    """
    TYPE_ABBR = {
        'BOOLEAN_OPERATION': 'BOO',
        'COMPONENT': 'CMP',
        'COMPONENT_SET': 'CMS',
        'ELLIPSE': 'ELL',
        'FRAME': 'FRA',
        'GROUP': 'GRP',
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


def _compute_flags(node, page_width, page_height):
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
    children = node.get('children', [])
    is_leaf = len(children) == 0

    # Visibility
    if node.get('visible') is False:
        flags.append('hidden')

    # Off-canvas
    if page_width > 0 and is_off_canvas(node, page_width):
        flags.append('off-canvas')

    # Overflow (extends beyond page on right or bottom)
    if page_width > 0:
        right_edge = bb['x'] + bb['w']
        if right_edge > page_width * 1.05:  # 5% tolerance
            flags.append('overflow')
        if page_height > 0 and bb['y'] + bb['h'] > page_height * 1.02:
            flags.append('overflow-y')

    # Background candidates
    if is_leaf and node_type in ('RECTANGLE', 'VECTOR', 'ELLIPSE'):
        if page_width > 0:
            width_ratio = bb['w'] / page_width
            if width_ratio >= 0.95:
                flags.append('bg-full')
            elif width_ratio >= 0.8:
                flags.append('bg-wide')

    # Decoration pattern
    if not is_leaf and is_decoration_pattern(node):
        flags.append('decoration')

    # Tiny element
    if bb['w'] > 0 and bb['h'] > 0 and bb['w'] < 50 and bb['h'] < 50:
        flags.append('tiny')

    return flags


def generate_enriched_table(children, page_width=1440, page_height=0):
    """Generate enriched Markdown table for Phase B Claude reasoning.

    Produces the enriched format:
    | # | ID | Name | Type | X | Y | W x H | Leaf? | ChildTypes | Flags | Text |

    This format provides Claude with enough structural information to detect
    patterns like cards, tables, background layers, etc. without needing
    rule-based Phase A detectors.

    Issue 194: Phase B Claude推論のネストレベル拡張

    Args:
        children: List of Figma child nodes (with absoluteBoundingBox).
        page_width: Page width for flag computation (default: 1440).
        page_height: Page height for overflow detection (default: 0 = skip).

    Returns:
        str: Markdown table string.
    """
    header = '| # | ID | Name | Type | X | Y | W x H | Leaf? | ChildTypes | Flags | Text |'
    separator = '|---|-----|------|------|---|---|-------|-------|------------|-------|------|'
    rows = [header, separator]

    for i, child in enumerate(children):
        bb = get_bbox(child)
        x = int(bb['x'])
        y = int(bb['y'])
        w = int(bb['w'])
        h = int(bb['h'])
        node_type = child.get('type', '')
        name = (child.get('name', '') or '')[:35]
        node_id = child.get('id', '')
        child_nodes = child.get('children', [])
        is_leaf = len(child_nodes) == 0
        leaf_str = 'Y' if is_leaf else 'N'

        # Child types summary
        child_types = _compute_child_types(child_nodes)

        # Flags
        flags = _compute_flags(child, page_width, page_height)
        flags_str = ','.join(flags) if flags else '-'

        # Text preview
        text = _collect_text_preview(child)
        if not text:
            text = '-'

        row = f'| {i+1} | {node_id} | {name} | {node_type} | {x} | {y} | {w}x{h} | {leaf_str} | {child_types} | {flags_str} | {text} |'
        rows.append(row)

    return '\n'.join(rows)

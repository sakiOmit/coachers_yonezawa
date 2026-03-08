"""Rename strategy helpers for semantic_rename.infer_name().

Extracted from semantic_rename.py for maintainability.
Each function handles a priority group from the infer_name() dispatch table.
"""

from .constants import (
    BULLET_MAX_SIZE,
    BUTTON_MAX_HEIGHT,
    BUTTON_MAX_WIDTH,
    BUTTON_TEXT_MAX_LEN,
    CTA_SQUARE_RATIO_MIN,
    CTA_SQUARE_RATIO_MAX,
    CTA_X_POSITION_RATIO,
    CTA_Y_THRESHOLD,
    DIVIDER_MAX_HEIGHT,
    FOOTER_MAX_HEIGHT,
    FOOTER_PROXIMITY,
    FOOTER_TEXT_RATIO,
    HEADER_Y_THRESHOLD,
    HEADING_BODY_TEXT_THRESHOLD,
    ICON_MAX_SIZE,
    IMAGE_WRAPPER_RATIO,
    NAV_GRANDCHILD_MIN,
    NAV_MAX_TEXT_LEN,
    NAV_MIN_TEXT_COUNT,
    OVERFLOW_BG_MIN_WIDTH,
    SECTION_BG_WIDTH_RATIO,
    SECTION_ROOT_WIDTH,
    SECTION_ROOT_WIDTH_RATIO,
    SIDE_PANEL_HEIGHT_RATIO,
    SIDE_PANEL_LEFT_X_RATIO,
    SIDE_PANEL_MAX_WIDTH,
    SIDE_PANEL_RIGHT_X_RATIO,
    UNNAMED_RE,
    WIDE_ELEMENT_MIN_WIDTH,
    WIDE_ELEMENT_RATIO,
)
from .detection import (
    decoration_dominant_shape,
    is_decoration_pattern,
)
from .geometry import filter_visible_children
from .naming import to_kebab

__all__ = [
    'RENAME_STRATEGIES',
    '_infer_from_text_content',
    '_infer_from_shape',
    '_infer_from_position',
    '_infer_from_children',
]


# ---------------------------------------------------------------------------
# Shared helpers used by the strategy functions
# ---------------------------------------------------------------------------

# Shape prefix mapping (canonical copy in semantic_rename.py; imported here for use)
_SHAPE_PREFIXES = {
    'RECTANGLE': 'bg',
    'ELLIPSE': 'circle',
    'LINE': 'divider',
    'VECTOR': 'icon',
    'IMAGE': 'img',
}

# CTA keywords used in Priority 3.15
_CTA_KEYWORDS = ['お問い合わせ', '問い合わせ', 'contact', '資料請求', '相談', '申し込み', '申込']


def _get_text_children_content_local(children):
    """Collect TEXT children's content, filtering unnamed."""
    from .metadata import get_text_children_content as _get_text_children
    return _get_text_children(children, filter_unnamed=True)


def _resolve_slug_local(text_contents_list):
    """Get a meaningful slug, trying to_kebab then JP keyword lookup."""
    from .naming import _jp_keyword_lookup
    for t in text_contents_list:
        slug = to_kebab(t[:30])
        if slug and slug != 'content':
            return slug
    for t in text_contents_list:
        jp_slug = _jp_keyword_lookup(t)
        if jp_slug:
            return jp_slug
    return ''


def _has_image_wrapper_local(children):
    """Check if any child is an image wrapper frame."""
    for c in children:
        c_type = c.get('type', '')
        if c_type not in ('FRAME', 'GROUP', 'INSTANCE', 'COMPONENT'):
            continue
        sub_children = filter_visible_children(c)
        if not sub_children:
            continue
        rect_count = sum(1 for sc in sub_children if sc.get('type', '') in ('RECTANGLE', 'IMAGE', 'ELLIPSE'))
        if rect_count >= len(sub_children) * IMAGE_WRAPPER_RATIO and rect_count >= 1:
            return True
    return False


# ---------------------------------------------------------------------------
# Priority 0-1: Text content based inference
# ---------------------------------------------------------------------------

def _infer_from_text_content(node, node_type, name, sibling_index):
    """Priorities 0-1: EN+JP label pairs and text content.

    Returns inferred name or None if not applicable.
    """
    if node_type != 'TEXT':
        return None

    text_content = node.get('characters', '') or name
    role = _infer_text_role_local(text_content)
    slug = to_kebab(text_content[:30])
    if role and slug:
        return f'{role}-{slug}'
    if slug:
        return f'text-{slug}'
    return f'text-{sibling_index}'


def _infer_text_role_local(text_content):
    """Infer role from text content (local copy to avoid circular import)."""
    content = text_content.strip()
    if not content:
        return None
    if len(content) <= BUTTON_TEXT_MAX_LEN and any(kw in content.lower() for kw in [
        'more', '詳しく', '一覧', 'submit', '送信', '申し込', 'contact', 'click',
        '見る', '戻る', '申込', '詳細',
    ]):
        return 'btn-text'
    from .constants import LABEL_MAX_LEN
    if len(content) <= LABEL_MAX_LEN:
        return 'label'
    return 'body'


# ---------------------------------------------------------------------------
# Priority 2: Shape analysis
# ---------------------------------------------------------------------------

def _infer_from_shape(node, node_type, children, w, h, sibling_index):
    """Priority 2: Shape analysis for leaf nodes.

    Returns inferred name or None if not applicable.
    """
    if node_type not in _SHAPE_PREFIXES or children:
        return None

    # Issue 17: fills-based IMAGE detection (enriched metadata)
    fills = node.get('fills', [])
    if fills and isinstance(fills, list):
        if any(f.get('type') == 'IMAGE' for f in fills if isinstance(f, dict)):
            return f'img-{sibling_index}'

    # Explicit IMAGE node → always img- prefix (benchmark improvement 1)
    if node_type == 'IMAGE':
        return f'img-{sibling_index}'

    # Small ELLIPSE → bullet point marker (benchmark improvement 2)
    if node_type == 'ELLIPSE' and w <= BULLET_MAX_SIZE and h <= BULLET_MAX_SIZE:
        return f'bullet-{sibling_index}'

    # Thin wide rectangle -> divider
    if node_type == 'RECTANGLE' and w > 0 and h > 0:
        if w / max(h, 1) > 10 and h < DIVIDER_MAX_HEIGHT:
            return f'divider-{sibling_index}'
        # Full-width RECTANGLE → section background (benchmark improvement 3)
        if w >= SECTION_ROOT_WIDTH * SECTION_BG_WIDTH_RATIO:
            return f'section-bg-{sibling_index}'

    prefix = _SHAPE_PREFIXES[node_type]
    return f'{prefix}-{sibling_index}'


# ---------------------------------------------------------------------------
# Priority 3-3.2: Position analysis
# ---------------------------------------------------------------------------

def _infer_from_position(node, node_type, parent, children, abs_bbox, w, h, sibling_index, total_siblings):
    """Priorities 3-3.2: Position-based inference (header/footer/CTA/side-panel/icon/nav).

    Returns inferred name or None if not applicable.
    """
    # Priority 3: Position analysis (top-level frames)
    if node_type == 'FRAME' and parent and parent.get('type') in ('PAGE', 'CANVAS'):
        y = abs_bbox.get('y', 0)
        if sibling_index == 0 or y < HEADER_Y_THRESHOLD:
            return 'section-header'
        if sibling_index == total_siblings - 1:
            return 'section-footer'
        return f'section-{sibling_index}'

    # Priority 3.1: Header/Footer heuristic (Issue 16, Issue 37)
    if node_type in ('FRAME', 'GROUP', 'INSTANCE', 'COMPONENT', 'SECTION') and parent and children:
        result = _try_header_footer(node_type, parent, children, abs_bbox, w, h)
        if result:
            return result

    # Priority 3.15: CTA square button detection (Issue 193)
    name = node.get('name', '')
    result = _try_cta(node, node_type, parent, children, abs_bbox, w, h, name, sibling_index)
    if result:
        return result

    # Priority 3.16: Side panel detection (Issue 192)
    if w > 0 and h > 0 and w <= SIDE_PANEL_MAX_WIDTH and h > w * SIDE_PANEL_HEIGHT_RATIO and parent:
        parent_bbox = parent.get('absoluteBoundingBox', {})
        parent_w = parent_bbox.get('width', 0) or SECTION_ROOT_WIDTH
        if parent_w >= SECTION_ROOT_WIDTH * SECTION_ROOT_WIDTH_RATIO:
            node_x = abs_bbox.get('x', 0)
            parent_x = parent_bbox.get('x', 0)
            relative_x = node_x - parent_x
            if relative_x > parent_w * SIDE_PANEL_RIGHT_X_RATIO or relative_x < parent_w * SIDE_PANEL_LEFT_X_RATIO:
                return f'side-panel-{sibling_index}'

    # Priority 3.2: Tiny empty frame -> icon
    if not children and w > 0 and w <= ICON_MAX_SIZE and h > 0 and h <= ICON_MAX_SIZE:
        return f'icon-{sibling_index}'

    return None


def _try_header_footer(node_type, parent, children, abs_bbox, w, h):
    """Try to detect header or footer based on position and structure."""
    parent_bbox = parent.get('absoluteBoundingBox', {})
    parent_y = parent_bbox.get('y', 0)
    parent_h = parent_bbox.get('height', 0)
    parent_w = parent_bbox.get('width', 0)
    node_y = abs_bbox.get('y', 0)
    relative_y = node_y - parent_y
    is_wide = w > max(parent_w * WIDE_ELEMENT_RATIO, WIDE_ELEMENT_MIN_WIDTH)

    if not is_wide:
        return None

    # Header: near top + has nav child (frame with 4+ text grandchildren)
    if relative_y < HEADER_Y_THRESHOLD:
        has_nav = False
        for c in children:
            if c.get('type') in ('FRAME', 'GROUP', 'INSTANCE', 'COMPONENT'):
                text_gchildren = [gc for gc in c.get('children', [])
                                  if gc.get('visible') != False and gc.get('type') == 'TEXT']
                if len(text_gchildren) >= NAV_GRANDCHILD_MIN:
                    has_nav = True
                    break
        if has_nav:
            return 'header'

    # Footer: near bottom + compact + text-heavy
    if parent_h > 0:
        node_bottom = node_y + h
        parent_bottom = parent_y + parent_h
        if abs(node_bottom - parent_bottom) < FOOTER_PROXIMITY and h < FOOTER_MAX_HEIGHT:
            text_count = sum(1 for c in children if c.get('type') == 'TEXT')
            if text_count >= max(len(children) * FOOTER_TEXT_RATIO, 1):
                return 'footer'

    return None


def _try_cta(node, node_type, parent, children, abs_bbox, w, h, name, sibling_index):
    """Try CTA square button detection (Issue 193)."""
    if not (w > 0 and h > 0 and parent):
        return None

    wh_ratio = w / h
    parent_bbox = parent.get('absoluteBoundingBox', {})
    parent_w = parent_bbox.get('width', 0) or SECTION_ROOT_WIDTH
    parent_y = parent_bbox.get('y', 0)
    node_x = abs_bbox.get('x', 0)
    node_y = abs_bbox.get('y', 0)
    relative_y = node_y - parent_y

    if not (CTA_SQUARE_RATIO_MIN <= wh_ratio <= CTA_SQUARE_RATIO_MAX
            and node_x > parent_w * CTA_X_POSITION_RATIO
            and relative_y < CTA_Y_THRESHOLD):
        return None

    # Check for CTA keyword text in children or self
    cta_texts = []
    if node_type == 'TEXT':
        cta_texts = [node.get('characters', '') or name]
    elif children:
        cta_texts = _get_text_children_content_local(children)
        if not cta_texts:
            for c in children[:5]:
                for gc in c.get('children', []):
                    if gc.get('type') == 'TEXT':
                        content = gc.get('characters', '') or gc.get('name', '')
                        if content:
                            cta_texts.append(content)

    for ct in cta_texts:
        ct_lower = ct.lower().strip()
        if any(kw in ct_lower for kw in _CTA_KEYWORDS):
            slug = to_kebab(ct[:20])
            return f'cta-{slug}' if slug and slug != 'content' else f'cta-{sibling_index}'

    return None


# ---------------------------------------------------------------------------
# Priority 3.5, 4: Children structure analysis
# ---------------------------------------------------------------------------

def _detect_card_pattern(children, child_types, text_contents, w, sibling_index):
    """Detect card-like pattern: image/rectangle + text.

    Returns inferred name or None.
    """
    child_count = len(children)
    has_direct_image = 'IMAGE' in child_types
    has_direct_rect = 'RECTANGLE' in child_types and 2 <= child_count <= 6
    has_rect_with_fill = any(
        c.get('type') == 'RECTANGLE'
        and c.get('fills') and isinstance(c.get('fills'), list)
        and any(f.get('type') == 'IMAGE' for f in c['fills'] if isinstance(f, dict))
        for c in children if isinstance(c, dict)
    )
    has_image_wrap = _has_image_wrapper_local(children)
    has_image = has_direct_image or has_rect_with_fill or has_image_wrap or has_direct_rect
    has_text = 'TEXT' in child_types

    if has_image and has_text and w < OVERFLOW_BG_MIN_WIDTH:
        slug = _resolve_slug_local(text_contents)
        if not slug:
            slug = str(sibling_index)
        return f'card-{slug}'
    return None


def _detect_heading_or_body(children, child_types, text_contents, text_type_count, sibling_index):
    """Detect heading vs body/content patterns.

    Returns inferred name or None.
    """
    has_image_wrap = _has_image_wrapper_local(children)
    has_image = 'IMAGE' in child_types or has_image_wrap
    if text_type_count > 2 or not text_contents or has_image or len(children) > 3:
        return None

    max_text_len = max(len(t) for t in text_contents)
    slug = _resolve_slug_local(text_contents)
    if max_text_len > HEADING_BODY_TEXT_THRESHOLD:
        has_non_text = any(ct != 'TEXT' for ct in child_types)
        prefix = 'content' if has_non_text else 'body'
        if slug:
            return f'{prefix}-{slug}'
        return f'{prefix}-text-{text_type_count}'
    if slug:
        return f'heading-{slug}'
    return f'heading-{sibling_index}'


def _detect_container_or_group(children, text_contents, sibling_index):
    """Fallback: infer container/group name from grandchild text content (Issue 174).

    Returns inferred name.
    """
    all_texts = text_contents if text_contents else []
    if not all_texts:
        for c in children[:10]:
            for gc in filter_visible_children(c):
                if gc.get('type') == 'TEXT':
                    content = gc.get('characters', '') or gc.get('name', '')
                    if content and not UNNAMED_RE.match(content):
                        all_texts.append(content)
                        if len(all_texts) >= 3:
                            break
            if len(all_texts) >= 3:
                break
    slug = _resolve_slug_local(all_texts) if all_texts else ''
    if len(children) > 5:
        return f'container-{slug}' if slug else f'container-{sibling_index}'
    return f'group-{slug}' if slug else f'group-{sibling_index}'


def _infer_from_children(node, node_type, children, w, h, sibling_index):
    """Priorities 3.5-4: Navigation, decoration, card, button, heading, container.

    Returns inferred name or None if not applicable.
    """
    if not children:
        return None

    text_contents = _get_text_children_content_local(children)

    # Priority 3.5: Navigation detection
    text_count = len(text_contents)
    if text_count >= NAV_MIN_TEXT_COUNT and all(len(t) <= NAV_MAX_TEXT_LEN for t in text_contents):
        return f'nav-{sibling_index}'

    # Priority 4.0: Decoration pattern detection (Issue 189)
    if is_decoration_pattern(node):
        dominant = decoration_dominant_shape(node)
        if dominant == 'ELLIPSE':
            return f'decoration-dots-{sibling_index}'
        else:
            return f'decoration-pattern-{sibling_index}'

    # Priority 4: Child structure analysis
    child_types = [c.get('type', '') for c in children]
    text_type_count = len([ct for ct in child_types if ct == 'TEXT'])

    # Card-like detection
    result = _detect_card_pattern(children, child_types, text_contents, w, sibling_index)
    if result:
        return result

    # Small icon-like: tiny frame with 0-1 children
    if w > 0 and w <= ICON_MAX_SIZE and h > 0 and h <= ICON_MAX_SIZE and len(children) <= 1:
        return f'icon-{sibling_index}'

    # Button/Tab: small frame with 1-2 children, short text
    if h > 0 and h <= BUTTON_MAX_HEIGHT and w > 0 and w < BUTTON_MAX_WIDTH and len(children) <= 2:
        if text_contents:
            slug = to_kebab(text_contents[0][:20])
            if slug:
                return f'btn-{slug}'
        return f'btn-{sibling_index}'

    # Heading vs Content (Issue 14)
    result = _detect_heading_or_body(children, child_types, text_contents, text_type_count, sibling_index)
    if result:
        return result

    # text-block with slug
    if 'TEXT' in child_types and len(children) <= 3:
        slug = _resolve_slug_local(text_contents)
        if slug:
            return f'text-block-{slug}'
        return f'text-block-{sibling_index}'

    # Fallback: container or group
    return _detect_container_or_group(children, text_contents, sibling_index)


# ---------------------------------------------------------------------------
# Strategy dispatch table — executed in priority order by infer_name()
# in semantic_rename.py.  Each entry documents a priority group, the
# function that implements it, a human-readable description, and the
# default confidence score assigned when the strategy matches.
#
# Entries whose confidence is None use a dynamic calculation
# (_estimate_children_confidence) instead of a fixed value.
#
# See .claude/rules/figma-prepare.md "リネームロジック（優先順）" for the
# authoritative priority table.
# ---------------------------------------------------------------------------

RENAME_STRATEGIES = (
    # (priority, function, description, confidence)
    (0,   _infer_from_text_content, "EN+JP label pair / text content-based naming",  90),
    (2,   _infer_from_shape,        "Shape analysis for leaf nodes (divider/bg/icon/bullet)", 85),
    (3,   _infer_from_position,     "Position-based inference (header/footer/CTA/side-panel/icon)", 75),
    (3.5, _infer_from_children,     "Children structure analysis (nav/decoration/card/btn/heading/container)", None),
)

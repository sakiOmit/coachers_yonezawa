"""Semantic rename logic for figma-prepare Phase 3.

Extracts all Python logic previously embedded in generate-rename-map.sh.
Provides ``generate_rename_map()`` as the main entry point, plus helper
functions for name inference and rename collection.

Issue: Extracted from shell heredoc for maintainability.
"""

import json
import sys

from .constants import (
    UNNAMED_RE,
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
    LABEL_MAX_LEN,
    NAV_GRANDCHILD_MIN,
    NAV_MAX_TEXT_LEN,
    NAV_MIN_TEXT_COUNT,
    OVERFLOW_BG_MIN_WIDTH,
    SECTION_ROOT_WIDTH,
    SECTION_ROOT_WIDTH_RATIO,
    SIDE_PANEL_HEIGHT_RATIO,
    SIDE_PANEL_LEFT_X_RATIO,
    SIDE_PANEL_MAX_WIDTH,
    SIDE_PANEL_RIGHT_X_RATIO,
    WIDE_ELEMENT_MIN_WIDTH,
    WIDE_ELEMENT_RATIO,
    EN_JP_PAIR_MAX_DISTANCE,
)
from .detection import (
    detect_en_jp_label_pairs,
    decoration_dominant_shape,
    is_decoration_pattern,
)
from .geometry import resolve_absolute_coords, yaml_str
from .metadata import get_root_node, get_text_children_content as _get_text_children, load_metadata
from .naming import _jp_keyword_lookup, to_kebab

# ---------------------------------------------------------------------------
# Shape prefix mapping
# ---------------------------------------------------------------------------

SHAPE_PREFIXES = {
    'RECTANGLE': 'bg',
    'ELLIPSE': 'circle',
    'LINE': 'divider',
    'VECTOR': 'icon',
    'IMAGE': 'img',
}

# CTA keywords used in Priority 3.15
CTA_KEYWORDS = ['お問い合わせ', '問い合わせ', 'contact', '資料請求', '相談', '申し込み', '申込']


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def get_text_children_content(children):
    """Collect TEXT children's content, filtering unnamed. Delegates to shared util (Issue 49)."""
    return _get_text_children(children, filter_unnamed=True)


def infer_text_role(text_content, font_size=None):
    """Infer role from text content."""
    content = text_content.strip()
    if not content:
        return None
    # Short button-like text
    if len(content) <= BUTTON_TEXT_MAX_LEN and any(kw in content.lower() for kw in [
        'more', '詳しく', '一覧', 'submit', '送信', '申し込', 'contact', 'click',
        '見る', '戻る', '申込', '詳細',
    ]):
        return 'btn-text'
    # Labels
    if len(content) <= LABEL_MAX_LEN:
        return 'label'
    return 'body'


def has_image_wrapper(children):
    """Check if any child is an image wrapper frame (contains mostly images/rectangles).

    Detects patterns like: FRAME containing [RECTANGLE, RECTANGLE, IMAGE] where the
    sub-frame acts as an image container. Returns True if any child FRAME/GROUP has
    >= 50% of its children as image-like types (RECTANGLE, IMAGE, ELLIPSE).
    """
    for c in children:
        c_type = c.get('type', '')
        if c_type not in ('FRAME', 'GROUP', 'INSTANCE', 'COMPONENT'):
            continue
        sub_children = [sc for sc in c.get('children', []) if sc.get('visible') != False]
        if not sub_children:
            continue
        rect_count = sum(1 for sc in sub_children if sc.get('type', '') in ('RECTANGLE', 'IMAGE', 'ELLIPSE'))
        if rect_count >= len(sub_children) * IMAGE_WRAPPER_RATIO and rect_count >= 1:
            return True
    return False


def _resolve_slug(text_contents_list):
    """Get a meaningful slug, trying to_kebab then JP keyword lookup.

    Issue 170: Helper to resolve a slug that avoids bare 'content'.
    """
    for t in text_contents_list:
        slug = to_kebab(t[:30])
        if slug and slug != 'content':
            return slug
    # to_kebab returned 'content' for all — try JP keyword lookup
    for t in text_contents_list:
        jp_slug = _jp_keyword_lookup(t)
        if jp_slug:
            return jp_slug
    return ''


def infer_name(node, parent=None, sibling_index=0, total_siblings=1):
    """Infer semantic name for an unnamed node."""
    node_type = node.get('type', '')
    children = [c for c in node.get('children', []) if c.get('visible') != False]
    name = node.get('name', '')
    abs_bbox = node.get('absoluteBoundingBox', {})
    w = abs_bbox.get('width', 0)
    h = abs_bbox.get('height', 0)

    # Priority 1: Text content
    # Prefer enriched characters over name (Issue 38)
    if node_type == 'TEXT':
        text_content = node.get('characters', '') or name
        role = infer_text_role(text_content)
        slug = to_kebab(text_content[:30])
        if role and slug:
            return f'{role}-{slug}'
        if slug:
            return f'text-{slug}'
        return f'text-{sibling_index}'

    # Priority 2: Shape analysis
    if node_type in SHAPE_PREFIXES and not children:
        prefix = SHAPE_PREFIXES[node_type]
        # Issue 17: fills-based IMAGE detection (enriched metadata)
        fills = node.get('fills', [])
        if fills and isinstance(fills, list):
            if any(f.get('type') == 'IMAGE' for f in fills if isinstance(f, dict)):
                return f'img-{sibling_index}'
        # Thin wide rectangle → divider
        if node_type == 'RECTANGLE' and w > 0 and h > 0:
            if w / max(h, 1) > 10 and h < DIVIDER_MAX_HEIGHT:
                return f'divider-{sibling_index}'
        return f'{prefix}-{sibling_index}'

    # Priority 3: Position analysis (top-level frames)
    # Note (Issue 39): This fires only when metadata root is PAGE/CANVAS (page-level query).
    if node_type == 'FRAME' and parent and parent.get('type') in ('PAGE', 'CANVAS'):
        y = abs_bbox.get('y', 0)
        if sibling_index == 0 or y < HEADER_Y_THRESHOLD:
            return 'section-header'
        if sibling_index == total_siblings - 1:
            return 'section-footer'
        return f'section-{sibling_index}'

    # Priority 3.1: Header/Footer heuristic (Issue 16, Issue 37)
    if node_type in ('FRAME', 'GROUP', 'INSTANCE', 'COMPONENT', 'SECTION') and parent and children:
        parent_bbox = parent.get('absoluteBoundingBox', {})
        parent_y = parent_bbox.get('y', 0)
        parent_h = parent_bbox.get('height', 0)
        parent_w = parent_bbox.get('width', 0)
        node_y = abs_bbox.get('y', 0)
        relative_y = node_y - parent_y
        is_wide = w > max(parent_w * WIDE_ELEMENT_RATIO, WIDE_ELEMENT_MIN_WIDTH)

        if is_wide:
            # Header: near top + has nav child (frame with 4+ text grandchildren)
            if relative_y < HEADER_Y_THRESHOLD:
                has_nav = False
                for c in children:
                    # Issue 77: Include INSTANCE/COMPONENT for nav detection
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

    # Priority 3.15: CTA square button detection (Issue 193)
    if w > 0 and h > 0 and parent:
        wh_ratio = w / h
        parent_bbox = parent.get('absoluteBoundingBox', {})
        parent_w = parent_bbox.get('width', 0) or SECTION_ROOT_WIDTH
        parent_y = parent_bbox.get('y', 0)
        node_x = abs_bbox.get('x', 0)
        node_y = abs_bbox.get('y', 0)
        relative_y = node_y - parent_y
        if (CTA_SQUARE_RATIO_MIN <= wh_ratio <= CTA_SQUARE_RATIO_MAX
                and node_x > parent_w * CTA_X_POSITION_RATIO
                and relative_y < CTA_Y_THRESHOLD):
            # Check for CTA keyword text in children or self
            cta_texts = []
            if node_type == 'TEXT':
                cta_texts = [node.get('characters', '') or name]
            elif children:
                cta_texts = get_text_children_content(children)
                if not cta_texts:
                    for c in children[:5]:
                        for gc in c.get('children', []):
                            if gc.get('type') == 'TEXT':
                                content = gc.get('characters', '') or gc.get('name', '')
                                if content:
                                    cta_texts.append(content)
            for ct in cta_texts:
                ct_lower = ct.lower().strip()
                if any(kw in ct_lower for kw in CTA_KEYWORDS):
                    slug = to_kebab(ct[:20])
                    return f'cta-{slug}' if slug and slug != 'content' else f'cta-{sibling_index}'

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

    # Priority 3.2: Tiny empty frame → icon
    if not children and w > 0 and w <= ICON_MAX_SIZE and h > 0 and h <= ICON_MAX_SIZE:
        return f'icon-{sibling_index}'

    # Priority 3.5+ and 4: Requires children
    if children:
        text_contents = get_text_children_content(children)

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
        child_count = len(children)
        has_direct_image = 'IMAGE' in child_types
        has_direct_rect = 'RECTANGLE' in child_types and 2 <= child_count <= 6
        has_rect_with_fill = any(
            c.get('type') == 'RECTANGLE'
            and c.get('fills') and isinstance(c.get('fills'), list)
            and any(f.get('type') == 'IMAGE' for f in c['fills'] if isinstance(f, dict))
            for c in children if isinstance(c, dict)
        )
        has_image_wrap = has_image_wrapper(children)
        has_image = has_direct_image or has_rect_with_fill or has_image_wrap or has_direct_rect
        has_text = 'TEXT' in child_types
        text_type_count = len([ct for ct in child_types if ct == 'TEXT'])
        has_button = any(
            c.get('type') == 'FRAME' and len(c.get('children', [])) <= 2
            and any(gc.get('type') == 'TEXT' for gc in c.get('children', []))
            for c in children if isinstance(c, dict)
        )

        # Card-like: image/rectangle + text, exclude section-root-width frames
        if has_image and has_text and w < OVERFLOW_BG_MIN_WIDTH:
            slug = _resolve_slug(text_contents)
            if not slug:
                slug = str(sibling_index)
            return f'card-{slug}'

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

        # Heading vs Content: check TEXT children length (Issue 14)
        if text_type_count <= 2 and len(text_contents) >= 1 and not has_image and not has_image_wrap and len(children) <= 3:
            max_text_len = max(len(t) for t in text_contents)
            slug = _resolve_slug(text_contents)
            if max_text_len > HEADING_BODY_TEXT_THRESHOLD:
                has_non_text = any(ct != 'TEXT' for ct in child_types)
                prefix = 'content' if has_non_text else 'body'
                if slug:
                    return f'{prefix}-{slug}'
                return f'{prefix}-text-{text_type_count}'
            if slug:
                return f'heading-{slug}'
            return f'heading-{sibling_index}'

        # text-block with slug
        if has_text and len(children) <= 3:
            slug = _resolve_slug(text_contents)
            if slug:
                return f'text-block-{slug}'
            return f'text-block-{sibling_index}'

        # Issue 174: Try semantic naming from child text content
        all_texts = text_contents if text_contents else []
        if not all_texts:
            for c in children[:10]:
                for gc in [g for g in c.get('children', []) if g.get('visible') != False]:
                    if gc.get('type') == 'TEXT':
                        content = gc.get('characters', '') or gc.get('name', '')
                        if content and not UNNAMED_RE.match(content):
                            all_texts.append(content)
                            if len(all_texts) >= 3:
                                break
                if len(all_texts) >= 3:
                    break
        slug = _resolve_slug(all_texts) if all_texts else ''
        if len(children) > 5:
            return f'container-{slug}' if slug else f'container-{sibling_index}'
        return f'group-{slug}' if slug else f'group-{sibling_index}'

    # Priority 5: Fallback
    type_prefix = node_type.lower().replace('_', '-')
    return f'{type_prefix}-{sibling_index}'


def collect_renames(node, parent=None, sibling_index=0, total_siblings=1, renames=None, en_jp_overrides=None):
    """Recursively collect rename candidates."""
    if renames is None:
        renames = {}
    if en_jp_overrides is None:
        en_jp_overrides = {}

    if node.get('visible') == False:
        return renames

    name = node.get('name', '')
    node_id = node.get('id', '')

    # Issue 185: Check if this node has an EN+JP pair override
    if node_id in en_jp_overrides:
        override_name = en_jp_overrides[node_id]
        if override_name != name:
            renames[node_id] = {
                'old_name': name,
                'new_name': override_name,
                'type': node.get('type', ''),
                'inference_method': 'en_jp_pair',
            }
    elif UNNAMED_RE.match(name) and node_id:
        new_name = infer_name(node, parent, sibling_index, total_siblings)
        if new_name and new_name != name:
            renames[node_id] = {
                'old_name': name,
                'new_name': new_name,
                'type': node.get('type', ''),
                'inference_method': 'auto',
            }

    children = [c for c in node.get('children', []) if c.get('visible') != False]

    # Issue 185: Detect EN+JP label pairs among children
    child_overrides = {}
    if children:
        pairs = detect_en_jp_label_pairs(children)
        for pair in pairs:
            en_child = children[pair['en_idx']]
            jp_child = children[pair['jp_idx']]
            en_id = en_child.get('id', '')
            jp_id = jp_child.get('id', '')
            en_name_val = en_child.get('name', '')
            jp_name_val = jp_child.get('name', '')
            en_slug = to_kebab(pair['en_text'][:20])
            # Only override unnamed nodes
            if en_id and UNNAMED_RE.match(en_name_val):
                child_overrides[en_id] = f'en-label-{en_slug}' if en_slug and en_slug != 'content' else f'en-label-{pair["en_idx"]}'
            if jp_id and UNNAMED_RE.match(jp_name_val):
                jp_slug = _jp_keyword_lookup(pair['jp_text'])
                if not jp_slug:
                    jp_slug = to_kebab(pair['jp_text'][:30])
                if jp_slug and jp_slug != 'content':
                    child_overrides[jp_id] = f'heading-{jp_slug}'
                else:
                    child_overrides[jp_id] = f'heading-{pair["jp_idx"]}'

    for i, child in enumerate(children):
        collect_renames(child, node, i, len(children), renames, child_overrides)

    return renames


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_rename_map(metadata_path, output_file=''):
    """Generate a semantic rename map from Figma metadata.

    Args:
        metadata_path: Path to Figma metadata JSON file.
        output_file: If non-empty, write YAML to this path and print summary JSON.
                     If empty, print full rename JSON to stdout.

    Returns:
        None (output goes to stdout/file).

    Raises:
        Prints error JSON to stderr and calls sys.exit(1) on failure.
    """
    sys.setrecursionlimit(3000)  # Guard against deeply nested Figma files (Issue 48)

    try:
        data = load_metadata(metadata_path)
        root = get_root_node(data)
        resolve_absolute_coords(root)
        renames = collect_renames(root)

        if output_file:
            # YAML output
            with open(output_file, 'w') as f:
                f.write('# Figma Rename Map\n')
                f.write(f'# Total renames: {len(renames)}\n')
                f.write('# Generated by /figma-prepare Phase 3\n')
                f.write('# Review before applying with --apply\n\n')
                f.write('renames:\n')
                for node_id, info in sorted(renames.items()):
                    f.write(f'  {yaml_str(node_id)}:\n')
                    f.write(f'    old: {yaml_str(info["old_name"])}\n')
                    f.write(f'    new: {yaml_str(info["new_name"])}\n')
                    f.write(f'    type: {yaml_str(info["type"])}\n')
            print(json.dumps({
                'total': len(renames),
                'output': output_file,
                'status': 'dry-run'
            }, indent=2))
        else:
            # JSON to stdout
            print(json.dumps({
                'total': len(renames),
                'renames': renames,
                'status': 'dry-run'
            }, indent=2, ensure_ascii=False))

    except Exception as e:
        print(json.dumps({'error': str(e)}), file=sys.stderr)
        sys.exit(1)

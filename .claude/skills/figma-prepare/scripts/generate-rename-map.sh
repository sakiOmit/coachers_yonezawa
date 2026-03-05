#!/usr/bin/env bash
# Phase 3: Generate Semantic Rename Map
#
# Usage: bash generate-rename-map.sh <metadata.json> [--output rename-map.yaml]
# Input: Figma get_metadata output (JSON)
# Output: YAML rename map (nodeId → newName)
# Exit: 0=success, 1=error

set -euo pipefail

if [[ $# -lt 1 ]] || [[ ! -f "$1" ]]; then
  echo '{"error": "Usage: generate-rename-map.sh <metadata.json> [--output file.yaml]"}' >&2
  exit 1
fi

OUTPUT_FILE=""
if [[ "${2:-}" == "--output" ]] && [[ -n "${3:-}" ]]; then
  OUTPUT_FILE="$3"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 -c "
import json, sys, os
sys.setrecursionlimit(3000)  # Guard against deeply nested Figma files (Issue 48)
sys.path.insert(0, os.path.join(sys.argv[1], 'lib'))
from figma_utils import resolve_absolute_coords, get_root_node, UNNAMED_RE, yaml_str, to_kebab, get_text_children_content as _get_text_children, _jp_keyword_lookup, JP_KEYWORD_MAP, detect_en_jp_label_pairs, EN_JP_PAIR_MAX_DISTANCE, CTA_SQUARE_RATIO_MIN, CTA_SQUARE_RATIO_MAX, CTA_Y_THRESHOLD, SIDE_PANEL_MAX_WIDTH, SIDE_PANEL_HEIGHT_RATIO, SECTION_ROOT_WIDTH, is_decoration_pattern, decoration_dominant_shape

# --- Rename Thresholds (Issue 124) ---
DIVIDER_MAX_HEIGHT = 5         # px — thin horizontal rectangle → divider
HEADER_Y_THRESHOLD = 100      # px — position from parent top to detect header
FOOTER_PROXIMITY = 100        # px — distance from parent bottom to detect footer
FOOTER_MAX_HEIGHT = 200       # px — max height for footer detection
WIDE_ELEMENT_RATIO = 0.7      # fraction of parent width to be 'wide'
WIDE_ELEMENT_MIN_WIDTH = 500  # px — minimum absolute width for 'wide'
ICON_MAX_SIZE = 48             # px — max width/height for icon detection
BUTTON_MAX_HEIGHT = 70         # px — max height for button detection
BUTTON_MAX_WIDTH = 300         # px — max width for button detection
BUTTON_TEXT_MAX_LEN = 15       # chars — max text length for button role
LABEL_MAX_LEN = 20             # chars — max text length for label role
NAV_MIN_TEXT_COUNT = 4         # minimum TEXT children for nav detection
NAV_MAX_TEXT_LEN = 20          # chars — max text length per nav item
NAV_GRANDCHILD_MIN = 4        # minimum TEXT grandchildren for header nav detection

# Prefix mapping by context
SHAPE_PREFIXES = {
    'RECTANGLE': 'bg',
    'ELLIPSE': 'circle',
    'LINE': 'divider',
    'VECTOR': 'icon',
    'IMAGE': 'img',
}

def get_text_children_content(children):
    \"\"\"Collect TEXT children's content, filtering unnamed. Delegates to shared util (Issue 49).\"\"\"
    return _get_text_children(children, filter_unnamed=True)

def infer_text_role(text_content, font_size=None):
    \"\"\"Infer role from text content.\"\"\"
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
    \"\"\"Check if any child is an image wrapper frame (contains mostly images/rectangles).

    Detects patterns like: FRAME containing [RECTANGLE, RECTANGLE, IMAGE] where the
    sub-frame acts as an image container. Returns True if any child FRAME/GROUP has
    >= 50% of its children as image-like types (RECTANGLE, IMAGE, ELLIPSE).
    \"\"\"
    for c in children:
        c_type = c.get('type', '')
        if c_type not in ('FRAME', 'GROUP', 'INSTANCE', 'COMPONENT'):
            continue
        sub_children = c.get('children', [])
        if not sub_children:
            continue
        rect_count = sum(1 for sc in sub_children if sc.get('type', '') in ('RECTANGLE', 'IMAGE', 'ELLIPSE'))
        if rect_count >= len(sub_children) * 0.5 and rect_count >= 1:
            return True
    return False

def infer_name(node, parent=None, sibling_index=0, total_siblings=1):
    \"\"\"Infer semantic name for an unnamed node.\"\"\"
    node_type = node.get('type', '')
    children = node.get('children', [])
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
    # In typical /figma-prepare usage (artboard-level query), root is FRAME, so this
    # branch is unreachable. Priority 3.1 handles header/footer in that case.
    if node_type == 'FRAME' and parent and parent.get('type') in ('PAGE', 'CANVAS'):
        y = abs_bbox.get('y', 0)
        if sibling_index == 0 or y < HEADER_Y_THRESHOLD:
            return f'section-header'
        if sibling_index == total_siblings - 1:
            return f'section-footer'
        return f'section-{sibling_index}'

    # Priority 3.1: Header/Footer heuristic (Issue 16, Issue 37)
    # Detects headers/footers within section roots (not just PAGE/CANVAS children)
    # Include INSTANCE/COMPONENT/SECTION as headers/footers may be component instances
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
                                          if gc.get('type') == 'TEXT']
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
                    if text_count >= max(len(children) * 0.3, 1):
                        return 'footer'

    # Priority 3.15: CTA square button detection (Issue 193)
    # Nearly square element at top-right with CTA keyword text
    CTA_KEYWORDS = ['お問い合わせ', '問い合わせ', 'contact', '資料請求', '相談', '申し込み', '申込']
    if w > 0 and h > 0 and parent:
        wh_ratio = w / h
        parent_bbox = parent.get('absoluteBoundingBox', {})
        parent_w = parent_bbox.get('width', 0) or SECTION_ROOT_WIDTH
        parent_y = parent_bbox.get('y', 0)
        node_x = abs_bbox.get('x', 0)
        node_y = abs_bbox.get('y', 0)
        relative_y = node_y - parent_y
        if (CTA_SQUARE_RATIO_MIN <= wh_ratio <= CTA_SQUARE_RATIO_MAX
                and node_x > parent_w * 0.8
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
    # Narrow vertical frame at page edge (SNS links, scroll indicators)
    if w > 0 and h > 0 and w <= SIDE_PANEL_MAX_WIDTH and h > w * SIDE_PANEL_HEIGHT_RATIO and parent:
        parent_bbox = parent.get('absoluteBoundingBox', {})
        parent_w = parent_bbox.get('width', 0) or SECTION_ROOT_WIDTH
        node_x = abs_bbox.get('x', 0)
        parent_x = parent_bbox.get('x', 0)
        relative_x = node_x - parent_x
        if relative_x > parent_w * 0.9 or relative_x < parent_w * 0.1:
            return f'side-panel-{sibling_index}'

    # Priority 3.2: Tiny empty frame → icon
    if not children and w > 0 and w <= ICON_MAX_SIZE and h > 0 and h <= ICON_MAX_SIZE:
        return f'icon-{sibling_index}'

    # Priority 3.5+ and 4: Requires children
    if children:
        text_contents = get_text_children_content(children)

        # Priority 3.5: Navigation detection
        text_count = len(text_contents)
        # Navigation: 4+ short text children → nav
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
        # Image detection: direct IMAGE, direct RECTANGLE (image placeholder in card context),
        # RECTANGLE with IMAGE fill, or wrapped in sub-frame
        has_direct_image = 'IMAGE' in child_types
        # RECTANGLE counts as image-like only when child_count is 2-6 (card-like structure).
        # Frames with many children (e.g., sections) should not treat every RECTANGLE as image.
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

        # Issue 170: Helper to resolve a slug that avoids bare 'content'
        def _resolve_slug(text_contents_list):
            \"\"\"Get a meaningful slug, trying to_kebab then JP keyword lookup.\"\"\"
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

        # Card-like: image/rectangle (direct or wrapped) + text (with or without button)
        # Exclude section-root-width frames (w >= 1400) from card detection — those are sections, not cards
        if has_image and has_text and w < 1400:
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
        # Guard: exclude card-like structures with image/rectangle children or image wrappers
        if text_type_count <= 2 and len(text_contents) >= 1 and not has_image and not has_image_wrap and len(children) <= 3:
            max_text_len = max(len(t) for t in text_contents)
            slug = _resolve_slug(text_contents)
            if max_text_len > 50:
                # Long text = body content, not heading
                # Issue 170: TEXT-only frames use 'body-*' to avoid 'content-content'
                has_non_text = any(ct != 'TEXT' for ct in child_types)
                prefix = 'content' if has_non_text else 'body'
                if slug:
                    return f'{prefix}-{slug}'
                return f'{prefix}-text-{text_type_count}'
            if slug:
                return f'heading-{slug}'
            return f'heading-{sibling_index}'

        # text-block with slug (improved from generic index)
        # Issue 170: Use _resolve_slug to avoid 'text-block-content'
        if has_text and len(children) <= 3:
            slug = _resolve_slug(text_contents)
            if slug:
                return f'text-block-{slug}'
            return f'text-block-{sibling_index}'

        # Issue 174: Try semantic naming from child text content
        all_texts = text_contents if text_contents else []
        if not all_texts:
            # Recurse one level deeper to find text in grandchildren
            for c in children[:10]:
                for gc in c.get('children', []):
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
    \"\"\"Recursively collect rename candidates.\"\"\"
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

    children = node.get('children', [])

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
                child_overrides[en_id] = f'en-label-{en_slug}' if en_slug and en_slug != 'content' else f'en-label-{pair[\"en_idx\"]}'
            if jp_id and UNNAMED_RE.match(jp_name_val):
                jp_slug = _jp_keyword_lookup(pair['jp_text'])
                if not jp_slug:
                    jp_slug = to_kebab(pair['jp_text'][:30])
                if jp_slug and jp_slug != 'content':
                    child_overrides[jp_id] = f'heading-{jp_slug}'
                else:
                    child_overrides[jp_id] = f'heading-{pair[\"jp_idx\"]}'

    for i, child in enumerate(children):
        collect_renames(child, node, i, len(children), renames, child_overrides)

    return renames

try:
    with open(sys.argv[2], 'r') as f:
        data = json.load(f)

    root = get_root_node(data)
    resolve_absolute_coords(root)
    renames = collect_renames(root)

    output_file = sys.argv[3] if len(sys.argv) > 3 else ''

    if output_file:
        # YAML output
        with open(output_file, 'w') as f:
            f.write('# Figma Rename Map\\n')
            f.write(f'# Total renames: {len(renames)}\\n')
            f.write('# Generated by /figma-prepare Phase 3\\n')
            f.write('# Review before applying with --apply\\n\\n')
            f.write('renames:\\n')
            for node_id, info in sorted(renames.items()):
                f.write(f'  {yaml_str(node_id)}:\\n')
                f.write(f'    old: {yaml_str(info[\"old_name\"])}\\n')
                f.write(f'    new: {yaml_str(info[\"new_name\"])}\\n')
                f.write(f'    type: {yaml_str(info[\"type\"])}\\n')
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
" "${SCRIPT_DIR}/.." "$1" "$OUTPUT_FILE"

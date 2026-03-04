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
import json, re, sys, unicodedata
sys.path.insert(0, '${SCRIPT_DIR}/../lib')
from figma_utils import resolve_absolute_coords, get_root_node, UNNAMED_RE, yaml_str

# Prefix mapping by context
SHAPE_PREFIXES = {
    'RECTANGLE': 'bg',
    'ELLIPSE': 'circle',
    'LINE': 'divider',
    'VECTOR': 'icon',
    'IMAGE': 'img',
}

# Japanese keyword → English slug mapping
JP_KEYWORD_MAP = {
    '募集詳細を見る': 'view-detail',
    '募集要項': 'requirements',
    'すべて': 'all', 'お知らせ': 'news', '一覧': 'list',
    '詳しく': 'more', '詳細': 'detail', '見る': 'view',
    '採用': 'recruit', '新卒': 'new-grad', '中途': 'mid-career',
    '募集': 'jobs', '事業': 'business', '仕事': 'work',
    'について': 'about', '環境': 'environment', '社員': 'staff',
    'インタビュー': 'interview', 'お問い合わせ': 'contact',
    '送信': 'submit', '申し込': 'apply', '戻る': 'back',
    'トップ': 'top', 'ホーム': 'home', '検索': 'search',
    'カテゴリー': 'category', 'イベント': 'event',
    '要項': 'requirements',
}

def to_kebab(text):
    \"\"\"Convert text to kebab-case safe name. Supports Japanese via keyword map.\"\"\"
    text = text.strip()
    if not text:
        return ''
    # Check JP keyword map first (longest match first, with ratio check)
    for jp, en in sorted(JP_KEYWORD_MAP.items(), key=lambda x: -len(x[0])):
        if jp in text:
            ratio = len(jp) / len(text)
            if ratio >= 0.5:  # keyword must be >= 50% of text length
                return en
    # Strip non-ASCII characters first (Issue 13)
    text = re.sub(r'[^\x00-\x7f]', ' ', text)
    # ASCII logic
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text[:40] if text else ''

def get_text_children_content(children):
    \"\"\"Collect named TEXT children's name as text content proxy.\"\"\"
    texts = []
    for c in children:
        if c.get('type') == 'TEXT':
            name = c.get('name', '')
            if name and not UNNAMED_RE.match(name):
                texts.append(name)
    return texts

def infer_text_role(text_content, font_size=None):
    \"\"\"Infer role from text content.\"\"\"
    content = text_content.strip()
    if not content:
        return None
    # Short button-like text
    if len(content) <= 15 and any(kw in content.lower() for kw in [
        'more', '詳しく', '一覧', 'submit', '送信', '申し込', 'contact', 'click',
        '見る', '戻る', '申込', '詳細',
    ]):
        return 'btn-text'
    # Labels
    if len(content) <= 20:
        return 'label'
    return 'body'

def infer_name(node, parent=None, sibling_index=0, total_siblings=1):
    \"\"\"Infer semantic name for an unnamed node.\"\"\"
    node_type = node.get('type', '')
    children = node.get('children', [])
    name = node.get('name', '')
    abs_bbox = node.get('absoluteBoundingBox', {})
    w = abs_bbox.get('width', 0)
    h = abs_bbox.get('height', 0)

    # Priority 1: Text content (TEXT nodes have content as name in get_metadata)
    if node_type == 'TEXT':
        text_content = name  # TEXT nodes store content in name field
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
            if w / max(h, 1) > 10 and h < 5:
                return f'divider-{sibling_index}'
        return f'{prefix}-{sibling_index}'

    # Priority 3: Position analysis (top-level frames)
    if node_type == 'FRAME' and parent and parent.get('type') in ('PAGE', 'CANVAS'):
        y = abs_bbox.get('y', 0)
        if sibling_index == 0 or y < 100:
            return f'section-header'
        if sibling_index == total_siblings - 1:
            return f'section-footer'
        return f'section-{sibling_index}'

    # Priority 3.1: Header/Footer heuristic (Issue 16)
    # Detects headers/footers within section roots (not just PAGE/CANVAS children)
    if node_type in ('FRAME', 'GROUP') and parent and children:
        parent_bbox = parent.get('absoluteBoundingBox', {})
        parent_y = parent_bbox.get('y', 0)
        parent_h = parent_bbox.get('height', 0)
        parent_w = parent_bbox.get('width', 0)
        node_y = abs_bbox.get('y', 0)
        relative_y = node_y - parent_y
        is_wide = w > max(parent_w * 0.7, 500)

        if is_wide:
            # Header: near top + has nav child (frame with 4+ text grandchildren)
            if relative_y < 100:
                has_nav = False
                for c in children:
                    if c.get('type') in ('FRAME', 'GROUP'):
                        text_gchildren = [gc for gc in c.get('children', [])
                                          if gc.get('type') == 'TEXT']
                        if len(text_gchildren) >= 4:
                            has_nav = True
                            break
                if has_nav:
                    return 'header'

            # Footer: near bottom + compact + text-heavy
            if parent_h > 0:
                node_bottom = node_y + h
                parent_bottom = parent_y + parent_h
                if abs(node_bottom - parent_bottom) < 100 and h < 200:
                    text_count = sum(1 for c in children if c.get('type') == 'TEXT')
                    if text_count >= max(len(children) * 0.3, 1):
                        return 'footer'

    # Priority 3.2: Tiny empty frame → icon
    if not children and w > 0 and w <= 48 and h > 0 and h <= 48:
        return f'icon-{sibling_index}'

    # Priority 3.5: Navigation detection
    if children:
        text_contents = get_text_children_content(children)
        text_count = len(text_contents)
        # Navigation: 4+ short text children → nav
        if text_count >= 4 and all(len(t) <= 20 for t in text_contents):
            return f'nav-{sibling_index}'

    # Priority 4: Child structure analysis
    if children:
        child_types = [c.get('type', '') for c in children]
        text_contents = get_text_children_content(children)
        has_image = 'IMAGE' in child_types or any(
            c.get('type') == 'RECTANGLE' and c.get('fills', [{}])[0].get('type') == 'IMAGE'
            for c in children if isinstance(c, dict)
        )
        has_text = 'TEXT' in child_types
        text_type_count = len([ct for ct in child_types if ct == 'TEXT'])
        has_button = any(
            c.get('type') == 'FRAME' and len(c.get('children', [])) <= 2
            and any(gc.get('type') == 'TEXT' for gc in c.get('children', []))
            for c in children if isinstance(c, dict)
        )

        if has_image and has_text and has_button:
            return f'card-{sibling_index}'
        if has_image and has_text:
            return f'media-{sibling_index}'

        # Small icon-like: tiny frame with 0-1 children
        if w > 0 and w <= 48 and h > 0 and h <= 48 and len(children) <= 1:
            return f'icon-{sibling_index}'

        # Button/Tab: small frame with 1-2 children, short text
        if h > 0 and h <= 70 and w > 0 and w < 300 and len(children) <= 2:
            if text_contents:
                slug = to_kebab(text_contents[0][:20])
                if slug:
                    return f'btn-{slug}'
            return f'btn-{sibling_index}'

        # Heading vs Content: check TEXT children length (Issue 14)
        if text_type_count <= 2 and len(text_contents) >= 1 and not has_image and len(children) <= 3:
            max_text_len = max(len(t) for t in text_contents)
            slug = to_kebab(text_contents[0][:30])
            if max_text_len > 50:
                # Long text = body content, not heading
                if slug:
                    return f'content-{slug}'
                return f'content-{sibling_index}'
            if slug:
                return f'heading-{slug}'
            return f'heading-{sibling_index}'

        # text-block with slug (improved from generic index)
        if has_text and len(children) <= 3:
            if text_contents:
                slug = to_kebab(text_contents[0][:30])
                if slug:
                    return f'text-block-{slug}'
            return f'text-block-{sibling_index}'

        if len(children) > 5:
            return f'container-{sibling_index}'
        return f'group-{sibling_index}'

    # Priority 5: Fallback
    type_prefix = node_type.lower().replace('_', '-')
    return f'{type_prefix}-{sibling_index}'

def collect_renames(node, parent=None, sibling_index=0, total_siblings=1, renames=None):
    \"\"\"Recursively collect rename candidates.\"\"\"
    if renames is None:
        renames = {}

    name = node.get('name', '')
    node_id = node.get('id', '')

    if UNNAMED_RE.match(name) and node_id:
        new_name = infer_name(node, parent, sibling_index, total_siblings)
        if new_name and new_name != name:
            renames[node_id] = {
                'old_name': name,
                'new_name': new_name,
                'type': node.get('type', ''),
                'inference_method': 'auto',
            }

    children = node.get('children', [])
    for i, child in enumerate(children):
        collect_renames(child, node, i, len(children), renames)

    return renames

try:
    with open(sys.argv[1], 'r') as f:
        data = json.load(f)

    root = get_root_node(data)
    resolve_absolute_coords(root)
    renames = collect_renames(root)

    output_file = sys.argv[2] if len(sys.argv) > 2 else ''

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
" "$1" "$OUTPUT_FILE"

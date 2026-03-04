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

# --- Constants ---

GRID_SNAP = 4  # px — gap/padding snap unit (figma-prepare.md)
SECTION_ROOT_WIDTH = 1440  # Figma page-level frame width


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
    return node.get('type') == 'FRAME' and abs(width - SECTION_ROOT_WIDTH) < 10


def to_kebab(text):
    """Convert text to kebab-case safe name.

    Non-ASCII-only text returns 'content' as a generic label.
    The downstream AI (via get_design_context) will assign final
    semantic names using the node's characters field.

    Issue 45: Extracted from generate-rename-map.sh to avoid duplication.
    Issue 47: Added CamelCase splitting (e.g. CamelCase → camel-case).
    """
    text = text.strip()
    if not text:
        return ''
    # Extract ASCII portion
    ascii_part = re.sub(r'[^\x00-\x7f]', '', text).strip()
    if not ascii_part:
        return 'content'
    # Split CamelCase before lowercasing (Issue 47)
    ascii_part = re.sub(r'([a-z])([A-Z])', r'\1 \2', ascii_part)
    ascii_part = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', ascii_part)
    # ASCII logic
    ascii_part = re.sub(r'[^\w\s-]', '', ascii_part.lower())
    ascii_part = re.sub(r'[\s_]+', '-', ascii_part)
    ascii_part = re.sub(r'-+', '-', ascii_part).strip('-')
    return ascii_part[:40] if ascii_part else 'content'

"""Shared utilities for figma-prepare scripts.

Common functions extracted to avoid duplication across
analyze-structure, detect-grouping-candidates, generate-rename-map,
infer-autolayout, prepare-sectioning-context, and enrich-metadata scripts.

Issue 24: resolve_absolute_coords was duplicated in 5 scripts.
"""

import json
import re


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
    """
    bbox = node.get('absoluteBoundingBox', {})
    abs_x = parent_x + bbox.get('x', 0)
    abs_y = parent_y + bbox.get('y', 0)
    bbox['x'] = abs_x
    bbox['y'] = abs_y
    node['absoluteBoundingBox'] = bbox
    for child in node.get('children', []):
        resolve_absolute_coords(child, abs_x, abs_y)


def get_bbox(node):
    """Get bounding box from node.

    Returns dict with short keys: x, y, w, h.
    """
    bbox = node.get('absoluteBoundingBox', {})
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

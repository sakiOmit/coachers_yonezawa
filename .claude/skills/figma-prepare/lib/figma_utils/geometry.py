"""Geometry and coordinate utilities for figma-prepare."""

import json

from .constants import GRID_SNAP


def yaml_str(value):
    """Safely encode a string for YAML double-quoted output.

    Uses json.dumps which properly escapes double quotes, backslashes,
    and other special characters. Output includes surrounding quotes.
    """
    return json.dumps(str(value), ensure_ascii=False)


def resolve_absolute_coords(node, parent_x=0, parent_y=0):
    """Convert parent-relative coordinates to absolute coordinates.

    get_metadata returns parent-relative x/y in absoluteBoundingBox.
    This function accumulates parent offsets to compute true absolute coords.

    Issue 67: Mutates in-place. A marker '_abs_resolved' prevents
    double-call from corrupting coordinates.

    Issue 272: When metadata comes from XML (Figma Dev Mode MCP), coordinates
    are already relative to the artboard root, NOT to the immediate parent.
    Detect this via '_coords_artboard_relative' flag (set by parse_figma_xml)
    and apply only the root offset once, without recursive accumulation.
    """
    if node.get('_abs_resolved'):
        return

    if node.get('_coords_artboard_relative'):
        # XML format: all coords are relative to artboard root.
        # Add root's page-level offset to all descendant nodes.
        _resolve_artboard_relative(node)
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


def _resolve_artboard_relative(root):
    """Resolve coordinates for artboard-relative XML metadata.

    Issue 272: In XML format, all nodes have x/y relative to the artboard root.
    We add the root's page-level x/y offset to every node to get true absolute
    coordinates, without recursive parent accumulation.

    Args:
        root: The root node with '_coords_artboard_relative' flag set.
    """
    root_bbox = root.get('absoluteBoundingBox') or {}
    root_x = root_bbox.get('x', 0)
    root_y = root_bbox.get('y', 0)

    # Root itself is already at page-level absolute coords
    root['_abs_resolved'] = True

    def _apply_offset(node):
        if node.get('_abs_resolved'):
            return
        bbox = node.get('absoluteBoundingBox') or {}
        bbox['x'] = root_x + bbox.get('x', 0)
        bbox['y'] = root_y + bbox.get('y', 0)
        node['absoluteBoundingBox'] = bbox
        node['_abs_resolved'] = True
        for child in node.get('children', []):
            _apply_offset(child)

    for child in root.get('children', []):
        _apply_offset(child)


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


def filter_visible_children(node):
    """Return children of *node* that are not explicitly hidden (visible != False)."""
    return [c for c in node.get('children', []) if c.get('visible') != False]


def sort_by_y(items):
    """Sort items by their absoluteBoundingBox Y coordinate."""
    return sorted(items, key=lambda c: get_bbox(c).get('y', 0))


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

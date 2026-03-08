"""Metadata I/O, node lookup, and structural predicates for figma-prepare.

This module provides the foundational metadata operations used throughout
the figma-prepare pipeline. Functions are organized into five categories:

Categories
----------
1. I/O & Parsing
   - parse_figma_xml        Parse Figma Dev Mode MCP XML to JSON node tree
   - load_metadata          Load metadata from file (JSON/XML auto-detect)

2. Node Lookup
   - get_root_node          Extract root node from various data formats
   - find_node_by_id        Recursive tree search by node ID

3. Structural Predicates
   - is_unnamed             Check if name matches auto-generated pattern
   - is_section_root        Detect section-level frames (width >= 90% of 1440px)
   - is_off_canvas          Check if node is outside the visible viewport

4. Content Extraction
   - get_text_children_content  Extract text content from TEXT children

5. Counting & Analysis
   - count_nested_flat          Count over-flat nodes inside section roots
   - _count_flat_descendants    Helper: count flat descendants in a subtree

Internal (not part of public API):
   - _TAG_TYPE_MAP              XML tag to Figma type mapping table
   - _apply_xml_attribute       Apply a parsed XML attribute to node/bbox
   - _FigmaXmlParser            Stateful XML parser class
"""

import json
from html import unescape

from .constants import (
    UNNAMED_RE,
    SECTION_ROOT_WIDTH,
    SECTION_ROOT_WIDTH_RATIO,
    FLAT_THRESHOLD,
    DEEP_NESTING_THRESHOLD,
    OFF_CANVAS_MARGIN,
)
from .geometry import filter_visible_children, get_bbox

__all__ = [
    # I/O & Parsing
    'parse_figma_xml',
    'load_metadata',
    # Node Lookup
    'get_root_node',
    'find_node_by_id',
    # Structural Predicates
    'is_unnamed',
    'is_section_root',
    'is_off_canvas',
    # Content Extraction
    'get_text_children_content',
    # Counting & Analysis
    'count_nested_flat',
]


# ============================================================
# I/O & Parsing
# ============================================================

_TAG_TYPE_MAP = {
    'frame': 'FRAME', 'text': 'TEXT', 'rectangle': 'RECTANGLE',
    'rounded-rectangle': 'RECTANGLE', 'ellipse': 'ELLIPSE',
    'vector': 'VECTOR', 'line': 'LINE', 'group': 'GROUP',
    'component': 'COMPONENT', 'instance': 'INSTANCE',
    'image': 'IMAGE', 'polygon': 'POLYGON', 'star': 'STAR',
    'section': 'SECTION', 'boolean-operation': 'BOOLEAN_OPERATION',
    'svg': 'VECTOR',
}


def _apply_xml_attribute(node, bbox, attr_name, attr_val):
    """Apply a parsed XML attribute to the node or bbox dict."""
    if attr_name == 'name':
        node['name'] = attr_val
    elif attr_name == 'id':
        node['id'] = attr_val
    elif attr_name in ('x', 'y', 'width', 'height'):
        try:
            bbox[attr_name] = float(attr_val)
        except ValueError:
            bbox[attr_name] = 0
    elif attr_name == 'visible' and attr_val == 'false':
        node['visible'] = False
    elif attr_name == 'characters':
        node['characters'] = attr_val


class _FigmaXmlParser:
    """Stateful XML parser for Figma Dev Mode MCP metadata."""

    def __init__(self, xml_str):
        self._s = xml_str
        self._pos = 0
        self._len = len(xml_str)

    def _skip_ws(self):
        s, length = self._s, self._len
        pos = self._pos
        while pos < length and s[pos] in ' \t\n\r':
            pos += 1
        self._pos = pos

    def _parse_attrs(self, node, bbox):
        """Parse attributes until self-close or tag-close. Returns True if self-closed."""
        s, length = self._s, self._len
        while self._pos < length:
            self._skip_ws()
            if self._pos >= length:
                break
            if s[self._pos] == '/' and self._pos + 1 < length and s[self._pos + 1] == '>':
                self._pos += 2
                return True
            if s[self._pos] == '>':
                self._pos += 1
                return False

            attr_start = self._pos
            while self._pos < length and s[self._pos] not in '= \t\n\r/>':
                self._pos += 1
            attr_name = s[attr_start:self._pos]

            self._skip_ws()
            if self._pos < length and s[self._pos] == '=':
                self._pos += 1
                self._skip_ws()
                if self._pos < length and s[self._pos] == '"':
                    self._pos += 1
                    val_start = self._pos
                    while self._pos < length and s[self._pos] != '"':
                        self._pos += 1
                    attr_val = unescape(s[val_start:self._pos])
                    self._pos += 1
                    _apply_xml_attribute(node, bbox, attr_name, attr_val)
        return False

    def _parse_children(self):
        """Parse child elements until closing tag. Returns list of children."""
        children = []
        while self._pos < self._len:
            self._skip_ws()
            if self._pos >= self._len:
                break
            if self._s[self._pos:self._pos + 2] == '</':
                end = self._s.find('>', self._pos)
                if end >= 0:
                    self._pos = end + 1
                break
            if self._s[self._pos] == '<':
                child = self._parse_tag()
                if child:
                    children.append(child)
            else:
                self._pos += 1
        return children

    def _parse_tag(self):
        """Parse a single XML tag with its attributes and children."""
        self._skip_ws()
        if self._pos >= self._len or self._s[self._pos] != '<':
            return None
        if self._s[self._pos:self._pos + 2] == '</':
            return None

        self._pos += 1  # skip <
        tag_start = self._pos
        while self._pos < self._len and self._s[self._pos] not in ' \t\n\r/>':
            self._pos += 1
        tag_name = self._s[tag_start:self._pos]

        node = {'type': _TAG_TYPE_MAP.get(tag_name, tag_name.upper())}
        bbox = {}

        self_closed = self._parse_attrs(node, bbox)
        if bbox:
            node['absoluteBoundingBox'] = bbox
        if self_closed:
            return node

        children = self._parse_children()
        if children:
            node['children'] = children

        return node

    def parse(self):
        """Parse the XML string and return the root node."""
        return self._parse_tag()


def parse_figma_xml(xml_str):
    """Parse Figma Dev Mode MCP XML metadata to JSON node tree.

    The Figma Dev Mode MCP (get_metadata) returns XML like:
      <frame id="2:5364" name="LP-PC5" x="-5542" y="348" width="1440" height="10770">
        <text id="2:5369" name="..." x="421" y="10425" width="101" height="23" />
        ...
      </frame>

    This converts to the JSON format expected by analyze-structure.sh:
      {"type": "FRAME", "id": "2:5364", "name": "LP-PC5",
       "absoluteBoundingBox": {"x": -5542, "y": 348, "width": 1440, "height": 10770},
       "children": [...]}

    Issue 272: Sets '_coords_artboard_relative' flag on root to signal that
    child coordinates are relative to the artboard root, not to immediate parents.
    This prevents resolve_absolute_coords() from double-accumulating offsets.
    """
    root = _FigmaXmlParser(xml_str).parse()
    if root is not None:
        root['_coords_artboard_relative'] = True
    return root


def load_metadata(file_path):
    """Load Figma metadata from file, auto-detecting format.

    Supports:
    - JSON with 'document'/'node'/'nodes' key (existing format)
    - MCP response wrapper: [{"type": "text", "text": "<frame ...>"}]
    - Raw XML string (Figma Dev Mode MCP get_metadata output)

    Returns: dict with 'document' key containing the root node.
    """
    with open(file_path, 'r') as f:
        content = f.read().strip()

    # Try JSON first
    if content.startswith('{') or content.startswith('['):
        data = json.loads(content)

        # MCP response wrapper: [{"type": "text", "text": "<frame ...>"}]
        if isinstance(data, list) and data and isinstance(data[0], dict) and 'text' in data[0]:
            xml_text = data[0]['text']
            if xml_text.strip().startswith('<'):
                root = parse_figma_xml(xml_text)
                return {'document': root}

        # Already JSON node format
        return data

    # Raw XML
    if content.startswith('<'):
        root = parse_figma_xml(content)
        return {'document': root}

    raise ValueError(f"Unknown metadata format in {file_path}")


# ============================================================
# Node Lookup
# ============================================================

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


def find_node_by_id(root, node_id):
    """Recursively search the tree and return the node with the given ID.

    Returns None if no node with the specified ID is found.

    Issue 194: Used by generate-nested-grouping-context.sh to locate
    section nodes within the metadata tree.
    """
    if root.get('id') == node_id:
        return root
    for child in root.get('children', []):
        found = find_node_by_id(child, node_id)
        if found:
            return found
    return None


# ============================================================
# Structural Predicates
# ============================================================

def is_unnamed(name):
    """Check if a node name matches unnamed (auto-generated) pattern."""
    return bool(UNNAMED_RE.match(name))


def is_section_root(node):
    """Detect section-level frames (width >= 90% of 1440px).

    Issue 53: Extracted from analyze-structure.sh to share with other scripts.
    Issue 191: Relaxed width check from |width - 1440| < 10 to width >= 1296
    to catch oversized footer wrappers (e.g. 2433px wide Group).

    Args:
        node: Figma node dict.

    Returns:
        bool: True if node is a section root frame.
    """
    bbox = node.get('absoluteBoundingBox') or {}
    width = bbox.get('width', 0)
    # Issue 116: Include COMPONENT/INSTANCE/SECTION types as section roots
    # (consistent with Issue 69/72 type extensions in other scripts)
    # Issue 191: Relaxed width check — width >= SECTION_ROOT_WIDTH * 0.9 (1296px)
    # catches both exact-match (~1440) and oversized wrappers (e.g. 2433px)
    return node.get('type') in ('FRAME', 'COMPONENT', 'INSTANCE', 'SECTION') and width >= SECTION_ROOT_WIDTH * SECTION_ROOT_WIDTH_RATIO


def is_off_canvas(node, page_width, root_x=0, root_y=0):
    """Check if a node is positioned completely outside the viewport.

    An element is considered off-canvas if:
    - Its left edge (x) is beyond page_width * OFF_CANVAS_MARGIN, OR
    - Its right edge (x + w) is less than 0 (completely to the left)

    Coordinates are evaluated relative to root_x, so artboards placed
    at arbitrary canvas positions (e.g., x=-5542) work correctly.

    These are typically unused assets or elements placed outside the
    visible design area.

    Issue 182: Elements outside viewport should not affect scoring or grouping.

    Args:
        node: Figma node dict.
        page_width: Width of the page/artboard (typically 1440px).
        root_x: X coordinate of the root artboard (for offset correction).
        root_y: Y coordinate of the root artboard (for offset correction, Issue 265).

    Returns:
        bool: True if the node is completely off-canvas.
    """
    if page_width <= 0:
        return False
    bb = get_bbox(node)
    if not bb or bb['w'] == 0:
        return False
    # Convert to root-relative coordinate
    rel_x = bb['x'] - root_x
    # Right edge is left of viewport
    if rel_x + bb['w'] < 0:
        return True
    # Left edge is beyond off-canvas margin
    if rel_x > page_width * OFF_CANVAS_MARGIN:
        return True
    return False


# ============================================================
# Content Extraction
# ============================================================

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


# ============================================================
# Counting & Analysis
# ============================================================

def count_nested_flat(node, threshold=FLAT_THRESHOLD):
    """Count FRAME/GROUP nodes with > threshold visible children, below section roots only.

    Issue 228: Captures internal structural quality beyond section-root flatness.
    Issue 231: Only counts within section root boundaries. Section roots themselves
    are excluded (they are counted by the flat_sections metric). Nodes above
    section roots are not counted either.

    Args:
        node: Figma node dict.
        threshold: Maximum visible children before a node is considered flat.

    Returns:
        int: Number of nodes with > threshold visible children inside section roots.
    """
    count = 0
    children = filter_visible_children(node)

    if is_section_root(node):
        # Inside a section root: count flat descendants (but not the root itself)
        count += _count_flat_descendants(node, threshold)
    else:
        # Above section roots: recurse to find section roots
        for child in children:
            count += count_nested_flat(child, threshold)

    return count


def _count_flat_descendants(node, threshold=FLAT_THRESHOLD):
    """Count flat nodes within a subtree (excluding the root node itself).

    Issue 231: Helper for count_nested_flat. Walks all descendants and counts
    FRAME/GROUP/COMPONENT/INSTANCE/SECTION nodes with > threshold visible children.
    Section roots encountered as children are skipped (not counted) but their
    subtrees are still recursed into, since nested section roots are handled
    by the flat_sections metric.

    Args:
        node: Figma node dict (subtree root, not counted itself).
        threshold: Maximum visible children before a node is considered flat.

    Returns:
        int: Number of flat descendant nodes.
    """
    count = 0
    children = filter_visible_children(node)
    for child in children:
        if is_section_root(child):
            # Skip counting this child (flat_sections handles it),
            # but recurse into its subtree
            count += _count_flat_descendants(child, threshold)
        else:
            child_children = filter_visible_children(child)
            if child.get('type') in ('FRAME', 'GROUP', 'COMPONENT', 'INSTANCE', 'SECTION') and len(child_children) > threshold:
                count += 1
            count += _count_flat_descendants(child, threshold)
    return count

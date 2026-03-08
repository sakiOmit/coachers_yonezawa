"""Tests for resolve_absolute_coords Issue #272 fix.

Verifies that resolve_absolute_coords correctly handles both:
- Parent-relative coordinates (Figma API JSON format)
- Artboard-relative coordinates (XML metadata format)
"""
import pytest

from figma_utils import resolve_absolute_coords, parse_figma_xml


# ============================================================
# XML (artboard-relative) coordinates - Issue #272
# ============================================================
class TestArtboardRelativeCoords:
    """Test that XML-parsed data with artboard-relative coords is handled correctly."""

    def test_xml_nested_no_double_accumulation(self):
        """Core bug: nested children should not double-add parent offset."""
        root = {
            'type': 'FRAME',
            '_coords_artboard_relative': True,
            'absoluteBoundingBox': {'x': 8544, 'y': 1285, 'width': 1440, 'height': 5851},
            'children': [
                {
                    'type': 'FRAME',
                    'absoluteBoundingBox': {'x': 792, 'y': 2450, 'width': 436, 'height': 66},
                    'children': [
                        {
                            'type': 'RECTANGLE',
                            'absoluteBoundingBox': {'x': 792, 'y': 2450, 'width': 436, 'height': 66},
                        },
                        {
                            'type': 'TEXT',
                            'absoluteBoundingBox': {'x': 813, 'y': 2463, 'width': 177, 'height': 40},
                        },
                    ],
                },
            ],
        }
        resolve_absolute_coords(root)

        # Root stays at page-level absolute
        assert root['absoluteBoundingBox']['x'] == 8544
        assert root['absoluteBoundingBox']['y'] == 1285

        # Level 1 child: root_x + child_x = 8544 + 792 = 9336
        child = root['children'][0]
        assert child['absoluteBoundingBox']['x'] == 8544 + 792
        assert child['absoluteBoundingBox']['y'] == 1285 + 2450

        # Level 2 grandchild: root_x + gc_x = 8544 + 792 = 9336 (NOT 8544 + 9336 + 792)
        gc_rect = child['children'][0]
        assert gc_rect['absoluteBoundingBox']['x'] == 8544 + 792
        assert gc_rect['absoluteBoundingBox']['y'] == 1285 + 2450

        gc_text = child['children'][1]
        assert gc_text['absoluteBoundingBox']['x'] == 8544 + 813
        assert gc_text['absoluteBoundingBox']['y'] == 1285 + 2463

    def test_xml_3_levels_deep(self):
        """3 levels of nesting should still only add root offset once."""
        root = {
            'type': 'FRAME',
            '_coords_artboard_relative': True,
            'absoluteBoundingBox': {'x': 100, 'y': 200, 'width': 1440, 'height': 5000},
            'children': [{
                'type': 'FRAME',
                'absoluteBoundingBox': {'x': 50, 'y': 100, 'width': 500, 'height': 300},
                'children': [{
                    'type': 'FRAME',
                    'absoluteBoundingBox': {'x': 60, 'y': 120, 'width': 200, 'height': 100},
                    'children': [{
                        'type': 'TEXT',
                        'absoluteBoundingBox': {'x': 70, 'y': 130, 'width': 100, 'height': 20},
                    }],
                }],
            }],
        }
        resolve_absolute_coords(root)

        assert root['absoluteBoundingBox']['x'] == 100
        child = root['children'][0]
        assert child['absoluteBoundingBox']['x'] == 150  # 100 + 50
        gc = child['children'][0]
        assert gc['absoluteBoundingBox']['x'] == 160  # 100 + 60
        ggc = gc['children'][0]
        assert ggc['absoluteBoundingBox']['x'] == 170  # 100 + 70

    def test_xml_negative_root_offset(self):
        """Negative root x/y (common in Figma pages) should work correctly."""
        root = {
            'type': 'FRAME',
            '_coords_artboard_relative': True,
            'absoluteBoundingBox': {'x': -5542, 'y': 348, 'width': 1440, 'height': 10770},
            'children': [{
                'type': 'TEXT',
                'absoluteBoundingBox': {'x': 421, 'y': 10425, 'width': 101, 'height': 23},
            }],
        }
        resolve_absolute_coords(root)

        assert root['absoluteBoundingBox']['x'] == -5542
        child = root['children'][0]
        assert child['absoluteBoundingBox']['x'] == -5542 + 421  # -5121
        assert child['absoluteBoundingBox']['y'] == 348 + 10425  # 10773

    def test_xml_zero_root_offset(self):
        """Root at (0,0) should still work correctly."""
        root = {
            'type': 'FRAME',
            '_coords_artboard_relative': True,
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 5000},
            'children': [{
                'type': 'FRAME',
                'absoluteBoundingBox': {'x': 100, 'y': 200, 'width': 400, 'height': 300},
                'children': [{
                    'type': 'TEXT',
                    'absoluteBoundingBox': {'x': 150, 'y': 250, 'width': 100, 'height': 20},
                }],
            }],
        }
        resolve_absolute_coords(root)

        child = root['children'][0]
        assert child['absoluteBoundingBox']['x'] == 100  # 0 + 100
        gc = child['children'][0]
        assert gc['absoluteBoundingBox']['x'] == 150  # 0 + 150 (not 100 + 150)

    def test_xml_double_call_guard(self):
        """Calling resolve_absolute_coords twice should not corrupt data."""
        root = {
            'type': 'FRAME',
            '_coords_artboard_relative': True,
            'absoluteBoundingBox': {'x': 100, 'y': 200, 'width': 1440, 'height': 5000},
            'children': [{
                'type': 'TEXT',
                'absoluteBoundingBox': {'x': 50, 'y': 60, 'width': 100, 'height': 20},
            }],
        }
        resolve_absolute_coords(root)
        child = root['children'][0]
        assert child['absoluteBoundingBox']['x'] == 150

        # Second call should be a no-op
        resolve_absolute_coords(root)
        assert child['absoluteBoundingBox']['x'] == 150

    def test_xml_missing_bbox(self):
        """Nodes with missing absoluteBoundingBox should get one with root offset."""
        root = {
            'type': 'FRAME',
            '_coords_artboard_relative': True,
            'absoluteBoundingBox': {'x': 100, 'y': 200, 'width': 1440, 'height': 5000},
            'children': [{
                'type': 'TEXT',
                # Missing absoluteBoundingBox
            }],
        }
        resolve_absolute_coords(root)

        child = root['children'][0]
        assert child['absoluteBoundingBox']['x'] == 100  # root_x + 0
        assert child['absoluteBoundingBox']['y'] == 200  # root_y + 0


# ============================================================
# JSON (parent-relative) coordinates - existing behavior
# ============================================================
class TestParentRelativeCoords:
    """Ensure existing parent-relative behavior is preserved for JSON data."""

    def test_json_accumulation_unchanged(self):
        """Standard parent-relative accumulation must still work."""
        node = {
            'absoluteBoundingBox': {'x': 10, 'y': 20, 'width': 100, 'height': 100},
            'children': [{
                'absoluteBoundingBox': {'x': 5, 'y': 5, 'width': 50, 'height': 50},
                'children': [{
                    'absoluteBoundingBox': {'x': 2, 'y': 3, 'width': 10, 'height': 10},
                    'children': [],
                }],
            }],
        }
        resolve_absolute_coords(node)

        assert node['absoluteBoundingBox']['x'] == 10
        child = node['children'][0]
        assert child['absoluteBoundingBox']['x'] == 15  # 10 + 5
        assert child['absoluteBoundingBox']['y'] == 25  # 20 + 5
        gc = child['children'][0]
        assert gc['absoluteBoundingBox']['x'] == 17  # 15 + 2
        assert gc['absoluteBoundingBox']['y'] == 28  # 25 + 3

    def test_json_with_parent_offset(self):
        """Parent offset parameter should still accumulate."""
        leaf = {'absoluteBoundingBox': {'x': 5, 'y': 10, 'width': 20, 'height': 30}}
        resolve_absolute_coords(leaf, parent_x=100, parent_y=200)
        assert leaf['absoluteBoundingBox']['x'] == 105
        assert leaf['absoluteBoundingBox']['y'] == 210

    def test_json_double_call_guard(self):
        """Double-call guard still works for JSON data."""
        node = {
            'absoluteBoundingBox': {'x': 10, 'y': 20, 'width': 100, 'height': 100},
            'children': [{
                'absoluteBoundingBox': {'x': 5, 'y': 5, 'width': 50, 'height': 50},
                'children': [],
            }],
        }
        resolve_absolute_coords(node)
        child = node['children'][0]
        assert child['absoluteBoundingBox']['x'] == 15

        resolve_absolute_coords(node)
        assert child['absoluteBoundingBox']['x'] == 15


# ============================================================
# parse_figma_xml integration - flag setting
# ============================================================
class TestParseFigmaXmlFlag:
    """Verify that parse_figma_xml sets the artboard-relative flag."""

    def test_flag_set_on_root(self):
        xml = '<frame id="1:1" name="Test" x="100" y="200" width="1440" height="5000" />'
        root = parse_figma_xml(xml)
        assert root is not None
        assert root.get('_coords_artboard_relative') is True

    def test_flag_with_children(self):
        xml = (
            '<frame id="1:1" name="Test" x="100" y="200" width="1440" height="5000">'
            '<text id="1:2" name="Hello" x="50" y="60" width="100" height="20" />'
            '</frame>'
        )
        root = parse_figma_xml(xml)
        assert root.get('_coords_artboard_relative') is True
        # Children should NOT have the flag
        assert root['children'][0].get('_coords_artboard_relative') is None

    def test_end_to_end_xml_resolve(self):
        """Full pipeline: parse XML -> resolve -> verify absolute coords."""
        xml = (
            '<frame id="1:1" name="Root" x="8544" y="1285" width="1440" height="5851">'
            '<frame id="1:2" name="Group" x="792" y="2450" width="436" height="66">'
            '<text id="1:3" name="Label" x="813" y="2463" width="177" height="40" />'
            '</frame>'
            '</frame>'
        )
        root = parse_figma_xml(xml)
        resolve_absolute_coords(root)

        # Root at page-level
        assert root['absoluteBoundingBox']['x'] == 8544

        # Nested group: 8544 + 792 = 9336
        group = root['children'][0]
        assert group['absoluteBoundingBox']['x'] == 9336
        assert group['absoluteBoundingBox']['y'] == 1285 + 2450

        # Deeply nested text: 8544 + 813 = 9357 (NOT 9336 + 813)
        text = group['children'][0]
        assert text['absoluteBoundingBox']['x'] == 8544 + 813
        assert text['absoluteBoundingBox']['y'] == 1285 + 2463

"""Tests for geometry utilities: resolve_absolute_coords, _resolve_artboard_relative.

Issue 272: Tests for XML artboard-relative coordinate resolution.
"""
import copy
import pytest

from figma_utils import resolve_absolute_coords, parse_figma_xml, get_bbox
from figma_utils.geometry import _resolve_artboard_relative


# ============================================================
# Fixtures
# ============================================================

def _make_json_tree():
    """Create a standard JSON-format tree (parent-relative coords).

    Structure: Root(100,200) -> Section(0,0) -> Group(50,100) -> Text(10,20)
    Expected absolute coords after resolve:
      Root:    (100, 200)
      Section: (100, 200)  = 100+0, 200+0
      Group:   (150, 300)  = 100+50, 200+100
      Text:    (160, 320)  = 150+10, 300+20
    """
    return {
        'type': 'FRAME', 'name': 'Root',
        'absoluteBoundingBox': {'x': 100, 'y': 200, 'width': 1440, 'height': 5000},
        'children': [
            {
                'type': 'FRAME', 'name': 'Section',
                'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 2000},
                'children': [
                    {
                        'type': 'GROUP', 'name': 'Group',
                        'absoluteBoundingBox': {'x': 50, 'y': 100, 'width': 300, 'height': 400},
                        'children': [
                            {
                                'type': 'TEXT', 'name': 'Text',
                                'absoluteBoundingBox': {'x': 10, 'y': 20, 'width': 100, 'height': 30},
                            },
                        ],
                    },
                ],
            },
        ],
    }


def _make_xml_tree():
    """Create an XML-format tree (artboard-relative coords).

    All children coords are relative to root, NOT to immediate parent.
    Root is at page-level (8544, 348).
    Section at artboard-relative (0, 0) -> absolute (8544, 348)
    Group at artboard-relative (50, 100) -> absolute (8594, 448)
    Text at artboard-relative (60, 120) -> absolute (8604, 468)
    """
    return {
        'type': 'FRAME', 'name': 'LP-PC5',
        '_coords_artboard_relative': True,
        'absoluteBoundingBox': {'x': 8544, 'y': 348, 'width': 1440, 'height': 10770},
        'children': [
            {
                'type': 'FRAME', 'name': 'Section',
                'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 2000},
                'children': [
                    {
                        'type': 'GROUP', 'name': 'Group',
                        'absoluteBoundingBox': {'x': 50, 'y': 100, 'width': 300, 'height': 400},
                        'children': [
                            {
                                'type': 'TEXT', 'name': 'Text',
                                'absoluteBoundingBox': {'x': 60, 'y': 120, 'width': 100, 'height': 30},
                            },
                        ],
                    },
                ],
            },
        ],
    }


def _make_xml_negative_root():
    """XML tree with negative root coordinates (common in Figma)."""
    return {
        'type': 'FRAME', 'name': 'LP-PC5',
        '_coords_artboard_relative': True,
        'absoluteBoundingBox': {'x': -5542, 'y': 348, 'width': 1440, 'height': 10770},
        'children': [
            {
                'type': 'FRAME', 'name': 'hero',
                'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 800},
            },
            {
                'type': 'TEXT', 'name': 'heading',
                'absoluteBoundingBox': {'x': 421, 'y': 10425, 'width': 101, 'height': 23},
            },
        ],
    }


# ============================================================
# Test: JSON format (existing behavior, regression)
# ============================================================


class TestResolveAbsoluteCoordsJSON:
    """Regression tests for standard JSON parent-relative coords."""

    def test_basic_accumulation(self):
        tree = _make_json_tree()
        resolve_absolute_coords(tree)

        # Root stays at its own position
        assert tree['absoluteBoundingBox']['x'] == 100
        assert tree['absoluteBoundingBox']['y'] == 200

        section = tree['children'][0]
        assert section['absoluteBoundingBox']['x'] == 100  # 100 + 0
        assert section['absoluteBoundingBox']['y'] == 200  # 200 + 0

        group = section['children'][0]
        assert group['absoluteBoundingBox']['x'] == 150  # 100 + 50
        assert group['absoluteBoundingBox']['y'] == 300  # 200 + 100

        text = group['children'][0]
        assert text['absoluteBoundingBox']['x'] == 160  # 150 + 10
        assert text['absoluteBoundingBox']['y'] == 320  # 300 + 20

    def test_no_flag_set(self):
        """JSON nodes should NOT have _coords_artboard_relative."""
        tree = _make_json_tree()
        assert '_coords_artboard_relative' not in tree

    def test_double_call_protection(self):
        """Calling resolve_absolute_coords twice should not corrupt coords."""
        tree = _make_json_tree()
        resolve_absolute_coords(tree)
        expected_x = tree['children'][0]['children'][0]['absoluteBoundingBox']['x']

        resolve_absolute_coords(tree)
        assert tree['children'][0]['children'][0]['absoluteBoundingBox']['x'] == expected_x


# ============================================================
# Test: XML format (Issue 272 - artboard-relative)
# ============================================================


class TestResolveAbsoluteCoordsXML:
    """Tests for XML artboard-relative coordinate resolution (Issue 272)."""

    def test_root_unchanged(self):
        """Root node coords should remain at page-level absolute."""
        tree = _make_xml_tree()
        resolve_absolute_coords(tree)

        assert tree['absoluteBoundingBox']['x'] == 8544
        assert tree['absoluteBoundingBox']['y'] == 348

    def test_child_gets_root_offset(self):
        """Direct children: absolute = root_offset + artboard_relative."""
        tree = _make_xml_tree()
        resolve_absolute_coords(tree)

        section = tree['children'][0]
        assert section['absoluteBoundingBox']['x'] == 8544  # 8544 + 0
        assert section['absoluteBoundingBox']['y'] == 348   # 348 + 0

    def test_nested_child_gets_root_offset_only(self):
        """Nested children should get root offset, NOT accumulated parent offsets."""
        tree = _make_xml_tree()
        resolve_absolute_coords(tree)

        group = tree['children'][0]['children'][0]
        # With XML format: absolute = root(8544,348) + artboard_relative(50,100)
        assert group['absoluteBoundingBox']['x'] == 8594  # 8544 + 50
        assert group['absoluteBoundingBox']['y'] == 448   # 348 + 100

    def test_deeply_nested_no_accumulation(self):
        """Deep nesting: offset is root-only, no parent accumulation."""
        tree = _make_xml_tree()
        resolve_absolute_coords(tree)

        text = tree['children'][0]['children'][0]['children'][0]
        # With XML format: absolute = root(8544,348) + artboard_relative(60,120)
        assert text['absoluteBoundingBox']['x'] == 8604  # 8544 + 60
        assert text['absoluteBoundingBox']['y'] == 468   # 348 + 120

    def test_negative_root_coords(self):
        """Root at negative page coords (common in Figma)."""
        tree = _make_xml_negative_root()
        resolve_absolute_coords(tree)

        # Root stays at negative page-level position
        assert tree['absoluteBoundingBox']['x'] == -5542
        assert tree['absoluteBoundingBox']['y'] == 348

        hero = tree['children'][0]
        assert hero['absoluteBoundingBox']['x'] == -5542  # -5542 + 0
        assert hero['absoluteBoundingBox']['y'] == 348    # 348 + 0

        heading = tree['children'][1]
        assert heading['absoluteBoundingBox']['x'] == -5121  # -5542 + 421
        assert heading['absoluteBoundingBox']['y'] == 10773  # 348 + 10425

    def test_double_call_protection(self):
        """Double resolve should not corrupt XML coords."""
        tree = _make_xml_tree()
        resolve_absolute_coords(tree)
        group = tree['children'][0]['children'][0]
        expected_x = group['absoluteBoundingBox']['x']

        resolve_absolute_coords(tree)
        assert group['absoluteBoundingBox']['x'] == expected_x

    def test_abs_resolved_flag_set(self):
        """All nodes should be marked _abs_resolved after resolve."""
        tree = _make_xml_tree()
        resolve_absolute_coords(tree)

        assert tree.get('_abs_resolved') is True
        assert tree['children'][0].get('_abs_resolved') is True
        assert tree['children'][0]['children'][0].get('_abs_resolved') is True

    def test_width_height_preserved(self):
        """Width and height should not be modified by resolve."""
        tree = _make_xml_tree()
        resolve_absolute_coords(tree)

        assert tree['absoluteBoundingBox']['width'] == 1440
        assert tree['absoluteBoundingBox']['height'] == 10770
        section = tree['children'][0]
        assert section['absoluteBoundingBox']['width'] == 1440
        assert section['absoluteBoundingBox']['height'] == 2000

    def test_empty_children(self):
        """Node with no children should resolve without error."""
        tree = {
            'type': 'FRAME', 'name': 'Root',
            '_coords_artboard_relative': True,
            'absoluteBoundingBox': {'x': 100, 'y': 200, 'width': 500, 'height': 300},
        }
        resolve_absolute_coords(tree)
        assert tree['absoluteBoundingBox']['x'] == 100
        assert tree.get('_abs_resolved') is True

    def test_no_bbox_child(self):
        """Child without absoluteBoundingBox should get bbox set to root offset."""
        tree = {
            'type': 'FRAME', 'name': 'Root',
            '_coords_artboard_relative': True,
            'absoluteBoundingBox': {'x': 100, 'y': 200, 'width': 500, 'height': 300},
            'children': [
                {'type': 'TEXT', 'name': 'NoBox'},
            ],
        }
        resolve_absolute_coords(tree)
        child = tree['children'][0]
        # No bbox means x=0, y=0 relative -> absolute = root offset
        assert child['absoluteBoundingBox']['x'] == 100
        assert child['absoluteBoundingBox']['y'] == 200


# ============================================================
# Test: _resolve_artboard_relative directly
# ============================================================


class TestResolveArtboardRelative:
    """Direct tests for the _resolve_artboard_relative helper."""

    def test_direct_call(self):
        tree = _make_xml_tree()
        _resolve_artboard_relative(tree)

        text = tree['children'][0]['children'][0]['children'][0]
        assert text['absoluteBoundingBox']['x'] == 8604
        assert text['absoluteBoundingBox']['y'] == 468

    def test_root_with_zero_offset(self):
        """Root at origin (0,0) should pass through coords unchanged."""
        tree = {
            'type': 'FRAME',
            '_coords_artboard_relative': True,
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 1000},
            'children': [
                {
                    'type': 'TEXT',
                    'absoluteBoundingBox': {'x': 100, 'y': 200, 'width': 50, 'height': 20},
                },
            ],
        }
        _resolve_artboard_relative(tree)
        assert tree['children'][0]['absoluteBoundingBox']['x'] == 100
        assert tree['children'][0]['absoluteBoundingBox']['y'] == 200


# ============================================================
# Test: parse_figma_xml sets the flag
# ============================================================


class TestParseFigmaXmlFlag:
    """Verify parse_figma_xml sets _coords_artboard_relative flag."""

    def test_flag_set_on_root(self):
        xml = '<frame id="1:1" name="Root" x="100" y="200" width="1440" height="5000"></frame>'
        root = parse_figma_xml(xml)
        assert root is not None
        assert root.get('_coords_artboard_relative') is True

    def test_flag_not_on_children(self):
        xml = '''<frame id="1:1" name="Root" x="100" y="200" width="1440" height="5000">
            <text id="1:2" name="T" x="10" y="20" width="50" height="30" />
        </frame>'''
        root = parse_figma_xml(xml)
        child = root['children'][0]
        assert '_coords_artboard_relative' not in child

    def test_self_closing_tag(self):
        xml = '<text id="1:1" name="Solo" x="0" y="0" width="100" height="20" />'
        root = parse_figma_xml(xml)
        assert root.get('_coords_artboard_relative') is True

    def test_end_to_end_xml_resolve(self):
        """Full pipeline: parse XML -> resolve -> check absolute coords."""
        xml = '''<frame id="0:1" name="Page" x="8544" y="348" width="1440" height="10770">
            <frame id="1:1" name="Section" x="0" y="0" width="1440" height="2000">
                <text id="1:2" name="Heading" x="100" y="50" width="200" height="30" />
            </frame>
            <frame id="2:1" name="Footer" x="0" y="10000" width="1440" height="770">
                <text id="2:2" name="Copyright" x="600" y="10700" width="240" height="20" />
            </frame>
        </frame>'''

        root = parse_figma_xml(xml)
        resolve_absolute_coords(root)

        # Root at page-level
        assert root['absoluteBoundingBox']['x'] == 8544
        assert root['absoluteBoundingBox']['y'] == 348

        # Section: 8544 + 0, 348 + 0
        section = root['children'][0]
        assert section['absoluteBoundingBox']['x'] == 8544
        assert section['absoluteBoundingBox']['y'] == 348

        # Heading: 8544 + 100, 348 + 50
        heading = section['children'][0]
        assert heading['absoluteBoundingBox']['x'] == 8644
        assert heading['absoluteBoundingBox']['y'] == 398

        # Footer: 8544 + 0, 348 + 10000
        footer = root['children'][1]
        assert footer['absoluteBoundingBox']['x'] == 8544
        assert footer['absoluteBoundingBox']['y'] == 10348

        # Copyright: 8544 + 600, 348 + 10700
        copyright_text = footer['children'][0]
        assert copyright_text['absoluteBoundingBox']['x'] == 9144
        assert copyright_text['absoluteBoundingBox']['y'] == 11048


# ============================================================
# Test: Contrast - JSON would double-accumulate (proving the bug)
# ============================================================


class TestContrastXMLvsJSON:
    """Demonstrate that without the flag, coords would be wrong."""

    def test_json_accumulates_but_xml_does_not(self):
        """Same tree structure: JSON accumulates, XML adds root offset only."""
        # JSON format: parent-relative
        json_tree = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 100, 'y': 200, 'width': 1440, 'height': 1000},
            'children': [{
                'type': 'FRAME',
                'absoluteBoundingBox': {'x': 50, 'y': 50, 'width': 200, 'height': 200},
                'children': [{
                    'type': 'TEXT',
                    'absoluteBoundingBox': {'x': 10, 'y': 10, 'width': 50, 'height': 20},
                }],
            }],
        }

        # XML format: artboard-relative (same numbers but different meaning)
        xml_tree = copy.deepcopy(json_tree)
        xml_tree['_coords_artboard_relative'] = True

        resolve_absolute_coords(json_tree)
        resolve_absolute_coords(xml_tree)

        # JSON: Text = 100+50+10 = 160
        json_text = json_tree['children'][0]['children'][0]
        assert json_text['absoluteBoundingBox']['x'] == 160

        # XML: Text = 100+10 = 110 (root offset + artboard-relative, no parent accumulation)
        xml_text = xml_tree['children'][0]['children'][0]
        assert xml_text['absoluteBoundingBox']['x'] == 110

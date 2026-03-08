"""Tests for metadata I/O and parsing: find_node_by_id, parse_figma_xml, load_metadata."""
import json
import os
import tempfile
import pytest

from helpers import run_script, write_fixture

from figma_utils import (
    load_metadata,
    parse_figma_xml,
)

try:
    from figma_utils import find_node_by_id
    HAS_FIND_NODE = True
except ImportError:
    HAS_FIND_NODE = False


# ============================================================
# Issue 194 Phase 3: find_node_by_id tests
# ============================================================


@pytest.mark.skipif(not HAS_FIND_NODE, reason="find_node_by_id not yet implemented")
class TestFindNodeById:
    """Tests for find_node_by_id() tree search utility (Issue 194 Phase 3)."""

    TREE = {
        "id": "0:1", "name": "Root", "type": "FRAME",
        "children": [
            {
                "id": "1:1", "name": "Section A", "type": "FRAME",
                "children": [
                    {"id": "1:10", "name": "Heading", "type": "TEXT", "children": []},
                    {"id": "1:11", "name": "Body", "type": "TEXT", "children": []},
                ],
            },
            {
                "id": "1:2", "name": "Section B", "type": "FRAME",
                "children": [
                    {
                        "id": "1:20", "name": "Card", "type": "FRAME",
                        "children": [
                            {"id": "1:200", "name": "Image", "type": "RECTANGLE",
                             "children": []},
                        ],
                    },
                ],
            },
        ],
    }

    def test_find_root(self):
        """Root node itself is found by its ID."""
        result = find_node_by_id(self.TREE, "0:1")
        assert result is not None
        assert result["id"] == "0:1"
        assert result["name"] == "Root"

    def test_find_nested(self):
        """Direct child node is found."""
        result = find_node_by_id(self.TREE, "1:1")
        assert result is not None
        assert result["name"] == "Section A"

    def test_find_grandchild(self):
        """Grandchild (depth=2) is found."""
        result = find_node_by_id(self.TREE, "1:10")
        assert result is not None
        assert result["name"] == "Heading"

    def test_not_found(self):
        """Non-existent ID returns None."""
        result = find_node_by_id(self.TREE, "99:99")
        assert result is None

    def test_deep_nesting(self):
        """Deeply nested node (5 levels) is found."""
        deep_tree = {"id": "L0", "children": [
            {"id": "L1", "children": [
                {"id": "L2", "children": [
                    {"id": "L3", "children": [
                        {"id": "L4", "children": [
                            {"id": "L5", "name": "deepest", "children": []}
                        ]}
                    ]}
                ]}
            ]}
        ]}
        result = find_node_by_id(deep_tree, "L5")
        assert result is not None
        assert result["name"] == "deepest"

    def test_empty_tree(self):
        """Root with no children -- search for non-root returns None."""
        root_only = {"id": "0:1", "name": "Alone"}
        assert find_node_by_id(root_only, "0:1") is not None
        assert find_node_by_id(root_only, "1:1") is None

    def test_find_leaf_in_nested_branch(self):
        """Leaf node in a nested branch (depth=3) is found."""
        result = find_node_by_id(self.TREE, "1:200")
        assert result is not None
        assert result["name"] == "Image"


# ==============================================================
# parse_figma_xml / load_metadata tests
# ==============================================================


class TestParseFigmaXml:
    """Tests for parse_figma_xml — Figma Dev Mode MCP XML parser."""

    def test_basic_frame(self):
        xml = '<frame id="1:2" name="Hero" x="0" y="0" width="1440" height="800" />'
        node = parse_figma_xml(xml)
        assert node["type"] == "FRAME"
        assert node["id"] == "1:2"
        assert node["name"] == "Hero"
        assert node["absoluteBoundingBox"]["width"] == 1440
        assert node["absoluteBoundingBox"]["height"] == 800

    def test_nested_children(self):
        xml = '''<frame id="1:1" name="Root" x="0" y="0" width="1440" height="900">
            <text id="1:2" name="Title" x="10" y="20" width="100" height="30" />
            <rectangle id="1:3" name="BG" x="0" y="0" width="1440" height="900" />
        </frame>'''
        node = parse_figma_xml(xml)
        assert len(node["children"]) == 2
        assert node["children"][0]["type"] == "TEXT"
        assert node["children"][1]["type"] == "RECTANGLE"

    def test_self_closing_tags(self):
        xml = '<text id="2:1" name="Hello" x="0" y="0" width="50" height="20" />'
        node = parse_figma_xml(xml)
        assert node["type"] == "TEXT"
        assert "children" not in node

    def test_html_entity_unescape(self):
        xml = '<frame id="1:1" name="&lt;Group&gt;" x="0" y="0" width="100" height="100" />'
        node = parse_figma_xml(xml)
        assert node["name"] == "<Group>"

    def test_rounded_rectangle_maps_to_rectangle(self):
        xml = '<rounded-rectangle id="1:1" name="RR" x="0" y="0" width="50" height="50" />'
        node = parse_figma_xml(xml)
        assert node["type"] == "RECTANGLE"

    def test_visible_false(self):
        xml = '<frame id="1:1" name="Hidden" x="0" y="0" width="100" height="100" visible="false" />'
        node = parse_figma_xml(xml)
        assert node.get("visible") is False

    def test_deep_nesting(self):
        xml = '''<frame id="1:1" name="L1" x="0" y="0" width="1440" height="900">
            <frame id="1:2" name="L2" x="0" y="0" width="1440" height="900">
                <frame id="1:3" name="L3" x="0" y="0" width="1440" height="900">
                    <text id="1:4" name="Leaf" x="0" y="0" width="100" height="20" />
                </frame>
            </frame>
        </frame>'''
        node = parse_figma_xml(xml)
        assert node["children"][0]["children"][0]["children"][0]["name"] == "Leaf"


class TestLoadMetadata:
    """Tests for load_metadata — format-agnostic metadata loader."""

    def test_load_json_document(self):
        data = {"document": {"type": "FRAME", "id": "1:1", "name": "Root"}}
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(data, f)
        f.close()
        try:
            result = load_metadata(f.name)
            assert "document" in result
            assert result["document"]["name"] == "Root"
        finally:
            os.unlink(f.name)

    def test_load_mcp_wrapper(self):
        xml = '<frame id="1:1" name="Test" x="0" y="0" width="1440" height="800" />'
        wrapper = [{"type": "text", "text": xml}]
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(wrapper, f)
        f.close()
        try:
            result = load_metadata(f.name)
            assert result["document"]["name"] == "Test"
            assert result["document"]["type"] == "FRAME"
        finally:
            os.unlink(f.name)

    def test_load_raw_xml(self):
        xml = '<frame id="1:1" name="LP" x="0" y="0" width="1440" height="10000">\n  <text id="1:2" name="Hi" x="0" y="0" width="100" height="20" />\n</frame>'
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False)
        f.write(xml)
        f.close()
        try:
            result = load_metadata(f.name)
            assert result["document"]["name"] == "LP"
            assert len(result["document"]["children"]) == 1
        finally:
            os.unlink(f.name)

    def test_load_unknown_format_raises(self):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        f.write("this is not valid metadata")
        f.close()
        try:
            with pytest.raises(ValueError):
                load_metadata(f.name)
        finally:
            os.unlink(f.name)

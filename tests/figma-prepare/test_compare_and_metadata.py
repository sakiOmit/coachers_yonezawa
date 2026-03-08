"""Tests for compare grouping, metadata parsing, protection, and suppression."""
import json
import os
import tempfile
import pytest

from helpers import run_script, write_fixture

from figma_utils import (
    compare_grouping_by_section,
    compare_grouping_results,
    load_metadata,
    parse_figma_xml,
    _stage_a_pattern_key,
    STAGE_C_COVERAGE_THRESHOLD,
)

try:
    from figma_utils import find_node_by_id
    HAS_FIND_NODE = True
except ImportError:
    HAS_FIND_NODE = False


class TestCompareGroupingResults:
    """Tests for compare_grouping_results (Issue 194 Phase 3)."""

    def test_perfect_match(self):
        """Both stages produce identical groups -> full coverage, Jaccard=1.0."""
        stage_a = [
            {'method': 'pattern', 'node_ids': ['1:1', '1:2', '1:3'], 'count': 3,
             'suggested_name': 'card-list'},
        ]
        stage_c = [
            {'name': 'card-list', 'pattern': 'card', 'node_ids': ['1:1', '1:2', '1:3']},
        ]
        result = compare_grouping_results(stage_a, stage_c)
        assert result['coverage'] == 1.0
        assert result['mean_jaccard'] == 1.0
        assert len(result['matched_pairs']) == 1
        assert result['matched_pairs'][0]['jaccard'] == 1.0
        assert result['stage_a_only'] == []
        assert result['stage_c_only'] == []
        # Pattern accuracy: pattern -> card is valid match
        assert result['pattern_accuracy']['pattern']['matched'] == 1
        assert result['pattern_accuracy']['pattern']['total'] == 1

    def test_partial_overlap(self):
        """Stage A and C overlap partially -> Jaccard between 0 and 1."""
        stage_a = [
            {'method': 'semantic', 'semantic_type': 'card-list',
             'node_ids': ['1:1', '1:2', '1:3', '1:4'], 'count': 4,
             'suggested_name': 'card-list'},
        ]
        stage_c = [
            {'name': 'cards', 'pattern': 'card',
             'node_ids': ['1:1', '1:2', '1:3']},  # missing 1:4
        ]
        result = compare_grouping_results(stage_a, stage_c)
        # 3 out of 4 Stage A nodes covered
        assert result['coverage'] == 0.75
        # Jaccard = 3 / 4 = 0.75
        assert abs(result['jaccard_by_group'][0] - 0.75) < 0.01
        assert len(result['matched_pairs']) == 1

    def test_stage_a_only(self):
        """Stage A detects a group that Stage C misses entirely."""
        stage_a = [
            {'method': 'highlight', 'semantic_type': 'highlight',
             'node_ids': ['2:1', '2:2'], 'count': 2,
             'suggested_name': 'highlight-text'},
            {'method': 'pattern', 'node_ids': ['3:1', '3:2', '3:3'], 'count': 3,
             'suggested_name': 'list-items'},
        ]
        stage_c = [
            {'name': 'card-list', 'pattern': 'card',
             'node_ids': ['3:1', '3:2', '3:3']},
        ]
        result = compare_grouping_results(stage_a, stage_c)
        # highlight group (2:1, 2:2) not covered
        assert result['coverage'] == 3 / 5  # 3 of 5 Stage A nodes covered
        assert len(result['stage_a_only']) == 1
        assert 0 in result['stage_a_only']  # index 0 = highlight
        assert result['stage_c_only'] == []

    def test_stage_c_only(self):
        """Stage C detects a group that Stage A does not have."""
        stage_a = [
            {'method': 'pattern', 'node_ids': ['1:1', '1:2'], 'count': 2,
             'suggested_name': 'list-items'},
        ]
        stage_c = [
            {'name': 'list-items', 'pattern': 'list',
             'node_ids': ['1:1', '1:2']},
            {'name': 'decoration-dots', 'pattern': 'single',
             'node_ids': ['5:1', '5:2']},
        ]
        result = compare_grouping_results(stage_a, stage_c)
        assert len(result['stage_c_only']) == 1
        assert 1 in result['stage_c_only']  # decoration-dots

    def test_both_empty(self):
        """Both empty -> perfect agreement."""
        result = compare_grouping_results([], [])
        assert result['coverage'] == 1.0
        assert result['mean_jaccard'] == 1.0
        assert result['matched_pairs'] == []

    def test_stage_a_empty(self):
        """Stage A empty, Stage C has groups -> coverage=1.0 (nothing to cover)."""
        stage_c = [
            {'name': 'g1', 'pattern': 'card', 'node_ids': ['1:1']},
        ]
        result = compare_grouping_results([], stage_c)
        assert result['coverage'] == 1.0
        assert result['stage_c_only'] == [0]

    def test_stage_c_empty(self):
        """Stage C empty, Stage A has groups -> coverage=0.0."""
        stage_a = [
            {'method': 'pattern', 'node_ids': ['1:1', '1:2'], 'count': 2,
             'suggested_name': 'items'},
        ]
        result = compare_grouping_results(stage_a, [])
        assert result['coverage'] == 0.0
        assert result['mean_jaccard'] == 0.0
        assert result['stage_a_only'] == [0]

    def test_pattern_type_mapping(self):
        """Pattern accuracy correctly maps Stage A methods to Stage C patterns."""
        stage_a = [
            {'method': 'semantic', 'semantic_type': 'card-list',
             'node_ids': ['1:1', '1:2', '1:3'], 'count': 3},
            {'method': 'table', 'node_ids': ['2:1', '2:2', '2:3'], 'count': 3},
            {'method': 'heading-content',
             'node_ids': ['3:1', '3:2'], 'count': 2},
        ]
        stage_c = [
            {'name': 'cards', 'pattern': 'card',
             'node_ids': ['1:1', '1:2', '1:3']},
            {'name': 'data-table', 'pattern': 'table',
             'node_ids': ['2:1', '2:2', '2:3']},
            {'name': 'section-heading', 'pattern': 'heading-pair',
             'node_ids': ['3:1', '3:2']},
        ]
        result = compare_grouping_results(stage_a, stage_c)
        pa = result['pattern_accuracy']
        assert pa['semantic:card-list']['matched'] == 1
        assert pa['table']['matched'] == 1
        assert pa['heading-content']['matched'] == 1
        assert result['mean_jaccard'] == 1.0

    def test_no_match_below_threshold(self):
        """Jaccard below 0.5 -> no match."""
        stage_a = [
            {'method': 'pattern',
             'node_ids': ['1:1', '1:2', '1:3', '1:4', '1:5'], 'count': 5},
        ]
        stage_c = [
            # Only 1 overlap out of 5+4=8 unique -> Jaccard = 1/8 = 0.125
            {'name': 'other', 'pattern': 'list',
             'node_ids': ['1:1', '2:1', '2:2', '2:3']},
        ]
        result = compare_grouping_results(stage_a, stage_c)
        # Jaccard < 0.5 -> no match
        assert len(result['matched_pairs']) == 0
        assert 0 in result['stage_a_only']

    def test_stage_a_pattern_key(self):
        """_stage_a_pattern_key returns correct keys."""
        assert _stage_a_pattern_key({'method': 'semantic', 'semantic_type': 'card-list'}) == 'semantic:card-list'
        assert _stage_a_pattern_key({'method': 'pattern'}) == 'pattern'
        assert _stage_a_pattern_key({'method': 'table'}) == 'table'
        assert _stage_a_pattern_key({'method': 'highlight', 'semantic_type': 'highlight'}) == 'highlight'
        assert _stage_a_pattern_key({'method': 'heading-content'}) == 'heading-content'


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


# ============================================================
# Issue #221: Protected node (GROUP/COMPONENT/INSTANCE) preservation
# ============================================================
class TestProtectedNodeGrouping:
    """Verify that designer-intentional GROUPs and COMPONENTs are not decomposed."""

    def test_named_group_children_not_regrouped(self):
        """A named GROUP's children should not generate grouping candidates."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 3000},
                "children": [
                    {
                        "id": "1:1", "type": "GROUP", "name": "悩み",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 800},
                        "children": [
                            {"id": "2:1", "type": "TEXT", "name": "Text 1",
                             "absoluteBoundingBox": {"x": 10, "y": 10, "width": 200, "height": 30}},
                            {"id": "2:2", "type": "TEXT", "name": "Text 2",
                             "absoluteBoundingBox": {"x": 10, "y": 50, "width": 200, "height": 30}},
                            {"id": "2:3", "type": "TEXT", "name": "Text 3",
                             "absoluteBoundingBox": {"x": 10, "y": 90, "width": 200, "height": 30}},
                            {"id": "2:4", "type": "TEXT", "name": "Text 4",
                             "absoluteBoundingBox": {"x": 10, "y": 130, "width": 200, "height": 30}},
                        ],
                    },
                    {
                        "id": "1:2", "type": "FRAME", "name": "Section 2",
                        "absoluteBoundingBox": {"x": 0, "y": 1000, "width": 1440, "height": 1000},
                        "children": [
                            {"id": "3:1", "type": "TEXT", "name": "Title",
                             "absoluteBoundingBox": {"x": 10, "y": 1010, "width": 200, "height": 30}},
                        ],
                    },
                ],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("detect-grouping-candidates.sh", tmp)
            candidates = result.get("candidates", [])
            # No candidates should have parent_id = "1:1" (the named GROUP "悩み")
            named_group_candidates = [c for c in candidates if c.get("parent_name") == "悩み"]
            assert len(named_group_candidates) == 0, \
                f"Named GROUP '悩み' should not have grouping candidates, got: {named_group_candidates}"
        finally:
            os.unlink(tmp)

    def test_unnamed_group_still_processed(self):
        """An auto-named GROUP (e.g. 'Group 1') should still be processed for grouping."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 3000},
                "children": [
                    {
                        "id": "1:1", "type": "GROUP", "name": "Group 1",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 800},
                        "children": [
                            {"id": "2:1", "type": "TEXT", "name": "Text 1",
                             "absoluteBoundingBox": {"x": 10, "y": 10, "width": 100, "height": 30}},
                            {"id": "2:2", "type": "TEXT", "name": "Text 2",
                             "absoluteBoundingBox": {"x": 10, "y": 50, "width": 100, "height": 30}},
                            {"id": "2:3", "type": "TEXT", "name": "Text 3",
                             "absoluteBoundingBox": {"x": 10, "y": 90, "width": 100, "height": 30}},
                            {"id": "2:4", "type": "TEXT", "name": "Text 4",
                             "absoluteBoundingBox": {"x": 10, "y": 130, "width": 100, "height": 30}},
                            {"id": "2:5", "type": "TEXT", "name": "Text 5",
                             "absoluteBoundingBox": {"x": 10, "y": 170, "width": 100, "height": 30}},
                            {"id": "2:6", "type": "TEXT", "name": "Text 6",
                             "absoluteBoundingBox": {"x": 10, "y": 210, "width": 100, "height": 30}},
                            {"id": "2:7", "type": "TEXT", "name": "Text 7",
                             "absoluteBoundingBox": {"x": 10, "y": 250, "width": 100, "height": 30}},
                            {"id": "2:8", "type": "TEXT", "name": "Text 8",
                             "absoluteBoundingBox": {"x": 10, "y": 290, "width": 100, "height": 30}},
                            {"id": "2:9", "type": "TEXT", "name": "Text 9",
                             "absoluteBoundingBox": {"x": 10, "y": 330, "width": 100, "height": 30}},
                            {"id": "2:10", "type": "TEXT", "name": "Text 10",
                             "absoluteBoundingBox": {"x": 10, "y": 370, "width": 100, "height": 30}},
                            {"id": "2:11", "type": "TEXT", "name": "Text 11",
                             "absoluteBoundingBox": {"x": 10, "y": 410, "width": 100, "height": 30}},
                            {"id": "2:12", "type": "TEXT", "name": "Text 12",
                             "absoluteBoundingBox": {"x": 10, "y": 450, "width": 100, "height": 30}},
                            {"id": "2:13", "type": "TEXT", "name": "Text 13",
                             "absoluteBoundingBox": {"x": 10, "y": 490, "width": 100, "height": 30}},
                            {"id": "2:14", "type": "TEXT", "name": "Text 14",
                             "absoluteBoundingBox": {"x": 10, "y": 530, "width": 100, "height": 30}},
                            {"id": "2:15", "type": "TEXT", "name": "Text 15",
                             "absoluteBoundingBox": {"x": 10, "y": 570, "width": 100, "height": 30}},
                            {"id": "2:16", "type": "TEXT", "name": "Text 16",
                             "absoluteBoundingBox": {"x": 10, "y": 610, "width": 100, "height": 30}},
                        ],
                    },
                ],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("detect-grouping-candidates.sh", tmp)
            candidates = result.get("candidates", [])
            # "Group 1" is auto-named, so its children should still be processed
            group1_candidates = [c for c in candidates if c.get("parent_name") == "Group 1"]
            assert len(group1_candidates) > 0, \
                "Auto-named GROUP 'Group 1' should still have grouping candidates"
        finally:
            os.unlink(tmp)

    def test_component_children_not_regrouped(self):
        """COMPONENT children should not generate grouping candidates."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 3000},
                "children": [
                    {
                        "id": "1:1", "type": "COMPONENT", "name": "Button",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 200, "height": 50},
                        "children": [
                            {"id": "2:1", "type": "RECTANGLE", "name": "Rectangle 1",
                             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 200, "height": 50}},
                            {"id": "2:2", "type": "TEXT", "name": "Label",
                             "absoluteBoundingBox": {"x": 10, "y": 10, "width": 180, "height": 30}},
                        ],
                    },
                    {
                        "id": "1:2", "type": "INSTANCE", "name": "Button Instance",
                        "absoluteBoundingBox": {"x": 0, "y": 100, "width": 200, "height": 50},
                        "children": [
                            {"id": "3:1", "type": "RECTANGLE", "name": "Rectangle 1",
                             "absoluteBoundingBox": {"x": 0, "y": 100, "width": 200, "height": 50}},
                            {"id": "3:2", "type": "TEXT", "name": "Label",
                             "absoluteBoundingBox": {"x": 10, "y": 110, "width": 180, "height": 30}},
                        ],
                    },
                ],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("detect-grouping-candidates.sh", tmp)
            candidates = result.get("candidates", [])
            # No candidates should have parent "Button" or "Button Instance"
            comp_candidates = [c for c in candidates
                               if c.get("parent_name") in ("Button", "Button Instance")]
            assert len(comp_candidates) == 0, \
                f"COMPONENT/INSTANCE children should not have grouping candidates, got: {comp_candidates}"
        finally:
            os.unlink(tmp)


# ============================================================
# Issue #222: Over-grouping suppression for non-root levels
# ============================================================
class TestOverGroupingSuppression:
    """Verify that non-root nodes with few children don't get over-grouped."""

    def test_few_children_no_proximity_grouping(self):
        """Non-root FRAME with < FLAT_THRESHOLD children should not get proximity groups."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 3000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Frame 1",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 800},
                        "children": [
                            {"id": "2:1", "type": "TEXT", "name": "Title",
                             "absoluteBoundingBox": {"x": 10, "y": 10, "width": 200, "height": 30}},
                            {"id": "2:2", "type": "RECTANGLE", "name": "Image",
                             "absoluteBoundingBox": {"x": 10, "y": 50, "width": 400, "height": 300}},
                            {"id": "2:3", "type": "TEXT", "name": "Description",
                             "absoluteBoundingBox": {"x": 10, "y": 360, "width": 400, "height": 60}},
                            {"id": "2:4", "type": "FRAME", "name": "Button",
                             "absoluteBoundingBox": {"x": 10, "y": 430, "width": 150, "height": 40},
                             "children": []},
                        ],
                    },
                ],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("detect-grouping-candidates.sh", tmp)
            candidates = result.get("candidates", [])
            # No proximity/pattern/spacing candidates should exist for "Frame 1"
            # because it has only 4 children (< FLAT_THRESHOLD=15)
            overgroup_candidates = [c for c in candidates
                                    if c.get("parent_name") == "Frame 1"
                                    and c.get("method") in ("proximity", "pattern", "spacing")]
            assert len(overgroup_candidates) == 0, \
                f"Non-root FRAME with few children should not have proximity/pattern groups, got: {overgroup_candidates}"
        finally:
            os.unlink(tmp)


# ================================================================
# Issue 226: Section-level (parent_id-based) matching tests
# ================================================================


class TestCompareGroupingResultsWithParentId:
    """Tests for compare_grouping_results parent_id filtering (Issue 226)."""

    def test_compare_grouping_results_with_parent_id_filter(self):
        """parent_id filters Stage A and Stage C to matching section only."""
        stage_a = [
            {'method': 'pattern', 'node_ids': ['1:1', '1:2'], 'parent_id': 'sec-A'},
            {'method': 'pattern', 'node_ids': ['2:1', '2:2'], 'parent_id': 'sec-B'},
        ]
        stage_c = [
            {'name': 'group-a', 'pattern': 'card', 'node_ids': ['1:1', '1:2'],
             'section_id': 'sec-A'},
            {'name': 'group-b', 'pattern': 'list', 'node_ids': ['2:1', '2:2', '2:3'],
             'section_id': 'sec-B'},
        ]
        # Filter to sec-A only
        result = compare_grouping_results(stage_a, stage_c, parent_id='sec-A')
        assert result['coverage'] == 1.0
        assert result['mean_jaccard'] == 1.0
        assert len(result['matched_pairs']) == 1

    def test_parent_id_filter_uses_parent_field(self):
        """Stage A 'parent' field is also accepted for filtering."""
        stage_a = [
            {'method': 'pattern', 'node_ids': ['1:1'], 'parent': 'sec-X'},
        ]
        stage_c = [
            {'name': 'g1', 'pattern': 'card', 'node_ids': ['1:1'],
             'parent_group': 'sec-X'},
        ]
        result = compare_grouping_results(stage_a, stage_c, parent_id='sec-X')
        assert result['coverage'] == 1.0
        assert len(result['matched_pairs']) == 1

    def test_parent_id_no_match_returns_empty(self):
        """parent_id that matches nothing -> both empty behavior."""
        stage_a = [
            {'method': 'pattern', 'node_ids': ['1:1'], 'parent_id': 'sec-A'},
        ]
        stage_c = [
            {'name': 'g1', 'pattern': 'card', 'node_ids': ['1:1'],
             'section_id': 'sec-A'},
        ]
        result = compare_grouping_results(stage_a, stage_c, parent_id='sec-NONE')
        assert result['coverage'] == 1.0  # both empty
        assert result['mean_jaccard'] == 1.0

    def test_parent_id_none_is_current_behavior(self):
        """parent_id=None (default) compares all candidates globally."""
        stage_a = [
            {'method': 'pattern', 'node_ids': ['1:1', '1:2'], 'parent_id': 'sec-A'},
            {'method': 'pattern', 'node_ids': ['2:1', '2:2'], 'parent_id': 'sec-B'},
        ]
        stage_c = [
            {'name': 'g1', 'pattern': 'card', 'node_ids': ['1:1', '1:2'],
             'section_id': 'sec-A'},
            {'name': 'g2', 'pattern': 'list', 'node_ids': ['2:1', '2:2'],
             'section_id': 'sec-B'},
        ]
        result = compare_grouping_results(stage_a, stage_c)
        assert result['coverage'] == 1.0
        assert len(result['matched_pairs']) == 2


class TestCompareGroupingBySection:
    """Tests for compare_grouping_by_section (Issue 226)."""

    def test_compare_grouping_by_section_basic(self):
        """Two sections: Stage C covers one well, other poorly -> mixed adoption."""
        stage_a = [
            # Section A: 3 nodes
            {'method': 'pattern', 'node_ids': ['1:1', '1:2', '1:3'],
             'parent_id': 'sec-A', 'suggested_name': 'cards'},
            # Section B: 3 nodes
            {'method': 'pattern', 'node_ids': ['2:1', '2:2', '2:3'],
             'parent_id': 'sec-B', 'suggested_name': 'items'},
        ]
        stage_c_sections = [
            {
                'section_id': 'sec-A',
                'groups': [
                    {'name': 'card-list', 'pattern': 'card',
                     'node_ids': ['1:1', '1:2', '1:3']},  # perfect match
                ],
            },
            {
                'section_id': 'sec-B',
                'groups': [
                    {'name': 'other', 'pattern': 'list',
                     'node_ids': ['2:1']},  # poor coverage: 1/3
                ],
            },
        ]
        result = compare_grouping_by_section(stage_a, stage_c_sections)
        assert result['total_sections'] == 2
        # sec-A: coverage=1.0 >= 0.8 -> stage_c
        sec_a = next(s for s in result['sections'] if s['section_id'] == 'sec-A')
        assert sec_a['source'] == 'stage_c'
        assert sec_a['coverage'] == 1.0
        # sec-B: coverage=1/3 < 0.8 -> stage_a
        sec_b = next(s for s in result['sections'] if s['section_id'] == 'sec-B')
        assert sec_b['source'] == 'stage_a'
        assert sec_b['coverage'] < 0.8
        # Mixed: 1 stage_a + 1 stage_c
        assert result['stage_a_sections'] == 1
        assert result['stage_c_sections'] == 1

    def test_compare_grouping_by_section_all_stage_c(self):
        """All sections well-covered -> all Stage C adopted."""
        stage_a = [
            {'method': 'pattern', 'node_ids': ['1:1', '1:2'],
             'parent_id': 'sec-A'},
            {'method': 'pattern', 'node_ids': ['2:1', '2:2'],
             'parent_id': 'sec-B'},
        ]
        stage_c_sections = [
            {
                'section_id': 'sec-A',
                'groups': [
                    {'name': 'g1', 'pattern': 'card',
                     'node_ids': ['1:1', '1:2']},
                ],
            },
            {
                'section_id': 'sec-B',
                'groups': [
                    {'name': 'g2', 'pattern': 'list',
                     'node_ids': ['2:1', '2:2']},
                ],
            },
        ]
        result = compare_grouping_by_section(stage_a, stage_c_sections)
        assert result['stage_c_sections'] == 2
        assert result['stage_a_sections'] == 0
        for sec in result['sections']:
            assert sec['source'] == 'stage_c'
            assert sec['coverage'] >= 0.8

    def test_compare_grouping_by_section_all_fallback(self):
        """All sections poorly covered -> all Stage A fallback."""
        stage_a = [
            {'method': 'pattern', 'node_ids': ['1:1', '1:2', '1:3', '1:4', '1:5'],
             'parent_id': 'sec-A'},
            {'method': 'pattern', 'node_ids': ['2:1', '2:2', '2:3', '2:4', '2:5'],
             'parent_id': 'sec-B'},
        ]
        stage_c_sections = [
            {
                'section_id': 'sec-A',
                'groups': [
                    {'name': 'g1', 'pattern': 'card',
                     'node_ids': ['1:1']},  # 1/5 coverage
                ],
            },
            {
                'section_id': 'sec-B',
                'groups': [
                    {'name': 'g2', 'pattern': 'list',
                     'node_ids': ['2:1']},  # 1/5 coverage
                ],
            },
        ]
        result = compare_grouping_by_section(stage_a, stage_c_sections)
        assert result['stage_a_sections'] == 2
        assert result['stage_c_sections'] == 0
        for sec in result['sections']:
            assert sec['source'] == 'stage_a'
            assert sec['coverage'] < 0.8

    def test_compare_grouping_by_section_empty(self):
        """Empty inputs handled gracefully."""
        result = compare_grouping_by_section([], [])
        assert result['sections'] == []
        assert result['overall_coverage'] == 1.0
        assert result['total_sections'] == 0

    def test_compare_grouping_by_section_stage_c_only_sections(self):
        """Stage C has sections not in Stage A -> still processed."""
        stage_a = []
        stage_c_sections = [
            {
                'section_id': 'sec-X',
                'groups': [
                    {'name': 'g1', 'pattern': 'card',
                     'node_ids': ['1:1', '1:2']},
                ],
            },
        ]
        result = compare_grouping_by_section(stage_a, stage_c_sections)
        assert result['total_sections'] == 1
        sec = result['sections'][0]
        assert sec['section_id'] == 'sec-X'
        # No Stage A candidates => coverage=1.0 (nothing to cover) -> stage_c
        assert sec['source'] == 'stage_c'

    def test_compare_grouping_by_section_stage_a_only_sections(self):
        """Stage A has sections not in Stage C -> falls back to Stage A."""
        stage_a = [
            {'method': 'pattern', 'node_ids': ['1:1', '1:2'],
             'parent_id': 'sec-Y'},
        ]
        stage_c_sections = []
        result = compare_grouping_by_section(stage_a, stage_c_sections)
        assert result['total_sections'] == 1
        sec = result['sections'][0]
        assert sec['section_id'] == 'sec-Y'
        # No Stage C groups => coverage=0.0 -> stage_a
        assert sec['source'] == 'stage_a'
        assert sec['coverage'] == 0.0

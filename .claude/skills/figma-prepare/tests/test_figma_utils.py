"""
figma_utils.py unit tests + script integration tests.

Run: python3 -m pytest tests/test_figma_utils.py -v
From: .claude/skills/figma-prepare/
"""
import json
import os
import subprocess
import sys
import tempfile

import pytest

SKILLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILLS_DIR, "lib"))

from figma_utils import (
    alignment_bonus,
    compute_gap_consistency,
    compute_grouping_score,
    detect_regular_spacing,
    detect_space_between,
    detect_wrap,
    get_bbox,
    get_root_node,
    get_text_children_content,
    infer_direction_two_elements,
    is_section_root,
    is_unnamed,
    resolve_absolute_coords,
    size_similarity_bonus,
    snap,
    structure_hash,
    structure_similarity,
    to_kebab,
    yaml_str,
)

SCRIPTS_DIR = os.path.join(SKILLS_DIR, "scripts")


def run_script(script_name, *args, timeout=30):
    """Run a shell script and return parsed JSON output."""
    script = os.path.join(SCRIPTS_DIR, script_name)
    result = subprocess.run(
        ["bash", script, *args],
        capture_output=True, text=True, timeout=timeout,
    )
    assert result.returncode == 0, f"{script_name} failed: {result.stderr}"
    return json.loads(result.stdout)


def write_fixture(data):
    """Write JSON fixture to temp file, return path (caller must delete)."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(data, f)
    f.close()
    return f.name


# ============================================================
# to_kebab
# ============================================================
class TestToKebab:
    @pytest.mark.parametrize("input_text,expected", [
        ("job description", "job-description"),
        ("REASON", "reason"),
        ("CamelCase", "camel-case"),
        ("HTMLParser", "html-parser"),
        ("myComponent", "my-component"),
    ])
    def test_ascii(self, input_text, expected):
        assert to_kebab(input_text) == expected

    @pytest.mark.parametrize("input_text", [
        "大規模イベントに強いオペレーション力",
        "イベント一覧",
        "お問い合わせ",
        "無料相談",
        "資料請求",
        "日本語テスト",
    ])
    def test_japanese_only_returns_content(self, input_text):
        assert to_kebab(input_text) == "content"

    def test_empty_and_whitespace(self):
        assert to_kebab("") == ""
        assert to_kebab("   ") == ""

    def test_mixed_jp_ascii(self):
        assert to_kebab("Hello世界") == "hello"
        assert to_kebab("日本語test混合") == "test"

    def test_special_chars_only(self):
        assert to_kebab("@#$%!") == "content"

    def test_truncation(self):
        assert len(to_kebab("a" * 100)) <= 40

    def test_whitespace_characters(self):
        assert to_kebab("hello\tworld") == "hello-world"
        assert to_kebab("hello\nworld") == "hello-world"
        assert to_kebab("hello\r\nworld") == "hello-world"
        assert to_kebab("  hello  ") == "hello"
        assert to_kebab("multi   space") == "multi-space"


# ============================================================
# snap
# ============================================================
class TestSnap:
    @pytest.mark.parametrize("value,expected", [
        (0, 0), (4, 4), (8, 8), (16, 16),     # exact multiples
        (1, 0), (5, 4), (13, 12),               # round down
        (3, 4), (6, 8), (7, 8), (14, 16), (15, 16),  # round up
        (2, 0),                                  # midpoint (banker's rounding)
        (-1, 0), (-3, -4),                       # negative
    ])
    def test_default_grid(self, value, expected):
        assert snap(value) == expected

    def test_custom_grid(self):
        assert snap(7, grid=8) == 8
        assert snap(3, grid=8) == 0

    def test_float(self):
        assert snap(5.7) == 4


# ============================================================
# is_section_root
# ============================================================
class TestIsSectionRoot:
    @pytest.mark.parametrize("width", [1440, 1438, 1442])
    def test_valid_roots(self, width):
        assert is_section_root({"type": "FRAME", "absoluteBoundingBox": {"width": width}})

    @pytest.mark.parametrize("node", [
        {"type": "GROUP", "absoluteBoundingBox": {"width": 1440}},
        {"type": "TEXT", "absoluteBoundingBox": {"width": 1440}},
        {"type": "FRAME", "absoluteBoundingBox": {"width": 800}},
        {"type": "FRAME", "absoluteBoundingBox": {"width": 1460}},
        {"type": "FRAME"},
        {"type": "FRAME", "absoluteBoundingBox": {}},
    ])
    def test_invalid_roots(self, node):
        assert is_section_root(node) is False


# ============================================================
# is_unnamed
# ============================================================
class TestIsUnnamed:
    @pytest.mark.parametrize("name", [
        "Frame 1", "Rectangle 23", "Text 5", "Group 100", "image 1254",
        "Instance 3", "Component 7", "Vector", "Ellipse", "Polygon 2",
        "Star 1", "Line",
    ])
    def test_unnamed(self, name):
        assert is_unnamed(name) is True

    @pytest.mark.parametrize("name", [
        "hero-section", "Header", "Frame Header", "My Frame 1",
        "card-feature", "",
    ])
    def test_named(self, name):
        assert is_unnamed(name) is False


# ============================================================
# get_bbox
# ============================================================
class TestGetBbox:
    def test_normal(self):
        node = {"absoluteBoundingBox": {"x": 10, "y": 20, "width": 100, "height": 50}}
        assert get_bbox(node) == {"x": 10, "y": 20, "w": 100, "h": 50}

    def test_missing(self):
        assert get_bbox({}) == {"x": 0, "y": 0, "w": 0, "h": 0}

    def test_partial(self):
        bb = get_bbox({"absoluteBoundingBox": {"x": 5}})
        assert bb["x"] == 5 and bb["y"] == 0


# ============================================================
# get_root_node
# ============================================================
class TestGetRootNode:
    def test_document_key(self):
        assert get_root_node({"document": {"id": "root"}})["id"] == "root"

    def test_node_key(self):
        assert get_root_node({"node": {"id": "n1"}})["id"] == "n1"

    def test_bare_node(self):
        assert get_root_node({"id": "bare", "children": []})["id"] == "bare"

    def test_document_priority(self):
        data = {"document": {"id": "doc"}, "node": {"id": "n"}}
        assert get_root_node(data)["id"] == "doc"


# ============================================================
# get_text_children_content
# ============================================================
class TestGetTextChildrenContent:
    CHILDREN = [
        {"type": "TEXT", "characters": "Hello", "name": "Text 1"},
        {"type": "TEXT", "characters": "", "name": "Fallback Name"},
        {"type": "FRAME", "name": "Frame 1"},
        {"type": "TEXT", "characters": "World", "name": "Text 3"},
        {"type": "TEXT", "name": "Frame 5"},
    ]

    def test_basic(self):
        assert get_text_children_content(self.CHILDREN) == [
            "Hello", "Fallback Name", "World", "Frame 5",
        ]

    def test_max_items(self):
        assert len(get_text_children_content(self.CHILDREN, max_items=2)) == 2

    def test_filter_unnamed(self):
        result = get_text_children_content(self.CHILDREN, filter_unnamed=True)
        assert "Frame 5" not in result
        assert len(result) == 3

    def test_empty(self):
        assert get_text_children_content([]) == []

    def test_characters_preferred(self):
        children = [{"type": "TEXT", "characters": "From characters", "name": "From name"}]
        assert get_text_children_content(children) == ["From characters"]


# ============================================================
# yaml_str
# ============================================================
class TestYamlStr:
    def test_basic(self):
        assert yaml_str("hello") == '"hello"'

    def test_empty(self):
        assert yaml_str("") == '""'

    def test_integer(self):
        assert yaml_str(123) == '"123"'

    def test_japanese(self):
        assert "日本語テスト" in yaml_str("日本語テスト")

    def test_quotes_escaped(self):
        result = yaml_str('say "hi"')
        assert isinstance(result, str)

    def test_backslash(self):
        result = yaml_str("path\\to\\file")
        assert "\\\\" in result


# ============================================================
# resolve_absolute_coords
# ============================================================
class TestResolveAbsoluteCoords:
    def test_parent_child_accumulation(self):
        node = {
            "absoluteBoundingBox": {"x": 10, "y": 20, "width": 100, "height": 100},
            "children": [{
                "absoluteBoundingBox": {"x": 5, "y": 5, "width": 50, "height": 50},
                "children": [{
                    "absoluteBoundingBox": {"x": 2, "y": 3, "width": 10, "height": 10},
                    "children": [],
                }],
            }],
        }
        resolve_absolute_coords(node)
        assert node["absoluteBoundingBox"]["x"] == 10
        child = node["children"][0]
        assert child["absoluteBoundingBox"]["x"] == 15
        assert child["absoluteBoundingBox"]["y"] == 25
        gc = child["children"][0]
        assert gc["absoluteBoundingBox"]["x"] == 17
        assert gc["absoluteBoundingBox"]["y"] == 28

    def test_leaf(self):
        leaf = {"absoluteBoundingBox": {"x": 5, "y": 10, "width": 20, "height": 30}}
        resolve_absolute_coords(leaf, parent_x=100, parent_y=200)
        assert leaf["absoluteBoundingBox"]["x"] == 105

    def test_missing_bbox(self):
        node = {"children": []}
        resolve_absolute_coords(node, parent_x=50, parent_y=60)
        assert node["absoluteBoundingBox"]["x"] == 50

    def test_double_call_guard(self):
        node = {
            "absoluteBoundingBox": {"x": 10, "y": 20, "width": 100, "height": 100},
            "children": [{
                "absoluteBoundingBox": {"x": 5, "y": 5, "width": 50, "height": 50},
                "children": [],
            }],
        }
        resolve_absolute_coords(node)
        child = node["children"][0]
        assert child["absoluteBoundingBox"]["x"] == 15
        resolve_absolute_coords(node)
        assert child["absoluteBoundingBox"]["x"] == 15

    def test_null_bbox(self):
        node = {"absoluteBoundingBox": None, "children": []}
        resolve_absolute_coords(node, parent_x=10, parent_y=20)
        assert node["absoluteBoundingBox"]["x"] == 10


# ============================================================
# compute_grouping_score (Area 1)
# ============================================================
class TestComputeGroupingScore:
    A = {"x": 0, "y": 0, "w": 100, "h": 50}

    def test_identical(self):
        assert compute_grouping_score(self.A, self.A) == 1.0

    def test_close(self):
        b = {"x": 110, "y": 0, "w": 100, "h": 50}
        assert compute_grouping_score(self.A, b, gap=24) >= 0.5

    def test_far(self):
        far = {"x": 500, "y": 0, "w": 100, "h": 50}
        assert compute_grouping_score(self.A, far) < 0.1

    def test_aligned_beats_unaligned(self):
        aligned = {"x": 0, "y": 70, "w": 100, "h": 50}
        unaligned = {"x": 30, "y": 70, "w": 60, "h": 50}
        assert compute_grouping_score(self.A, aligned) >= compute_grouping_score(self.A, unaligned)

    def test_same_size_beats_diff(self):
        same = {"x": 130, "y": 0, "w": 100, "h": 50}
        diff = {"x": 130, "y": 0, "w": 200, "h": 100}
        assert compute_grouping_score(self.A, same) >= compute_grouping_score(self.A, diff)

    def test_alignment_bonus(self):
        aligned = {"x": 0, "y": 70, "w": 100, "h": 50}
        assert alignment_bonus(self.A, aligned) == 0.5

    def test_size_similarity_bonus(self):
        same = {"x": 130, "y": 0, "w": 100, "h": 50}
        diff = {"x": 130, "y": 0, "w": 200, "h": 100}
        assert size_similarity_bonus(self.A, same) == 0.7
        assert size_similarity_bonus(self.A, diff) == 1.0

    def test_zero_size(self):
        zero = {"x": 0, "y": 0, "w": 0, "h": 0}
        assert size_similarity_bonus(self.A, zero) == 1.0


# ============================================================
# structure_similarity / detect_regular_spacing (Area 2)
# ============================================================
class TestStructureSimilarity:
    def test_identical(self):
        assert structure_similarity("FRAME:[TEXT,TEXT]", "FRAME:[TEXT,TEXT]") == 1.0

    def test_different(self):
        assert structure_similarity("FRAME:[TEXT]", "FRAME:[IMAGE]") == 0.0

    def test_partial(self):
        s = structure_similarity("FRAME:[IMAGE,TEXT,TEXT]", "FRAME:[IMAGE,TEXT,RECTANGLE]")
        assert 0.3 < s < 0.9

    def test_leaf_same(self):
        assert structure_similarity("TEXT", "TEXT") == 1.0

    def test_leaf_diff(self):
        assert structure_similarity("TEXT", "IMAGE") == 0.0

    def test_card_variants(self):
        s = structure_similarity("FRAME:[IMAGE,TEXT,TEXT,FRAME]", "FRAME:[RECTANGLE,TEXT,TEXT,FRAME]")
        assert s >= 0.5

    def test_empty_children(self):
        assert structure_similarity("FRAME:[]", "FRAME:[]") == 1.0


class TestDetectRegularSpacing:
    def test_even(self):
        boxes = [{"x": i * 120, "y": 0, "w": 100, "h": 50} for i in range(5)]
        assert detect_regular_spacing(boxes) is True

    def test_too_few(self):
        boxes = [{"x": i * 120, "y": 0, "w": 100, "h": 50} for i in range(2)]
        assert detect_regular_spacing(boxes) is False

    def test_irregular(self):
        boxes = [
            {"x": 0, "y": 0, "w": 100, "h": 50},
            {"x": 110, "y": 0, "w": 100, "h": 50},
            {"x": 500, "y": 0, "w": 100, "h": 50},
        ]
        assert detect_regular_spacing(boxes) is False

    def test_vertical(self):
        boxes = [{"x": 0, "y": i * 80, "w": 100, "h": 60} for i in range(4)]
        assert detect_regular_spacing(boxes) is True


# ============================================================
# structure_hash (Issue 144)
# ============================================================
class TestStructureHash:
    def test_leaf(self):
        assert structure_hash({"type": "TEXT"}) == "TEXT"

    def test_empty_children(self):
        assert structure_hash({"type": "IMAGE", "children": []}) == "IMAGE"

    def test_missing_type(self):
        assert structure_hash({}) == "UNKNOWN"

    def test_sorted_children(self):
        node = {"type": "FRAME", "children": [
            {"type": "TEXT"}, {"type": "IMAGE"}, {"type": "TEXT"},
        ]}
        assert structure_hash(node) == "FRAME:[IMAGE,TEXT,TEXT]"

    def test_single_child(self):
        node = {"type": "FRAME", "children": [{"type": "RECTANGLE"}]}
        assert structure_hash(node) == "FRAME:[RECTANGLE]"

    def test_instance(self):
        node = {"type": "INSTANCE", "children": [{"type": "FRAME"}, {"type": "TEXT"}]}
        assert structure_hash(node) == "INSTANCE:[FRAME,TEXT]"


# ============================================================
# infer_direction_two / wrap / space_between (Area 4)
# ============================================================
class TestInferDirectionTwo:
    def test_horizontal(self):
        a = {"x": 0, "y": 0, "w": 100, "h": 50}
        b = {"x": 120, "y": 0, "w": 100, "h": 50}
        assert infer_direction_two_elements(a, b) == "HORIZONTAL"

    def test_vertical(self):
        a = {"x": 0, "y": 0, "w": 100, "h": 50}
        b = {"x": 0, "y": 70, "w": 100, "h": 50}
        assert infer_direction_two_elements(a, b) == "VERTICAL"

    def test_diagonal_horizontal(self):
        a = {"x": 0, "y": 0, "w": 50, "h": 50}
        b = {"x": 200, "y": 30, "w": 50, "h": 50}
        assert infer_direction_two_elements(a, b) == "HORIZONTAL"

    def test_diagonal_vertical(self):
        a = {"x": 0, "y": 0, "w": 50, "h": 50}
        b = {"x": 30, "y": 200, "w": 50, "h": 50}
        assert infer_direction_two_elements(a, b) == "VERTICAL"

    def test_same_position(self):
        s = {"x": 0, "y": 0, "w": 50, "h": 50}
        assert infer_direction_two_elements(s, s) == "VERTICAL"


class TestDetectWrap:
    BOXES = [
        {"x": 0, "y": 0, "w": 100, "h": 50},
        {"x": 120, "y": 0, "w": 100, "h": 50},
        {"x": 0, "y": 70, "w": 100, "h": 50},
        {"x": 120, "y": 70, "w": 100, "h": 50},
    ]

    def test_wrap_detected(self):
        assert detect_wrap(self.BOXES, "HORIZONTAL") is True

    def test_too_few(self):
        assert detect_wrap(self.BOXES[:3], "HORIZONTAL") is False

    def test_single_row(self):
        row = [{"x": i * 120, "y": 0, "w": 100, "h": 50} for i in range(5)]
        assert detect_wrap(row, "HORIZONTAL") is False

    def test_vertical_always_false(self):
        assert detect_wrap(self.BOXES, "VERTICAL") is False


class TestDetectSpaceBetween:
    def test_touching_edges(self):
        frame = {"x": 0, "y": 0, "w": 400, "h": 50}
        boxes = [
            {"x": 0, "y": 0, "w": 100, "h": 50},
            {"x": 150, "y": 0, "w": 100, "h": 50},
            {"x": 300, "y": 0, "w": 100, "h": 50},
        ]
        assert detect_space_between(boxes, "HORIZONTAL", frame) is True

    def test_not_touching(self):
        frame = {"x": 0, "y": 0, "w": 500, "h": 50}
        boxes = [
            {"x": 0, "y": 0, "w": 100, "h": 50},
            {"x": 150, "y": 0, "w": 100, "h": 50},
            {"x": 300, "y": 0, "w": 100, "h": 50},
        ]
        assert detect_space_between(boxes, "HORIZONTAL", frame) is False

    def test_vertical(self):
        frame = {"x": 0, "y": 0, "w": 100, "h": 300}
        boxes = [
            {"x": 0, "y": 0, "w": 100, "h": 80},
            {"x": 0, "y": 110, "w": 100, "h": 80},
            {"x": 0, "y": 220, "w": 100, "h": 80},
        ]
        assert detect_space_between(boxes, "VERTICAL", frame) is True


class TestGapConsistency:
    def test_uniform(self):
        assert compute_gap_consistency([20, 20, 20]) < 0.01

    def test_varied(self):
        assert compute_gap_consistency([10, 50, 20]) > 0.3

    def test_single(self):
        assert compute_gap_consistency([20]) == 0.0

    def test_empty(self):
        assert compute_gap_consistency([]) == 1.0


# ============================================================
# Script integration tests (create fixture → call script → verify)
# ============================================================
class TestScriptIntegration:
    """Tests that create temp fixtures and invoke shell scripts."""

    def test_fills_empty_no_crash(self):
        """Issue 32: fills=[] should not crash generate-rename-map.sh."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1000},
            "children": [{
                "id": "1:1", "name": "Frame 1", "type": "FRAME",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 800, "height": 400},
                "children": [
                    {"id": "1:2", "name": "Rectangle 1", "type": "RECTANGLE",
                     "absoluteBoundingBox": {"x": 0, "y": 0, "width": 800, "height": 200},
                     "fills": [], "children": []},
                    {"id": "1:3", "name": "Text 1", "type": "TEXT",
                     "absoluteBoundingBox": {"x": 0, "y": 200, "width": 800, "height": 50},
                     "children": []},
                    {"id": "1:4", "name": "Frame 2", "type": "FRAME",
                     "absoluteBoundingBox": {"x": 0, "y": 250, "width": 200, "height": 50},
                     "children": [{"id": "1:5", "name": "Button", "type": "TEXT",
                                   "absoluteBoundingBox": {"x": 0, "y": 0, "width": 100, "height": 30},
                                   "children": []}]},
                ],
            }],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("generate-rename-map.sh", tmp)
            assert "error" not in data
        finally:
            os.unlink(tmp)

    def test_instance_header_detection(self):
        """Issue 37: INSTANCE at top → header, COMPONENT at bottom → footer."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 5000},
            "children": [
                {"id": "1:1", "name": "Header Instance", "type": "INSTANCE",
                 "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 80},
                 "children": []},
                {"id": "1:2", "name": "Main Content", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 100, "width": 1440, "height": 4700},
                 "children": []},
                {"id": "1:3", "name": "Footer Component", "type": "COMPONENT",
                 "absoluteBoundingBox": {"x": 0, "y": 4850, "width": 1440, "height": 150},
                 "children": []},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("prepare-sectioning-context.sh", tmp)
            assert "1:1" in data["heuristic_hints"]["header_candidates"]
            assert "1:3" in data["heuristic_hints"]["footer_candidates"]
        finally:
            os.unlink(tmp)

    def test_characters_field_preference(self):
        """Issue 38: characters field preferred over name for TEXT nodes."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1000},
            "children": [
                {"id": "1:1", "name": "Text 1", "type": "TEXT",
                 "absoluteBoundingBox": {"x": 0, "y": 0, "width": 200, "height": 30},
                 "characters": "お問い合わせ", "children": []},
                {"id": "1:2", "name": "Frame 1", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 100, "width": 400, "height": 200},
                 "children": [
                     {"id": "1:3", "name": "Text 2", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 0, "y": 0, "width": 200, "height": 30},
                      "characters": "募集要項", "children": []},
                     {"id": "1:4", "name": "Text 3", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 0, "y": 40, "width": 200, "height": 30},
                      "characters": "REASON", "children": []},
                 ]},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("generate-rename-map.sh", tmp)
            renames = data.get("renames", {})
            r1 = renames.get("1:1", {})
            assert "content" in r1.get("new_name", "")
            r2 = renames.get("1:2", {})
            name = r2.get("new_name", "")
            assert "requirements" in name or "heading" in name
        finally:
            os.unlink(tmp)

    def test_yaml_structure_hash_key(self):
        """Issue 41: YAML output uses structure_hash key, not pattern."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
            "children": [
                {"id": f"1:{i}", "name": f"Frame {i}", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": i * 300, "width": 300, "height": 200},
                 "children": [
                     {"id": f"1:{i}0", "name": f"Text {i}", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 0, "y": 0, "width": 200, "height": 30},
                      "children": []},
                 ]}
                for i in range(1, 4)
            ],
        }
        tmp = write_fixture(fixture)
        yaml_path = tmp + ".yaml"
        try:
            run_script("detect-grouping-candidates.sh", tmp, "--output", yaml_path)
            with open(yaml_path) as f:
                content = f.read()
            assert "structure_hash:" in content
            assert "pattern:" not in content
        finally:
            os.unlink(tmp)
            if os.path.exists(yaml_path):
                os.unlink(yaml_path)

    def test_empty_enrichment(self):
        """Issue 58: empty enrichment handled gracefully."""
        metadata = {
            "id": "0:1", "name": "Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1000},
            "children": [{"id": "1:1", "name": "Child", "type": "FRAME",
                          "absoluteBoundingBox": {"x": 0, "y": 0, "width": 100, "height": 100},
                          "children": []}],
        }
        meta_tmp = write_fixture(metadata)
        enrich_tmp = write_fixture({})
        out_tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
        try:
            data = run_script("enrich-metadata.sh", meta_tmp, enrich_tmp, "--output", out_tmp)
            assert data["enriched_nodes"] == 0
            with open(out_tmp) as f:
                assert json.load(f)["id"] == "0:1"
        finally:
            for p in (meta_tmp, enrich_tmp, out_tmp):
                if os.path.exists(p):
                    os.unlink(p)

    def test_childless_root(self):
        """Issue 59: childless root handled gracefully."""
        fixture = {
            "id": "0:1", "name": "Empty Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 0},
            "children": [],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("prepare-sectioning-context.sh", tmp)
            assert data["total_children"] == 0
            assert data["top_level_children"] == []
            assert data["heuristic_hints"]["header_candidates"] == []
        finally:
            os.unlink(tmp)

    def test_semantic_detection(self):
        """Area 3: Card + nav detection, semantic method, dedup."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
            "children": [
                {"id": "1:1", "name": "Cards Section", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 600},
                 "children": [
                     {"id": f"1:{10+i}", "name": f"Card {i}", "type": "FRAME",
                      "absoluteBoundingBox": {"x": i * 400, "y": 0, "width": 350, "height": 400},
                      "children": [
                          {"id": f"1:{20+i}", "name": f"img {i}", "type": "RECTANGLE",
                           "absoluteBoundingBox": {"x": i * 400, "y": 0, "width": 350, "height": 200}},
                          {"id": f"1:{30+i}", "name": f"text {i}", "type": "TEXT",
                           "absoluteBoundingBox": {"x": i * 400, "y": 210, "width": 350, "height": 40},
                           "characters": f"Card Title {i}"},
                      ]}
                     for i in range(3)
                 ]},
                {"id": "2:1", "name": "Nav Section", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 700, "width": 1440, "height": 60},
                 "children": [
                     {"id": f"2:{10+i}", "name": f"Link {i}", "type": "TEXT",
                      "absoluteBoundingBox": {"x": i * 150, "y": 700, "width": 120, "height": 40},
                      "characters": f"Menu {i}"}
                     for i in range(5)
                 ]},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("detect-grouping-candidates.sh", tmp)
            methods = {c.get("method", "") for c in data.get("candidates", [])}
            cards = [c for c in data["candidates"]
                     if c.get("method") == "semantic" and c.get("semantic_type") == "card-list"]
            navs = [c for c in data["candidates"]
                    if c.get("method") == "semantic" and c.get("semantic_type") == "navigation"]
            assert len(cards) >= 1
            assert len(navs) >= 1
            assert "semantic" in methods
            assert "page-kv" not in methods
            assert data["total"] >= 2
        finally:
            os.unlink(tmp)

    def test_detect_header_footer_groups(self):
        """Issue 85: Header/footer group detection from flat elements."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 5000},
            "children": [
                {"id": "1:1", "name": "Vector", "type": "VECTOR",
                 "absoluteBoundingBox": {"x": 50, "y": 20, "width": 100, "height": 30}},
                *[{"id": f"1:{10+i}", "name": f"Nav {i}", "type": "TEXT",
                   "absoluteBoundingBox": {"x": 300 + i * 150, "y": 25, "width": 120, "height": 20},
                   "characters": f"Menu {i}"} for i in range(6)],
                {"id": "1:20", "name": "Frame 1", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 80},
                 "children": [
                     {"id": "1:21", "name": "Sub 1", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 200, "y": 10, "width": 100, "height": 20}},
                     {"id": "1:22", "name": "Sub 2", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 400, "y": 10, "width": 100, "height": 20}},
                 ]},
                {"id": "2:1", "name": "Main Content", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 400, "width": 1440, "height": 3000},
                 "children": [{"id": "2:2", "name": "Text 1", "type": "TEXT",
                                "absoluteBoundingBox": {"x": 50, "y": 400, "width": 500, "height": 40}}]},
                {"id": "3:1", "name": "Line 1", "type": "LINE",
                 "absoluteBoundingBox": {"x": 0, "y": 4800, "width": 1440, "height": 1}},
                {"id": "3:2", "name": "Footer Text", "type": "TEXT",
                 "absoluteBoundingBox": {"x": 50, "y": 4850, "width": 300, "height": 20},
                 "characters": "Copyright 2024"},
                {"id": "3:3", "name": "Footer Links", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 4900, "width": 1440, "height": 80},
                 "children": [{"id": "3:4", "name": "Link 1", "type": "TEXT",
                                "absoluteBoundingBox": {"x": 50, "y": 4900, "width": 100, "height": 20}}]},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("detect-grouping-candidates.sh", tmp)
            header = [c for c in data["candidates"] if c.get("semantic_type") == "header"]
            footer = [c for c in data["candidates"] if c.get("semantic_type") == "footer"]
            assert len(header) >= 1
            assert "1:1" in header[0]["node_ids"]
            assert len(footer) >= 1
            for c in header + footer:
                assert "2:1" not in c.get("node_ids", [])
        finally:
            os.unlink(tmp)

    def test_already_named_header_footer_excluded(self):
        """Issue 85: Already-named HEADER/FOOTER should not be re-grouped."""
        fixture = {
            "id": "0:1", "name": "Test", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 3000},
            "children": [
                {"id": "1:1", "name": "HEADER", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 80},
                 "children": []},
                {"id": "2:1", "name": "Content", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 80, "width": 1440, "height": 2800},
                 "children": []},
                {"id": "3:1", "name": "FOOTER", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 2880, "width": 1440, "height": 120},
                 "children": []},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("detect-grouping-candidates.sh", tmp)
            hf = [c for c in data["candidates"]
                  if c.get("semantic_type") in ("header", "footer")]
            assert len(hf) == 0
        finally:
            os.unlink(tmp)

    def test_infer_zone_semantic_name(self):
        """Issue 91: Zone names should be semantic, not generic 'section'."""
        fixture = {
            "id": "1:1", "name": "Artboard", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 4500},
            "children": [
                {"id": "2:1", "name": "Rectangle 1", "type": "RECTANGLE",
                 "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 600}},
                {"id": "2:2", "name": "Text 1", "type": "TEXT", "characters": "Welcome",
                 "absoluteBoundingBox": {"x": 100, "y": 200, "width": 400, "height": 60}},
                *[{"id": f"2:{3+i}", "name": f"Frame {2+i}", "type": "FRAME",
                   "absoluteBoundingBox": {"x": 100 + i * 400, "y": 800, "width": 350, "height": 400},
                   "children": [
                       {"id": f"3:{1+i*2}", "type": "RECTANGLE", "name": f"Image {i+1}",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 350, "height": 200}},
                       {"id": f"3:{2+i*2}", "type": "TEXT", "name": f"Title {i+1}",
                        "characters": f"Card {i+1}",
                        "absoluteBoundingBox": {"x": 0, "y": 210, "width": 350, "height": 30}},
                   ]} for i in range(3)],
                *[{"id": f"2:{6+i}", "name": f"Text {2+i}", "type": "TEXT",
                   "characters": name,
                   "absoluteBoundingBox": {"x": 100 + i * 100, "y": 1500, "width": 60, "height": 20}}
                  for i, name in enumerate(["Home", "About", "Service", "Contact", "FAQ"])],
                {"id": "2:11", "name": "Text 7", "type": "TEXT", "characters": "Description",
                 "absoluteBoundingBox": {"x": 100, "y": 2000, "width": 600, "height": 100}},
                {"id": "2:12", "name": "Frame 5", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 100, "y": 2100, "width": 600, "height": 200},
                 "children": [
                     {"id": "3:7", "type": "TEXT", "name": "Sub", "characters": "Sub text",
                      "absoluteBoundingBox": {"x": 0, "y": 0, "width": 300, "height": 30}},
                 ]},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("detect-grouping-candidates.sh", tmp)
            zone_candidates = [c for c in data.get("candidates", []) if c.get("method") == "zone"]
            assert len(zone_candidates) >= 1
            generic = [c for c in zone_candidates if c.get("suggested_name") == "section"]
            assert len(generic) == 0, f"Generic names found: {[c['suggested_name'] for c in zone_candidates]}"
            for c in zone_candidates:
                name = c.get("suggested_name", "")
                assert name.startswith("section-")
                assert len(name) > len("section-")
        finally:
            os.unlink(tmp)

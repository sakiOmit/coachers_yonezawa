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
    _jp_keyword_lookup,
    _raw_distance,
    alignment_bonus,
    compute_gap_consistency,
    compute_grouping_score,
    detect_consecutive_similar,
    detect_heading_content_pairs,
    detect_regular_spacing,
    detect_space_between,
    detect_wrap,
    find_absorbable_elements,
    get_bbox,
    get_root_node,
    get_text_children_content,
    infer_direction_two_elements,
    is_heading_like,
    is_section_root,
    is_unnamed,
    JP_KEYWORD_MAP,
    resolve_absolute_coords,
    size_similarity_bonus,
    snap,
    structure_hash,
    structure_similarity,
    to_kebab,
    yaml_str,
    CONSECUTIVE_PATTERN_MIN,
    LOOSE_ELEMENT_MAX_HEIGHT,
    LOOSE_ABSORPTION_DISTANCE,
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
        "無料相談",
        "資料請求",
        "日本語テスト",
    ])
    def test_japanese_only_returns_content(self, input_text):
        """JP text with no keyword match falls back to 'content'."""
        assert to_kebab(input_text) == "content"

    @pytest.mark.parametrize("input_text,expected", [
        ("お問い合わせ", "contact"),
        ("イベント一覧", "event"),  # 'イベント' matches (longer keyword first)
        ("大規模イベントに強いオペレーション力", "event"),  # contains 'イベント'
        ("ケータリング", "catering"),
        ("フィンガーフード", "finger-food"),
        ("メニュー", "menu"),
        ("サービス", "service"),
        ("パーティー", "party"),
        ("企業", "corporate"),
        ("オフィス", "office"),
        ("スタッフ", "staff"),
        ("プラン", "plan"),
        ("フード", "food"),
    ])
    def test_japanese_keyword_map(self, input_text, expected):
        """JP text with keyword match returns the mapped English slug."""
        assert to_kebab(input_text) == expected

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
# _jp_keyword_lookup
# ============================================================
class TestJpKeywordLookup:
    def test_exact_match(self):
        assert _jp_keyword_lookup("ケータリング") == "catering"
        assert _jp_keyword_lookup("フィンガーフード") == "finger-food"
        assert _jp_keyword_lookup("メニュー") == "menu"

    def test_partial_match(self):
        """Keyword found within longer text."""
        assert _jp_keyword_lookup("ケータリングサービスのご案内") == "catering"
        assert _jp_keyword_lookup("大規模イベントに強いオペレーション力") == "event"

    def test_longest_match_first(self):
        """Longer keywords are preferred over shorter ones."""
        # 'フィンガーフード' (7 chars) should match before 'フード' (3 chars)
        assert _jp_keyword_lookup("フィンガーフード盛り合わせ") == "finger-food"
        # 'お問い合わせ' (6 chars) should match before '問い合わせ' (5 chars)
        assert _jp_keyword_lookup("お問い合わせフォーム") == "contact"

    def test_no_match(self):
        assert _jp_keyword_lookup("日本語テスト") == ""
        assert _jp_keyword_lookup("無料相談") == ""
        assert _jp_keyword_lookup("") == ""

    def test_all_required_keywords_present(self):
        """Verify all keywords from Issue 170 spec are in JP_KEYWORD_MAP."""
        required = {
            'ケータリング': 'catering',
            'フィンガーフード': 'finger-food',
            'メニュー': 'menu',
            'サービス': 'service',
            'イベント': 'event',
            'パーティー': 'party',
            'フード': 'food',
            'プラン': 'plan',
            '企業': 'corporate',
            'オフィス': 'office',
            'スタッフ': 'staff',
        }
        for jp, en in required.items():
            assert jp in JP_KEYWORD_MAP, f"Missing: {jp}"
            assert JP_KEYWORD_MAP[jp] == en, f"{jp}: expected {en}, got {JP_KEYWORD_MAP[jp]}"


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

    def test_zero_grid(self):
        """grid=0 falls back to round()."""
        assert snap(2.5, grid=0) == round(2.5)

    def test_negative_grid(self):
        """grid=-1 falls back to round()."""
        assert snap(2.5, grid=-1) == round(2.5)


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

    def test_component_section_root(self):
        """COMPONENT type with width 1440 is a section root."""
        assert is_section_root({"type": "COMPONENT", "absoluteBoundingBox": {"width": 1440}}) is True

    def test_instance_section_root(self):
        """INSTANCE type with width 1440 is a section root."""
        assert is_section_root({"type": "INSTANCE", "absoluteBoundingBox": {"width": 1440}}) is True

    def test_section_section_root(self):
        """SECTION type with width 1440 is a section root."""
        assert is_section_root({"type": "SECTION", "absoluteBoundingBox": {"width": 1440}}) is True


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

    def test_rest_api_format(self):
        """Issue 177: Support Figma REST API format nodes.{id}.document"""
        data = {"nodes": {"38:718": {"document": {"id": "38:718", "type": "FRAME", "name": "Page"}}}}
        root = get_root_node(data)
        assert root["id"] == "38:718"
        assert root["name"] == "Page"

    def test_rest_api_multiple_nodes(self):
        """Issue 177: First node in nodes dict is returned"""
        data = {"nodes": {"1:1": {"document": {"id": "1:1"}}, "2:2": {"document": {"id": "2:2"}}}}
        root = get_root_node(data)
        assert root["id"] in ("1:1", "2:2")  # First node returned

    def test_rest_api_no_document(self):
        """Issue 177: nodes dict without document key falls through"""
        data = {"nodes": {"1:1": {"components": {}}}}
        # Should fall through to bare node behavior
        root = get_root_node(data)
        assert "nodes" in root  # Returns data itself as fallback


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
# _raw_distance
# ============================================================
class TestRawDistance:
    def test_overlapping_boxes(self):
        """Two overlapping boxes -> distance 0."""
        a = {"x": 0, "y": 0, "w": 100, "h": 50}
        b = {"x": 50, "y": 25, "w": 100, "h": 50}
        assert _raw_distance(a, b) == 0

    def test_touching_boxes(self):
        """Two touching boxes -> distance 0."""
        a = {"x": 0, "y": 0, "w": 100, "h": 50}
        b = {"x": 100, "y": 0, "w": 100, "h": 50}
        assert _raw_distance(a, b) == 0

    def test_containment(self):
        """One box fully inside another -> distance 0."""
        outer = {"x": 0, "y": 0, "w": 200, "h": 200}
        inner = {"x": 50, "y": 50, "w": 50, "h": 50}
        assert _raw_distance(outer, inner) == 0


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

    def test_zero_gap(self):
        """Issue 136: gap=0 returns 0.0 for non-overlapping boxes."""
        b = {"x": 200, "y": 0, "w": 100, "h": 50}
        assert compute_grouping_score(self.A, b, gap=0) == 0.0


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

    def test_children_but_no_type(self):
        """Node with children but missing type field produces 'UNKNOWN:[CHILD_TYPES]' hash."""
        node = {"children": [{"type": "TEXT"}, {"type": "TEXT"}]}
        result = structure_hash(node)
        assert result == "UNKNOWN:[TEXT,TEXT]"


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
# detect_consecutive_similar (Issue 165)
# ============================================================
class TestDetectConsecutiveSimilar:
    def _make_frame(self, name, child_types):
        """Helper to create a frame with typed children."""
        return {
            "type": "FRAME", "name": name,
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 100, "height": 100},
            "children": [{"type": t, "name": f"{t} {i}"}
                         for i, t in enumerate(child_types)],
        }

    def test_three_consecutive_similar(self):
        """3 consecutive frames with FRAME:[FRAME,TEXT] → should group."""
        children = [
            self._make_frame("menu-1", ["FRAME", "TEXT"]),
            self._make_frame("menu-2", ["FRAME", "TEXT"]),
            self._make_frame("menu-3", ["FRAME", "TEXT"]),
        ]
        groups = detect_consecutive_similar(children)
        assert len(groups) == 1
        assert groups[0]['indices'] == [0, 1, 2]
        assert len(groups[0]['children']) == 3

    def test_non_consecutive_not_grouped(self):
        """Similar frames separated by a different frame → no group."""
        children = [
            self._make_frame("menu-1", ["FRAME", "TEXT"]),
            self._make_frame("different", ["IMAGE", "RECTANGLE"]),
            self._make_frame("menu-2", ["FRAME", "TEXT"]),
            self._make_frame("menu-3", ["FRAME", "TEXT"]),
        ]
        groups = detect_consecutive_similar(children)
        assert len(groups) == 0  # only 2 consecutive, not 3

    def test_too_few(self):
        """Only 2 similar frames → below min_count threshold."""
        children = [
            self._make_frame("a", ["TEXT"]),
            self._make_frame("b", ["TEXT"]),
        ]
        groups = detect_consecutive_similar(children)
        assert len(groups) == 0

    def test_custom_min_count(self):
        """Custom min_count=2 → group of 2."""
        children = [
            self._make_frame("a", ["TEXT"]),
            self._make_frame("b", ["TEXT"]),
        ]
        groups = detect_consecutive_similar(children, min_count=2)
        assert len(groups) == 1

    def test_mixed_but_similar(self):
        """Fuzzy match: FRAME:[FRAME,TEXT] vs FRAME:[TEXT,FRAME] → same hash (sorted)."""
        children = [
            self._make_frame("a", ["FRAME", "TEXT"]),
            self._make_frame("b", ["TEXT", "FRAME"]),
            self._make_frame("c", ["FRAME", "TEXT"]),
        ]
        groups = detect_consecutive_similar(children)
        assert len(groups) == 1

    def test_empty_children(self):
        """Empty input → no groups."""
        assert detect_consecutive_similar([]) == []

    def test_two_separate_runs(self):
        """Two separate consecutive runs with a break."""
        children = [
            self._make_frame("a1", ["TEXT"]),
            self._make_frame("a2", ["TEXT"]),
            self._make_frame("a3", ["TEXT"]),
            self._make_frame("break", ["IMAGE", "RECTANGLE", "VECTOR"]),
            self._make_frame("b1", ["TEXT"]),
            self._make_frame("b2", ["TEXT"]),
            self._make_frame("b3", ["TEXT"]),
        ]
        groups = detect_consecutive_similar(children)
        assert len(groups) == 2
        assert groups[0]['indices'] == [0, 1, 2]
        assert groups[1]['indices'] == [4, 5, 6]


# ============================================================
# is_heading_like / detect_heading_content_pairs (Issue 166)
# ============================================================
class TestIsHeadingLike:
    def test_text_heavy_frame(self):
        """Frame with mostly TEXT/VECTOR children → heading-like."""
        node = {
            "type": "FRAME",
            "children": [
                {"type": "TEXT", "children": []},
                {"type": "TEXT", "children": []},
                {"type": "VECTOR", "children": []},
            ],
        }
        assert is_heading_like(node) is True

    def test_image_heavy_frame(self):
        """Frame with mostly RECTANGLE/IMAGE → not heading-like."""
        node = {
            "type": "FRAME",
            "children": [
                {"type": "RECTANGLE", "children": []},
                {"type": "IMAGE", "children": []},
                {"type": "TEXT", "children": []},
            ],
        }
        assert is_heading_like(node) is False

    def test_empty_frame(self):
        """Frame with no children → not heading-like."""
        assert is_heading_like({"type": "FRAME", "children": []}) is False

    def test_leaf_node(self):
        """Leaf node (no children key) → not heading-like."""
        assert is_heading_like({"type": "TEXT"}) is False

    def test_too_many_children(self):
        """Frame with > HEADING_MAX_CHILDREN → not heading-like."""
        node = {
            "type": "FRAME",
            "children": [{"type": "TEXT", "children": []} for _ in range(6)],
        }
        assert is_heading_like(node) is False

    def test_nested_text(self):
        """Frame with nested TEXT descendants → heading-like."""
        node = {
            "type": "FRAME",
            "children": [
                {"type": "FRAME", "children": [
                    {"type": "TEXT", "children": []},
                    {"type": "TEXT", "children": []},
                ]},
                {"type": "ELLIPSE", "children": []},
            ],
        }
        assert is_heading_like(node) is True

    # --- Issue 175: ELLIPSE decoration false positive ---

    def test_is_heading_like_ellipse_only_false(self):
        """Frame with 3 ELLIPSE children, 0 TEXT → not heading-like."""
        node = {
            "type": "FRAME",
            "children": [
                {"type": "ELLIPSE", "children": []},
                {"type": "ELLIPSE", "children": []},
                {"type": "ELLIPSE", "children": []},
            ],
        }
        assert is_heading_like(node) is False

    def test_is_heading_like_ellipse_dominated_false(self):
        """Frame with 3 ELLIPSE + 1 TEXT → not heading-like (ELLIPSE > TEXT)."""
        node = {
            "type": "FRAME",
            "children": [
                {"type": "ELLIPSE", "children": []},
                {"type": "ELLIPSE", "children": []},
                {"type": "ELLIPSE", "children": []},
                {"type": "TEXT", "children": []},
            ],
        }
        assert is_heading_like(node) is False

    def test_is_heading_like_text_with_ellipse_true(self):
        """Frame with 2 TEXT + 1 ELLIPSE → heading-like (TEXT > ELLIPSE)."""
        node = {
            "type": "FRAME",
            "children": [
                {"type": "TEXT", "children": []},
                {"type": "TEXT", "children": []},
                {"type": "ELLIPSE", "children": []},
            ],
        }
        assert is_heading_like(node) is True

    def test_is_heading_like_equal_text_ellipse_true(self):
        """Frame with 2 TEXT + 2 ELLIPSE → heading-like (TEXT == ELLIPSE)."""
        node = {
            "type": "FRAME",
            "children": [
                {"type": "TEXT", "children": []},
                {"type": "TEXT", "children": []},
                {"type": "ELLIPSE", "children": []},
                {"type": "ELLIPSE", "children": []},
            ],
        }
        assert is_heading_like(node) is True


class TestDetectHeadingContentPairs:
    def test_heading_content_pair(self):
        """Small heading frame (h=215) + large content frame (h=746) → pair."""
        children = [
            {
                "type": "FRAME", "name": "section-heading",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 215},
                "children": [
                    {"type": "TEXT", "children": []},
                    {"type": "VECTOR", "children": []},
                ],
            },
            {
                "type": "FRAME", "name": "section-content",
                "absoluteBoundingBox": {"x": 0, "y": 215, "width": 1440, "height": 746},
                "children": [
                    {"type": "TEXT", "children": []},
                    {"type": "FRAME", "children": [
                        {"type": "TEXT", "children": []},
                    ]},
                ],
            },
        ]
        pairs = detect_heading_content_pairs(children)
        assert len(pairs) == 1
        assert pairs[0]['heading_idx'] == 0
        assert pairs[0]['content_idx'] == 1

    def test_equal_height_not_paired(self):
        """Two frames of equal height → no pair."""
        children = [
            {
                "type": "FRAME", "name": "a",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                "children": [{"type": "TEXT", "children": []}],
            },
            {
                "type": "FRAME", "name": "b",
                "absoluteBoundingBox": {"x": 0, "y": 500, "width": 1440, "height": 500},
                "children": [{"type": "TEXT", "children": []}],
            },
        ]
        pairs = detect_heading_content_pairs(children)
        assert len(pairs) == 0

    def test_content_must_be_frame(self):
        """Heading followed by TEXT (not FRAME) → no pair."""
        children = [
            {
                "type": "FRAME", "name": "heading",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 100},
                "children": [{"type": "TEXT", "children": []}],
            },
            {
                "type": "TEXT", "name": "text",
                "absoluteBoundingBox": {"x": 0, "y": 100, "width": 1440, "height": 500},
            },
        ]
        pairs = detect_heading_content_pairs(children)
        assert len(pairs) == 0

    def test_content_must_have_children(self):
        """Heading followed by empty FRAME → no pair."""
        children = [
            {
                "type": "FRAME", "name": "heading",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 100},
                "children": [{"type": "TEXT", "children": []}],
            },
            {
                "type": "FRAME", "name": "empty",
                "absoluteBoundingBox": {"x": 0, "y": 100, "width": 1440, "height": 500},
                "children": [],
            },
        ]
        pairs = detect_heading_content_pairs(children)
        assert len(pairs) == 0

    def test_single_child(self):
        """Only one child → no pairs."""
        children = [
            {
                "type": "FRAME", "name": "only",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 100},
                "children": [{"type": "TEXT", "children": []}],
            },
        ]
        pairs = detect_heading_content_pairs(children)
        assert len(pairs) == 0

    def test_multiple_pairs(self):
        """Two heading-content pairs in sequence."""
        children = [
            {
                "type": "FRAME", "name": "h1",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 100},
                "children": [{"type": "TEXT", "children": []}],
            },
            {
                "type": "FRAME", "name": "c1",
                "absoluteBoundingBox": {"x": 0, "y": 100, "width": 1440, "height": 600},
                "children": [{"type": "TEXT", "children": []}],
            },
            {
                "type": "FRAME", "name": "h2",
                "absoluteBoundingBox": {"x": 0, "y": 700, "width": 1440, "height": 80},
                "children": [{"type": "TEXT", "children": []}, {"type": "VECTOR", "children": []}],
            },
            {
                "type": "FRAME", "name": "c2",
                "absoluteBoundingBox": {"x": 0, "y": 780, "width": 1440, "height": 500},
                "children": [{"type": "FRAME", "children": [{"type": "TEXT", "children": []}]}],
            },
        ]
        pairs = detect_heading_content_pairs(children)
        assert len(pairs) == 2


# ============================================================
# find_absorbable_elements (Issue 167)
# ============================================================
class TestFindAbsorbableElements:
    def test_line_absorbed(self):
        """LINE element between two grouped frames → absorbed."""
        children = [
            {"type": "FRAME", "name": "section-a",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500}},
            {"type": "LINE", "name": "divider",
             "absoluteBoundingBox": {"x": 0, "y": 510, "width": 1440, "height": 1}},
            {"type": "FRAME", "name": "section-b",
             "absoluteBoundingBox": {"x": 0, "y": 530, "width": 1440, "height": 600}},
        ]
        group_indices = {0, 2}
        absorptions = find_absorbable_elements(children, group_indices)
        assert len(absorptions) == 1
        assert absorptions[0]['element_idx'] == 1
        assert absorptions[0]['target_group_idx'] in (0, 2)
        assert 'LINE' in absorptions[0]['reason']

    def test_small_rect_absorbed(self):
        """Small RECTANGLE (h=5) → absorbed as divider."""
        children = [
            {"type": "FRAME", "name": "section",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500}},
            {"type": "RECTANGLE", "name": "Rectangle 1",
             "absoluteBoundingBox": {"x": 0, "y": 510, "width": 1440, "height": 5}},
        ]
        group_indices = {0}
        absorptions = find_absorbable_elements(children, group_indices)
        assert len(absorptions) == 1
        assert absorptions[0]['element_idx'] == 1

    def test_large_frame_not_absorbed(self):
        """Large FRAME (h=500) → not absorbed."""
        children = [
            {"type": "FRAME", "name": "section",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500}},
            {"type": "FRAME", "name": "Frame 2",
             "absoluteBoundingBox": {"x": 0, "y": 510, "width": 1440, "height": 500},
             "children": [{"type": "TEXT"}]},
        ]
        group_indices = {0}
        absorptions = find_absorbable_elements(children, group_indices)
        assert len(absorptions) == 0

    def test_too_far_not_absorbed(self):
        """LINE element > LOOSE_ABSORPTION_DISTANCE away → not absorbed."""
        children = [
            {"type": "FRAME", "name": "section",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500}},
            {"type": "LINE", "name": "far-divider",
             "absoluteBoundingBox": {"x": 0, "y": 800, "width": 1440, "height": 1}},
        ]
        group_indices = {0}
        absorptions = find_absorbable_elements(children, group_indices)
        assert len(absorptions) == 0  # distance = 300 > 200

    def test_already_grouped_skipped(self):
        """Elements already in groups → skipped."""
        children = [
            {"type": "LINE", "name": "divider",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1}},
        ]
        group_indices = {0}
        absorptions = find_absorbable_elements(children, group_indices)
        assert len(absorptions) == 0

    def test_empty_inputs(self):
        """Empty children → no absorptions."""
        assert find_absorbable_elements([], set()) == []

    def test_nearest_group_chosen(self):
        """LINE closer to group B than group A → absorbed into B."""
        children = [
            {"type": "FRAME", "name": "A",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 200}},
            {"type": "LINE", "name": "divider",
             "absoluteBoundingBox": {"x": 0, "y": 410, "width": 1440, "height": 1}},
            {"type": "FRAME", "name": "B",
             "absoluteBoundingBox": {"x": 0, "y": 420, "width": 1440, "height": 300}},
        ]
        group_indices = {0, 2}
        absorptions = find_absorbable_elements(children, group_indices)
        assert len(absorptions) == 1
        # B is at y=420, divider bottom is at y=411, distance = 9
        # A bottom is at y=200, divider top is at y=410, distance = 210 (> LOOSE_ABSORPTION_DISTANCE)
        # But both are checked; B is closer
        assert absorptions[0]['target_group_idx'] == 2

    def test_zone_bbox_absorbs_divider_within_span(self):
        """LINE inside a zone's vertical span -> absorbed via zone bbox even if
        individual members are far away (root-level divider fix)."""
        # Zone has two members: y=4269..4500 and y=4800..5015
        # LINE at y=4706 is between them but inside the zone's bounding box.
        children = [
            {"id": "m1", "type": "FRAME", "name": "zone-member-1",
             "absoluteBoundingBox": {"x": 0, "y": 4269, "width": 1440, "height": 231}},
            {"id": "d1", "type": "LINE", "name": "divider-28",
             "absoluteBoundingBox": {"x": 100, "y": 4706, "width": 1240, "height": 1}},
            {"id": "m2", "type": "FRAME", "name": "zone-member-2",
             "absoluteBoundingBox": {"x": 0, "y": 4800, "width": 1440, "height": 215}},
        ]
        group_indices = {0, 2}
        # Without candidate_groups: m1 bottom=4500, divider top=4706 => dist=206 > 200
        #   m2 top=4800, divider bottom=4707 => dist=93 < 200, so absorbed by member-level.
        absorptions_no_zone = find_absorbable_elements(children, group_indices)
        assert len(absorptions_no_zone) == 1

        # With candidate_groups: zone bbox y=4269..5015, divider center=4706.5 inside
        candidate_groups = [{"node_ids": ["m1", "m2"]}]
        absorptions_zone = find_absorbable_elements(children, group_indices, candidate_groups=candidate_groups)
        assert len(absorptions_zone) == 1
        assert absorptions_zone[0]['distance'] == 0.0

    def test_zone_bbox_absorbs_distant_divider(self):
        """LINE far from individual members but inside zone span -> absorbed."""
        # Zone members at y=100..300 and y=900..1100, divider at y=600
        # Member distances: 600-300=300 > 200, and 900-601=299 > 200
        # But zone spans 100..1100, so divider center y=600.5 is inside.
        children = [
            {"id": "a", "type": "FRAME", "name": "top-member",
             "absoluteBoundingBox": {"x": 0, "y": 100, "width": 1440, "height": 200}},
            {"id": "div", "type": "LINE", "name": "divider",
             "absoluteBoundingBox": {"x": 0, "y": 600, "width": 1440, "height": 1}},
            {"id": "b", "type": "FRAME", "name": "bottom-member",
             "absoluteBoundingBox": {"x": 0, "y": 900, "width": 1440, "height": 200}},
        ]
        group_indices = {0, 2}
        # Without zone: both distances > 200 -> not absorbed
        absorptions_no_zone = find_absorbable_elements(children, group_indices)
        assert len(absorptions_no_zone) == 0

        # With zone: center y=600.5 is within [100, 1100] -> absorbed
        candidate_groups = [{"node_ids": ["a", "b"]}]
        absorptions_zone = find_absorbable_elements(children, group_indices, candidate_groups=candidate_groups)
        assert len(absorptions_zone) == 1
        assert absorptions_zone[0]['distance'] == 0.0
        assert absorptions_zone[0]['element_idx'] == 1

    def test_zone_bbox_outside_not_absorbed(self):
        """LINE outside all zone bounding boxes and far from members -> not absorbed."""
        children = [
            {"id": "m1", "type": "FRAME", "name": "member",
             "absoluteBoundingBox": {"x": 0, "y": 100, "width": 1440, "height": 200}},
            {"id": "div", "type": "LINE", "name": "far-divider",
             "absoluteBoundingBox": {"x": 0, "y": 800, "width": 1440, "height": 1}},
        ]
        group_indices = {0}
        # Zone spans y=100..300, divider at y=800 is outside and 500px away
        candidate_groups = [{"node_ids": ["m1"]}]
        absorptions = find_absorbable_elements(children, group_indices, candidate_groups=candidate_groups)
        assert len(absorptions) == 0

    def test_zone_bbox_two_dividers_same_zone(self):
        """Two LINE elements within same zone span -> both absorbed."""
        children = [
            {"id": "m1", "type": "FRAME", "name": "section-top",
             "absoluteBoundingBox": {"x": 0, "y": 4000, "width": 1440, "height": 300}},
            {"id": "d1", "type": "LINE", "name": "divider-1",
             "absoluteBoundingBox": {"x": 100, "y": 4500, "width": 1240, "height": 1}},
            {"id": "d2", "type": "LINE", "name": "divider-2",
             "absoluteBoundingBox": {"x": 100, "y": 4700, "width": 1240, "height": 1}},
            {"id": "m2", "type": "FRAME", "name": "section-bottom",
             "absoluteBoundingBox": {"x": 0, "y": 4800, "width": 1440, "height": 300}},
        ]
        group_indices = {0, 3}
        candidate_groups = [{"node_ids": ["m1", "m2"]}]
        absorptions = find_absorbable_elements(children, group_indices, candidate_groups=candidate_groups)
        assert len(absorptions) == 2
        absorbed_indices = {a['element_idx'] for a in absorptions}
        assert absorbed_indices == {1, 2}

    def test_candidate_groups_none_backward_compat(self):
        """candidate_groups=None -> backward compatible member-level only."""
        children = [
            {"id": "s", "type": "FRAME", "name": "section",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500}},
            {"id": "d", "type": "LINE", "name": "divider",
             "absoluteBoundingBox": {"x": 0, "y": 510, "width": 1440, "height": 1}},
        ]
        group_indices = {0}
        absorptions = find_absorbable_elements(children, group_indices, candidate_groups=None)
        assert len(absorptions) == 1
        assert absorptions[0]['element_idx'] == 1


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
            # Issue 170: お問い合わせ → contact via JP_KEYWORD_MAP
            assert "contact" in r1.get("new_name", ""), \
                f"Expected 'contact' in {r1.get('new_name', '')}"
            r2 = renames.get("1:2", {})
            name = r2.get("new_name", "")
            # Issue 170: 募集要項 → recruit via JP_KEYWORD_MAP, or REASON → reason
            assert "recruit" in name or "reason" in name or "heading" in name, \
                f"Expected 'recruit'/'reason'/'heading' in {name}"
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

    def test_image_wrapper_card_detection(self):
        """Image wrapped in sub-frame + TEXT caption should be card-*, not heading-*."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1000},
            "children": [
                # Menu item: FRAME containing [FRAME(with rectangles), TEXT]
                # This pattern is common for food/product cards with image + caption
                {"id": "1:1", "name": "Frame 1", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 0, "width": 250, "height": 245},
                 "children": [
                     # Image wrapper frame with rectangles (photo overlays)
                     {"id": "1:2", "name": "Group 1", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 0, "y": 0, "width": 230, "height": 173},
                      "children": [
                          {"id": "1:3", "name": "Rectangle 1", "type": "RECTANGLE",
                           "absoluteBoundingBox": {"x": 0, "y": 0, "width": 230, "height": 173},
                           "children": []},
                          {"id": "1:4", "name": "Rectangle 2", "type": "RECTANGLE",
                           "absoluteBoundingBox": {"x": 10, "y": 10, "width": 210, "height": 153},
                           "children": []},
                      ]},
                     # Caption text
                     {"id": "1:5", "name": "Text 1", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 0, "y": 180, "width": 230, "height": 40},
                      "characters": "finger food",
                      "children": []},
                 ]},
                # Second card item with different text
                {"id": "2:1", "name": "Frame 2", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 260, "y": 0, "width": 250, "height": 245},
                 "children": [
                     {"id": "2:2", "name": "Group 2", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 0, "y": 0, "width": 230, "height": 173},
                      "children": [
                          {"id": "2:3", "name": "Rectangle 3", "type": "RECTANGLE",
                           "absoluteBoundingBox": {"x": 0, "y": 0, "width": 230, "height": 173},
                           "children": []},
                      ]},
                     {"id": "2:4", "name": "Text 2", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 0, "y": 180, "width": 230, "height": 40},
                      "characters": "catering service",
                      "children": []},
                 ]},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("generate-rename-map.sh", tmp)
            renames = data.get("renames", {})
            # Frame 1 (image-wrapper + text) must be card-*, not heading-*
            r1 = renames.get("1:1", {})
            assert r1.get("new_name", "").startswith("card-"), \
                f"Expected card-* for image-wrapper+text, got: {r1.get('new_name', '')}"
            # Frame 2 similarly
            r2 = renames.get("2:1", {})
            assert r2.get("new_name", "").startswith("card-"), \
                f"Expected card-* for image-wrapper+text, got: {r2.get('new_name', '')}"
            # Verify the card slug uses text content
            assert "finger-food" in r1["new_name"], \
                f"Expected slug from text content, got: {r1['new_name']}"
            assert "catering-service" in r2["new_name"], \
                f"Expected slug from text content, got: {r2['new_name']}"
        finally:
            os.unlink(tmp)

    def test_consecutive_pattern_detection(self):
        """Issue 165: 3 consecutive similar frames grouped at root level."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 5000},
            "children": [
                {"id": "1:1", "name": "HEADER", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 80},
                 "children": []},
                # 3 consecutive similar frames (each has FRAME + TEXT child)
                {"id": "2:1", "name": "section-menu-1", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 200, "width": 1440, "height": 600},
                 "children": [
                     {"id": "2:10", "name": "Frame 1", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 0, "y": 0, "width": 500, "height": 400}},
                     {"id": "2:11", "name": "Text 1", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 0, "y": 400, "width": 500, "height": 40},
                      "characters": "Menu 1"},
                 ]},
                {"id": "2:2", "name": "section-menu-2", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 820, "width": 1440, "height": 600},
                 "children": [
                     {"id": "2:20", "name": "Frame 2", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 0, "y": 0, "width": 500, "height": 400}},
                     {"id": "2:21", "name": "Text 2", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 0, "y": 400, "width": 500, "height": 40},
                      "characters": "Menu 2"},
                 ]},
                {"id": "2:3", "name": "section-menu-3", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 1440, "width": 1440, "height": 600},
                 "children": [
                     {"id": "2:30", "name": "Frame 3", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 0, "y": 0, "width": 500, "height": 400}},
                     {"id": "2:31", "name": "Text 3", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 0, "y": 400, "width": 500, "height": 40},
                      "characters": "Menu 3"},
                 ]},
                {"id": "3:1", "name": "FOOTER", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 4800, "width": 1440, "height": 200},
                 "children": []},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("detect-grouping-candidates.sh", tmp)
            consecutive = [c for c in data["candidates"] if c.get("method") == "consecutive"]
            assert len(consecutive) >= 1, \
                f"No consecutive groups found. Methods: {[c['method'] for c in data['candidates']]}"
            # All 3 menu frames should be in the group
            group_ids = set(consecutive[0]["node_ids"])
            assert "2:1" in group_ids
            assert "2:2" in group_ids
            assert "2:3" in group_ids
            # Suggested name should be list-based
            assert consecutive[0]["suggested_name"].startswith("list-")
        finally:
            os.unlink(tmp)

    def test_heading_content_pair_detection(self):
        """Issue 166: Small heading frame + large content frame paired."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 5000},
            "children": [
                {"id": "1:1", "name": "HEADER", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 80},
                 "children": []},
                # Heading frame (small, text-heavy; TEXT >= ELLIPSE per Issue 175)
                {"id": "2:1", "name": "section-our-concept", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 200, "width": 1440, "height": 215},
                 "children": [
                     {"id": "2:10", "name": "Text 1", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 200, "y": 50, "width": 400, "height": 60},
                      "characters": "OUR CONCEPT"},
                     {"id": "2:13", "name": "Text 2", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 200, "y": 120, "width": 400, "height": 30},
                      "characters": "Our philosophy"},
                     {"id": "2:11", "name": "Ellipse 1", "type": "ELLIPSE",
                      "absoluteBoundingBox": {"x": 300, "y": 160, "width": 10, "height": 10}},
                     {"id": "2:12", "name": "Ellipse 2", "type": "ELLIPSE",
                      "absoluteBoundingBox": {"x": 320, "y": 160, "width": 10, "height": 10}},
                 ]},
                # Content frame (large, complex)
                {"id": "2:2", "name": "section-concept-detail", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 415, "width": 1440, "height": 746},
                 "children": [
                     {"id": "2:20", "name": "Text 2", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 100, "y": 50, "width": 800, "height": 200},
                      "characters": "Detail text"},
                     {"id": "2:21", "name": "Frame 1", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 100, "y": 300, "width": 600, "height": 300},
                      "children": [
                          {"id": "2:22", "name": "Tag 1", "type": "TEXT",
                           "absoluteBoundingBox": {"x": 0, "y": 0, "width": 100, "height": 30},
                           "characters": "Tag"},
                      ]},
                 ]},
                {"id": "3:1", "name": "FOOTER", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 4800, "width": 1440, "height": 200},
                 "children": []},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("detect-grouping-candidates.sh", tmp)
            hc_pairs = [c for c in data["candidates"] if c.get("method") == "heading-content"]
            assert len(hc_pairs) >= 1, \
                f"No heading-content pairs found. Methods: {[c['method'] for c in data['candidates']]}"
            pair_ids = set(hc_pairs[0]["node_ids"])
            assert "2:1" in pair_ids, "Heading not in pair"
            assert "2:2" in pair_ids, "Content not in pair"
            # Suggested name should contain concept slug
            assert "section-" in hc_pairs[0]["suggested_name"]
        finally:
            os.unlink(tmp)

    def test_loose_element_absorption(self):
        """Issue 167: LINE dividers absorbed into nearest group."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 5000},
            "children": [
                # Three consecutive similar frames (will form a consecutive group)
                {"id": "2:1", "name": "section-menu-1", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 600},
                 "children": [
                     {"id": "2:10", "type": "FRAME", "name": "F1",
                      "absoluteBoundingBox": {"x": 0, "y": 0, "width": 400, "height": 400}},
                     {"id": "2:11", "type": "TEXT", "name": "T1",
                      "absoluteBoundingBox": {"x": 0, "y": 400, "width": 400, "height": 40},
                      "characters": "Item 1"},
                 ]},
                # Loose LINE divider between menu-1 and menu-2
                {"id": "9:1", "name": "divider-1", "type": "LINE",
                 "absoluteBoundingBox": {"x": 0, "y": 610, "width": 1440, "height": 1}},
                {"id": "2:2", "name": "section-menu-2", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 620, "width": 1440, "height": 600},
                 "children": [
                     {"id": "2:20", "type": "FRAME", "name": "F2",
                      "absoluteBoundingBox": {"x": 0, "y": 0, "width": 400, "height": 400}},
                     {"id": "2:21", "type": "TEXT", "name": "T2",
                      "absoluteBoundingBox": {"x": 0, "y": 400, "width": 400, "height": 40},
                      "characters": "Item 2"},
                 ]},
                # Another loose divider
                {"id": "9:2", "name": "divider-2", "type": "LINE",
                 "absoluteBoundingBox": {"x": 0, "y": 1230, "width": 1440, "height": 1}},
                {"id": "2:3", "name": "section-menu-3", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 1240, "width": 1440, "height": 600},
                 "children": [
                     {"id": "2:30", "type": "FRAME", "name": "F3",
                      "absoluteBoundingBox": {"x": 0, "y": 0, "width": 400, "height": 400}},
                     {"id": "2:31", "type": "TEXT", "name": "T3",
                      "absoluteBoundingBox": {"x": 0, "y": 400, "width": 400, "height": 40},
                      "characters": "Item 3"},
                 ]},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("detect-grouping-candidates.sh", tmp)
            # Check that dividers were absorbed into a group
            all_grouped_ids = set()
            for c in data["candidates"]:
                all_grouped_ids.update(c.get("node_ids", []))
            # At least one divider should be absorbed
            divider_absorbed = "9:1" in all_grouped_ids or "9:2" in all_grouped_ids
            assert divider_absorbed, \
                f"No dividers absorbed. Grouped IDs: {all_grouped_ids}"
        finally:
            os.unlink(tmp)

    def test_semantic_group_naming_from_child_text(self):
        """Issue 174: group-N / container-N should use semantic slug from child text."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 3000},
            "children": [
                # FRAME with 4 child FRAMEs, each with TEXT children (Japanese)
                # This should get group-{slug} instead of group-0
                {"id": "1:1", "name": "Frame 1", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 100, "y": 100, "width": 600, "height": 800},
                 "children": [
                     {"id": "1:10", "name": "Frame 10", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 100, "y": 100, "width": 500, "height": 180},
                      "children": [
                          {"id": "1:11", "name": "Text 1", "type": "TEXT",
                           "absoluteBoundingBox": {"x": 110, "y": 110, "width": 200, "height": 30},
                           "characters": "サービスについて", "children": []},
                      ]},
                     {"id": "1:20", "name": "Frame 11", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 100, "y": 300, "width": 500, "height": 180},
                      "children": [
                          {"id": "1:21", "name": "Text 2", "type": "TEXT",
                           "absoluteBoundingBox": {"x": 110, "y": 310, "width": 200, "height": 30},
                           "characters": "詳しくはこちら", "children": []},
                      ]},
                     {"id": "1:30", "name": "Frame 12", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 100, "y": 500, "width": 500, "height": 180},
                      "children": [
                          {"id": "1:31", "name": "Text 3", "type": "TEXT",
                           "absoluteBoundingBox": {"x": 110, "y": 510, "width": 200, "height": 30},
                           "characters": "お問い合わせ", "children": []},
                      ]},
                     {"id": "1:40", "name": "Frame 13", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 100, "y": 700, "width": 500, "height": 180},
                      "children": [
                          {"id": "1:41", "name": "Text 4", "type": "TEXT",
                           "absoluteBoundingBox": {"x": 110, "y": 710, "width": 200, "height": 30},
                           "characters": "料金プラン", "children": []},
                      ]},
                 ]},
                # FRAME with 6+ child FRAMEs -> container-{slug}
                {"id": "2:1", "name": "Frame 2", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 100, "y": 1000, "width": 600, "height": 1200},
                 "children": [
                     {"id": f"2:{10+i}", "name": f"Frame {20+i}", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 100, "y": 1000 + i * 180, "width": 500, "height": 160},
                      "children": [
                          {"id": f"2:{50+i}", "name": f"Text {10+i}", "type": "TEXT",
                           "absoluteBoundingBox": {"x": 110, "y": 1010 + i * 180, "width": 200, "height": 30},
                           "characters": "ケータリング" if i == 0 else f"Item {i}",
                           "children": []},
                      ]}
                     for i in range(6)
                 ]},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("generate-rename-map.sh", tmp)
            renames = data.get("renames", {})
            # 1:1 has 4 children, each with JP text -> should be group-{slug}
            r1 = renames.get("1:1", {})
            name1 = r1.get("new_name", "")
            assert name1.startswith("group-"), \
                f"Expected group-* for 4-child frame, got: {name1}"
            # Must NOT end with numeric index -- should have semantic slug
            assert not name1.split("-")[-1].isdigit(), \
                f"Expected semantic slug, not numeric index: {name1}"
            # Should contain 'service' from 'サービスについて' (first text child)
            assert "service" in name1, \
                f"Expected 'service' slug from 'サービスについて', got: {name1}"

            # 2:1 has 6 children -> should be container-{slug}
            r2 = renames.get("2:1", {})
            name2 = r2.get("new_name", "")
            assert name2.startswith("container-"), \
                f"Expected container-* for 6-child frame, got: {name2}"
            # Must have semantic slug, not numeric
            assert not name2.split("-")[-1].isdigit(), \
                f"Expected semantic slug, not numeric index: {name2}"
            # Should contain 'catering' from 'ケータリング' (first grandchild text)
            assert "catering" in name2, \
                f"Expected 'catering' slug from 'ケータリング', got: {name2}"
        finally:
            os.unlink(tmp)

    def test_semantic_group_naming_fallback_to_index(self):
        """Issue 174: group-N fallback when no text content is available."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
            "children": [
                # FRAME with 4 child FRAMEs, none with TEXT → falls back to group-N
                {"id": "1:1", "name": "Frame 1", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 100, "y": 100, "width": 600, "height": 800},
                 "children": [
                     {"id": f"1:{10+i}", "name": f"Frame {10+i}", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 100, "y": 100 + i * 200, "width": 500, "height": 180},
                      "children": [
                          {"id": f"1:{20+i}", "name": f"Rectangle {i}", "type": "RECTANGLE",
                           "absoluteBoundingBox": {"x": 110, "y": 110 + i * 200, "width": 200, "height": 150},
                           "children": []},
                      ]}
                     for i in range(4)
                 ]},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("generate-rename-map.sh", tmp)
            renames = data.get("renames", {})
            r1 = renames.get("1:1", {})
            name1 = r1.get("new_name", "")
            # No text children → should fall back to group-{index}
            assert name1.startswith("group-"), \
                f"Expected group-* fallback, got: {name1}"
            assert name1 == "group-0", \
                f"Expected group-0 (numeric fallback), got: {name1}"
        finally:
            os.unlink(tmp)

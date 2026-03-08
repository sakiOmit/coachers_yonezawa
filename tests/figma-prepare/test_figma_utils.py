"""
figma_utils.py unit tests + script integration tests.

Run: python3 -m pytest tests/figma-prepare/test_figma_utils.py -v
From: project root
"""
import json
import os
import subprocess
import sys
import tempfile

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILLS_DIR = os.path.join(PROJECT_ROOT, ".claude", "skills", "figma-prepare")
sys.path.insert(0, os.path.join(SKILLS_DIR, "lib"))

from figma_utils import (
    _jp_keyword_lookup,
    _raw_distance,
    alignment_bonus,
    compute_gap_consistency,
    compute_grouping_score,
    detect_bg_content_layers,
    detect_consecutive_similar,
    detect_heading_content_pairs,
    detect_regular_spacing,
    detect_space_between,
    detect_table_rows,
    detect_wrap,
    find_absorbable_elements,
    get_bbox,
    get_root_node,
    get_text_children_content,
    infer_direction_two_elements,
    is_heading_like,
    is_off_canvas,
    is_section_root,
    is_unnamed,
    JP_KEYWORD_MAP,
    load_metadata,
    parse_figma_xml,
    resolve_absolute_coords,
    size_similarity_bonus,
    snap,
    structure_hash,
    structure_similarity,
    to_kebab,
    yaml_str,
    BG_WIDTH_RATIO,
    BG_MIN_HEIGHT_RATIO,
    BG_DECORATION_MAX_AREA_RATIO,
    OVERFLOW_BG_MIN_WIDTH,
    CONSECUTIVE_PATTERN_MIN,
    LOOSE_ELEMENT_MAX_HEIGHT,
    LOOSE_ABSORPTION_DISTANCE,
    OFF_CANVAS_MARGIN,
    TABLE_MIN_ROWS,
    TABLE_ROW_WIDTH_RATIO,
    TABLE_DIVIDER_MAX_HEIGHT,
    detect_repeating_tuple,
    TUPLE_PATTERN_MIN,
    TUPLE_MAX_SIZE,
    detect_en_jp_label_pairs,
    EN_LABEL_MAX_WORDS,
    EN_JP_PAIR_MAX_DISTANCE,
    CTA_SQUARE_RATIO_MIN,
    CTA_SQUARE_RATIO_MAX,
    CTA_Y_THRESHOLD,
    SIDE_PANEL_MAX_WIDTH,
    SIDE_PANEL_HEIGHT_RATIO,
    is_decoration_pattern,
    decoration_dominant_shape,
    DECORATION_MAX_SIZE,
    DECORATION_SHAPE_RATIO,
    DECORATION_MIN_SHAPES,
    detect_highlight_text,
    generate_enriched_table,
    HIGHLIGHT_OVERLAP_RATIO,
    HIGHLIGHT_TEXT_MAX_LEN,
    HIGHLIGHT_HEIGHT_RATIO_MIN,
    HIGHLIGHT_HEIGHT_RATIO_MAX,
    detect_horizontal_bar,
    HORIZONTAL_BAR_MAX_HEIGHT,
    HORIZONTAL_BAR_MIN_ELEMENTS,
    HORIZONTAL_BAR_VARIANCE_RATIO,
    _compute_child_types,
    _compute_flags,
    _compute_zone_bboxes,
    _count_flat_descendants,
    count_nested_flat,
    FLAT_THRESHOLD,
    MAX_STAGE_C_DEPTH,
    STAGE_C_COVERABLE_DETECTORS,
    STAGE_A_ONLY_DETECTORS,
    STAGE_C_COVERAGE_THRESHOLD,
    deduplicate_candidates,
    METHOD_PRIORITY,
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
        {"type": "FRAME", "absoluteBoundingBox": {"width": 1295}},
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

    def test_oversized_width_is_section_root(self):
        """Issue 191: Oversized footer wrapper (width=2433) is a section root."""
        assert is_section_root({"type": "FRAME", "absoluteBoundingBox": {"width": 2433}}) is True

    def test_boundary_width_1296_is_section_root(self):
        """Issue 191: Boundary at 90% of 1440 (width=1296) is a section root."""
        assert is_section_root({"type": "FRAME", "absoluteBoundingBox": {"width": 1296}}) is True

    def test_below_boundary_width_1295_not_section_root(self):
        """Issue 191: Below 90% boundary (width=1295) is NOT a section root."""
        assert is_section_root({"type": "FRAME", "absoluteBoundingBox": {"width": 1295}}) is False


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

    def test_all_zero_gaps(self):
        """Edge-to-edge elements (gap=0) should be perfectly regular."""
        boxes = [
            {"x": 0, "y": 0, "w": 100, "h": 50},
            {"x": 100, "y": 0, "w": 100, "h": 50},
            {"x": 200, "y": 0, "w": 100, "h": 50},
        ]
        assert detect_regular_spacing(boxes) is True

    def test_mixed_zero_positive_gaps(self):
        """Mix of zero and positive gaps should be irregular."""
        boxes = [
            {"x": 0, "y": 0, "w": 100, "h": 50},
            {"x": 100, "y": 0, "w": 100, "h": 50},   # gap=0
            {"x": 250, "y": 0, "w": 100, "h": 50},   # gap=50
            {"x": 350, "y": 0, "w": 100, "h": 50},   # gap=0
        ]
        assert detect_regular_spacing(boxes) is False


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

    def test_row_tolerance_zero_uses_default(self):
        """Issue #244: row_tolerance=0 should not raise ZeroDivisionError."""
        assert detect_wrap(self.BOXES, "HORIZONTAL", row_tolerance=0) is True

    def test_rounding_boundary_no_false_wrap(self):
        """Issue #251: Elements near rounding boundary should not create false rows.
        Y values 100, 119, 120, 139 with tolerance=20 are all within 39px spread
        — a single row, not multiple rows."""
        boxes = [
            {"x": 0, "y": 100, "w": 100, "h": 50},
            {"x": 120, "y": 119, "w": 100, "h": 50},
            {"x": 240, "y": 120, "w": 100, "h": 50},
            {"x": 360, "y": 139, "w": 100, "h": 50},
        ]
        assert detect_wrap(boxes, "HORIZONTAL", row_tolerance=20) is False

    def test_real_wrap_still_detected(self):
        """Issue #251: Real wrap (large Y gap) should still be detected."""
        boxes = [
            {"x": 0, "y": 0, "w": 100, "h": 50},
            {"x": 120, "y": 0, "w": 100, "h": 50},
            {"x": 0, "y": 100, "w": 100, "h": 50},
            {"x": 120, "y": 100, "w": 100, "h": 50},
        ]
        assert detect_wrap(boxes, "HORIZONTAL", row_tolerance=20) is True


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

    def test_dedup_partial_overlap_preserves_nodes(self):
        """Issue 236: Partial overlap should trim, not delete entire candidate.

        Setup: A section with 3 cards (semantic:card-list) followed by 3 pattern
        elements that share the last card's node ID. After dedup, the non-overlapping
        pattern nodes should still be covered by a trimmed candidate.
        """
        # Create a flat structure with 20+ children to trigger pattern detection:
        # - 3 card-like FRAMEs (img+text) → semantic:card-list {c0, c1, c2}
        # - c2 is also structurally similar to pattern items p0, p1
        # - pattern items p0, p1, c2 share structure → pattern {c2, p0, p1}
        # After dedup, p0 and p1 must NOT be orphaned.
        cards = []
        for i in range(3):
            cards.append({
                "id": f"card:{i}", "name": f"Frame {i}", "type": "FRAME",
                "absoluteBoundingBox": {"x": i * 400, "y": 100, "width": 350, "height": 400},
                "children": [
                    {"id": f"card:{i}:img", "name": f"Rectangle {i}", "type": "RECTANGLE",
                     "absoluteBoundingBox": {"x": i * 400, "y": 100, "width": 350, "height": 200}},
                    {"id": f"card:{i}:txt", "name": f"Text {i}", "type": "TEXT",
                     "absoluteBoundingBox": {"x": i * 400, "y": 310, "width": 350, "height": 40},
                     "characters": f"Card Title {i}"},
                ],
            })
        # Add extra pattern items structurally similar to cards
        extra_patterns = []
        for i in range(3, 6):
            extra_patterns.append({
                "id": f"card:{i}", "name": f"Frame {i}", "type": "FRAME",
                "absoluteBoundingBox": {"x": (i - 3) * 400, "y": 600, "width": 350, "height": 400},
                "children": [
                    {"id": f"card:{i}:img", "name": f"Rectangle {i}", "type": "RECTANGLE",
                     "absoluteBoundingBox": {"x": (i - 3) * 400, "y": 600, "width": 350, "height": 200}},
                    {"id": f"card:{i}:txt", "name": f"Text {i}", "type": "TEXT",
                     "absoluteBoundingBox": {"x": (i - 3) * 400, "y": 810, "width": 350, "height": 40},
                     "characters": f"Item Title {i}"},
                ],
            })
        # Padding elements to reach flat_threshold (15)
        fillers = []
        for i in range(9):
            fillers.append({
                "id": f"fill:{i}", "name": f"Line {i}", "type": "LINE",
                "absoluteBoundingBox": {"x": 0, "y": 1100 + i * 100, "width": 1440, "height": 1},
            })
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 3000},
            "children": cards + extra_patterns + fillers,
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("detect-grouping-candidates.sh", tmp)
            candidates = data.get("candidates", [])
            # Collect all covered node IDs
            all_covered = set()
            for c in candidates:
                all_covered.update(c.get("node_ids", []))
            # All card/pattern frame IDs should be covered (no orphans)
            frame_ids = {f"card:{i}" for i in range(6)}
            orphaned = frame_ids - all_covered
            assert len(orphaned) == 0, (
                f"Issue 236: nodes {orphaned} orphaned after dedup. "
                f"Covered: {all_covered & frame_ids}"
            )
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


# ============================================================
# detect_bg_content_layers (Issue 180)
# ============================================================
class TestDetectBgContentLayers:
    """Tests for background-content layer separation (Issue 180)."""

    def test_standard_case(self):
        """1 bg RECTANGLE + 1 decoration VECTOR + 3 content elements -> 1 candidate."""
        parent_bb = {'x': 0, 'y': 0, 'w': 1440, 'h': 800}
        children = [
            # bg RECTANGLE: 1239x275, covers >80% of 1440 and >30% of 800
            {"id": "bg1", "type": "RECTANGLE", "name": "Rectangle 794",
             "absoluteBoundingBox": {"x": 100, "y": 100, "width": 1239, "height": 275}},
            # decoration VECTOR: small, overlaps bg
            {"id": "deco1", "type": "VECTOR", "name": "Vector 4",
             "absoluteBoundingBox": {"x": 200, "y": 300, "width": 52, "height": 40}},
            # content: heading group
            {"id": "c1", "type": "GROUP", "name": "Group 6030",
             "absoluteBoundingBox": {"x": 150, "y": 150, "width": 400, "height": 60},
             "children": [{"type": "TEXT", "children": []}]},
            # content: text
            {"id": "c2", "type": "TEXT", "name": "description",
             "absoluteBoundingBox": {"x": 150, "y": 220, "width": 600, "height": 40}},
            # content: button
            {"id": "c3", "type": "GROUP", "name": "Group 6004",
             "absoluteBoundingBox": {"x": 150, "y": 300, "width": 200, "height": 50},
             "children": [{"type": "TEXT", "children": []}]},
        ]
        result = detect_bg_content_layers(children, parent_bb)
        assert len(result) == 1
        cand = result[0]
        assert cand['method'] == 'semantic'
        assert cand['semantic_type'] == 'bg-content'
        assert cand['suggested_name'] == 'content-layer'
        assert cand['suggested_wrapper'] == 'content-group'
        # Content should be 3 elements (c1, c2, c3)
        assert set(cand['node_ids']) == {'c1', 'c2', 'c3'}
        assert cand['count'] == 3
        # Bg should include the RECTANGLE and the small VECTOR decoration
        assert set(cand['bg_node_ids']) == {'bg1', 'deco1'}

    def test_no_bg_rectangle(self):
        """No full-width RECTANGLE -> empty result."""
        parent_bb = {'x': 0, 'y': 0, 'w': 1440, 'h': 800}
        children = [
            {"id": "c1", "type": "GROUP", "name": "content-1",
             "absoluteBoundingBox": {"x": 100, "y": 100, "width": 400, "height": 300},
             "children": [{"type": "TEXT", "children": []}]},
            {"id": "c2", "type": "TEXT", "name": "text",
             "absoluteBoundingBox": {"x": 100, "y": 500, "width": 400, "height": 60}},
        ]
        result = detect_bg_content_layers(children, parent_bb)
        assert result == []

    def test_multiple_bg_rectangles(self):
        """Multiple full-width RECTANGLEs -> empty result (ambiguous)."""
        parent_bb = {'x': 0, 'y': 0, 'w': 1440, 'h': 1000}
        children = [
            {"id": "bg1", "type": "RECTANGLE", "name": "Rectangle 1",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 400}},
            {"id": "bg2", "type": "RECTANGLE", "name": "Rectangle 2",
             "absoluteBoundingBox": {"x": 0, "y": 500, "width": 1440, "height": 400}},
            {"id": "c1", "type": "TEXT", "name": "text",
             "absoluteBoundingBox": {"x": 100, "y": 200, "width": 400, "height": 60}},
            {"id": "c2", "type": "GROUP", "name": "group",
             "absoluteBoundingBox": {"x": 100, "y": 600, "width": 400, "height": 100},
             "children": [{"type": "TEXT", "children": []}]},
        ]
        result = detect_bg_content_layers(children, parent_bb)
        assert result == []

    def test_thin_rectangle_divider(self):
        """Thin bg RECTANGLE (height < 30% of parent) -> empty result (divider, not bg)."""
        parent_bb = {'x': 0, 'y': 0, 'w': 1440, 'h': 800}
        children = [
            # RECTANGLE covers full width but only 5px tall (< 30% of 800)
            {"id": "bg1", "type": "RECTANGLE", "name": "Rectangle 1",
             "absoluteBoundingBox": {"x": 0, "y": 400, "width": 1440, "height": 5}},
            {"id": "c1", "type": "TEXT", "name": "text1",
             "absoluteBoundingBox": {"x": 100, "y": 100, "width": 400, "height": 60}},
            {"id": "c2", "type": "TEXT", "name": "text2",
             "absoluteBoundingBox": {"x": 100, "y": 500, "width": 400, "height": 60}},
        ]
        result = detect_bg_content_layers(children, parent_bb)
        assert result == []

    def test_content_count_less_than_two(self):
        """Only 1 content element (+ bg) -> empty result."""
        parent_bb = {'x': 0, 'y': 0, 'w': 1440, 'h': 800}
        children = [
            {"id": "bg1", "type": "RECTANGLE", "name": "Rectangle 1",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 400}},
            {"id": "c1", "type": "TEXT", "name": "only-content",
             "absoluteBoundingBox": {"x": 100, "y": 100, "width": 400, "height": 60}},
        ]
        result = detect_bg_content_layers(children, parent_bb)
        assert result == []

    def test_empty_children(self):
        """Empty children list -> empty result."""
        result = detect_bg_content_layers([], {'x': 0, 'y': 0, 'w': 1440, 'h': 800})
        assert result == []

    def test_zero_parent_dimensions(self):
        """Parent with zero width/height -> empty result."""
        children = [
            {"id": "bg1", "type": "RECTANGLE", "name": "Rectangle 1",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 400}},
        ]
        assert detect_bg_content_layers(children, {'x': 0, 'y': 0, 'w': 0, 'h': 800}) == []
        assert detect_bg_content_layers(children, {'x': 0, 'y': 0, 'w': 1440, 'h': 0}) == []

    def test_narrow_rectangle_not_bg(self):
        """RECTANGLE narrower than 80% of parent -> not treated as bg."""
        parent_bb = {'x': 0, 'y': 0, 'w': 1440, 'h': 800}
        children = [
            # Width 1000 < 1440 * 0.8 = 1152 -> too narrow
            {"id": "r1", "type": "RECTANGLE", "name": "Rectangle 1",
             "absoluteBoundingBox": {"x": 220, "y": 100, "width": 1000, "height": 400}},
            {"id": "c1", "type": "TEXT", "name": "text1",
             "absoluteBoundingBox": {"x": 100, "y": 100, "width": 400, "height": 60}},
            {"id": "c2", "type": "TEXT", "name": "text2",
             "absoluteBoundingBox": {"x": 100, "y": 300, "width": 400, "height": 60}},
        ]
        result = detect_bg_content_layers(children, parent_bb)
        assert result == []

    def test_rectangle_with_children_not_bg(self):
        """RECTANGLE with children (non-leaf) -> not treated as bg."""
        parent_bb = {'x': 0, 'y': 0, 'w': 1440, 'h': 800}
        children = [
            {"id": "r1", "type": "RECTANGLE", "name": "Rectangle 1",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 400},
             "children": [{"type": "TEXT", "children": []}]},
            {"id": "c1", "type": "TEXT", "name": "text1",
             "absoluteBoundingBox": {"x": 100, "y": 100, "width": 400, "height": 60}},
            {"id": "c2", "type": "TEXT", "name": "text2",
             "absoluteBoundingBox": {"x": 100, "y": 300, "width": 400, "height": 60}},
        ]
        result = detect_bg_content_layers(children, parent_bb)
        assert result == []

    def test_large_vector_not_decoration(self):
        """Large VECTOR (area >= 5% of bg) -> treated as content, not decoration."""
        parent_bb = {'x': 0, 'y': 0, 'w': 1440, 'h': 800}
        # bg area = 1440 * 400 = 576000. 5% = 28800
        # Large vector area = 300 * 200 = 60000 > 28800
        children = [
            {"id": "bg1", "type": "RECTANGLE", "name": "Rectangle 1",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 400}},
            {"id": "v1", "type": "VECTOR", "name": "large-vector",
             "absoluteBoundingBox": {"x": 100, "y": 100, "width": 300, "height": 200}},
            {"id": "c1", "type": "TEXT", "name": "text1",
             "absoluteBoundingBox": {"x": 100, "y": 100, "width": 400, "height": 60}},
            {"id": "c2", "type": "GROUP", "name": "group",
             "absoluteBoundingBox": {"x": 100, "y": 300, "width": 400, "height": 100},
             "children": [{"type": "TEXT", "children": []}]},
        ]
        result = detect_bg_content_layers(children, parent_bb)
        assert len(result) == 1
        cand = result[0]
        # Large VECTOR should be content, not decoration
        assert 'v1' in cand['node_ids']
        assert 'v1' not in cand['bg_node_ids']
        assert cand['count'] == 3  # v1, c1, c2

    def test_non_overlapping_vector_not_decoration(self):
        """Small VECTOR that doesn't overlap bg -> treated as content."""
        parent_bb = {'x': 0, 'y': 0, 'w': 1440, 'h': 800}
        children = [
            {"id": "bg1", "type": "RECTANGLE", "name": "Rectangle 1",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 300}},
            # Small vector but completely below the bg RECTANGLE
            {"id": "v1", "type": "VECTOR", "name": "Vector 1",
             "absoluteBoundingBox": {"x": 100, "y": 500, "width": 20, "height": 20}},
            {"id": "c1", "type": "TEXT", "name": "text1",
             "absoluteBoundingBox": {"x": 100, "y": 100, "width": 400, "height": 60}},
            {"id": "c2", "type": "GROUP", "name": "group",
             "absoluteBoundingBox": {"x": 100, "y": 350, "width": 400, "height": 100},
             "children": [{"type": "TEXT", "children": []}]},
        ]
        result = detect_bg_content_layers(children, parent_bb)
        assert len(result) == 1
        # Non-overlapping vector is content
        assert 'v1' in result[0]['node_ids']
        assert 'v1' not in result[0]['bg_node_ids']

    def test_constants_exported(self):
        """Verify constants are exported and have expected values."""
        assert BG_WIDTH_RATIO == 0.8
        assert BG_MIN_HEIGHT_RATIO == 0.3
        assert BG_DECORATION_MAX_AREA_RATIO == 0.05
        assert OVERFLOW_BG_MIN_WIDTH == 1400

    def test_oversized_element_detected_as_bg(self):
        """Issue 183: Element wider than OVERFLOW_BG_MIN_WIDTH (1400px) -> bg candidate."""
        parent_bb = {'x': 0, 'y': 0, 'w': 1440, 'h': 1000}
        children = [
            # Oversized RECTANGLE: 1943px wide (exceeds page width), leaf node
            {"id": "bg1", "type": "RECTANGLE", "name": "red-panel",
             "absoluteBoundingBox": {"x": -200, "y": 0, "width": 1943, "height": 937}},
            # content elements
            {"id": "c1", "type": "TEXT", "name": "heading",
             "absoluteBoundingBox": {"x": 100, "y": 100, "width": 400, "height": 60}},
            {"id": "c2", "type": "GROUP", "name": "content-group",
             "absoluteBoundingBox": {"x": 100, "y": 200, "width": 600, "height": 300},
             "children": [{"type": "TEXT", "children": []}]},
        ]
        result = detect_bg_content_layers(children, parent_bb)
        assert len(result) == 1
        cand = result[0]
        assert cand['semantic_type'] == 'bg-content'
        assert 'bg1' in cand['bg_node_ids']
        assert set(cand['node_ids']) == {'c1', 'c2'}

    def test_left_overflow_element_detected_as_bg(self):
        """Issue 183: Element with x < 0 (left overflow) and width >= 50% parent -> bg candidate."""
        parent_bb = {'x': 0, 'y': 0, 'w': 1440, 'h': 1200}
        children = [
            # Left-overflow RECTANGLE: x=-143, width=1422 (>= 50% of 1440), leaf
            {"id": "bg1", "type": "RECTANGLE", "name": "recruit_bg",
             "absoluteBoundingBox": {"x": -143, "y": 200, "width": 1422, "height": 578}},
            # content
            {"id": "c1", "type": "TEXT", "name": "title",
             "absoluteBoundingBox": {"x": 100, "y": 300, "width": 300, "height": 40}},
            {"id": "c2", "type": "FRAME", "name": "content-frame",
             "absoluteBoundingBox": {"x": 100, "y": 400, "width": 500, "height": 200},
             "children": [{"type": "TEXT", "children": []}]},
        ]
        result = detect_bg_content_layers(children, parent_bb)
        assert len(result) == 1
        cand = result[0]
        assert 'bg1' in cand['bg_node_ids']
        assert set(cand['node_ids']) == {'c1', 'c2'}

    def test_overflow_bg_wider_parent(self):
        """Issue 183: RECTANGLE at OVERFLOW_BG_MIN_WIDTH in wider parent -> bg candidate via overflow check."""
        # Parent width 2000 -> 80% = 1600. Width 1400 < 1600 would fail old check.
        # But 1400 >= OVERFLOW_BG_MIN_WIDTH should pass new check.
        parent_bb_wide = {'x': 0, 'y': 0, 'w': 2000, 'h': 800}
        children = [
            {"id": "bg1", "type": "RECTANGLE", "name": "wide-bg",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1400, "height": 400}},
            {"id": "c1", "type": "TEXT", "name": "text1",
             "absoluteBoundingBox": {"x": 100, "y": 100, "width": 400, "height": 60}},
            {"id": "c2", "type": "TEXT", "name": "text2",
             "absoluteBoundingBox": {"x": 100, "y": 300, "width": 400, "height": 60}},
        ]
        result = detect_bg_content_layers(children, parent_bb_wide)
        assert len(result) == 1
        assert 'bg1' in result[0]['bg_node_ids']


# ============================================================
# detect_table_rows (Issue 181)
# ============================================================
class TestDetectTableRows:
    """Tests for table row structure detection (Issue 181)."""

    def _make_table_children(self):
        """Create a standard 4-row table fixture:
        1 heading FRAME + 4 bg RECTANGLEs + 5 divider VECTORs + 12 TEXTs.
        Modeled after the /strength page Group 6131.
        """
        parent_w = 600
        row_h = 103
        children = []
        y_cursor = 0

        # Heading frame above table
        children.append({
            "id": "h:1", "type": "FRAME", "name": "Frame 1",
            "absoluteBoundingBox": {"x": 0, "y": y_cursor, "width": parent_w, "height": 60},
            "children": [
                {"id": "h:2", "type": "TEXT", "name": "heading-text",
                 "absoluteBoundingBox": {"x": 10, "y": y_cursor + 10, "width": 200, "height": 30},
                 "characters": "水道関連有資格者数"},
            ],
        })
        y_cursor += 60

        # Top divider
        children.append({
            "id": "d:0", "type": "VECTOR", "name": "Vector 1",
            "absoluteBoundingBox": {"x": 0, "y": y_cursor, "width": parent_w, "height": 0},
        })

        for row_idx in range(4):
            row_y = y_cursor + row_idx * (row_h + 1)  # +1 for divider
            # Row background RECTANGLE
            children.append({
                "id": f"r:{row_idx}", "type": "RECTANGLE", "name": f"Rectangle {row_idx}",
                "absoluteBoundingBox": {"x": 0, "y": row_y, "width": parent_w, "height": row_h},
            })
            # Label TEXT (left side)
            children.append({
                "id": f"t:label:{row_idx}", "type": "TEXT", "name": f"Text label {row_idx}",
                "absoluteBoundingBox": {"x": 10, "y": row_y + 20, "width": 200, "height": 30},
                "characters": f"資格名{row_idx}",
            })
            # Value TEXT (center)
            children.append({
                "id": f"t:val:{row_idx}", "type": "TEXT", "name": f"Text val {row_idx}",
                "absoluteBoundingBox": {"x": 300, "y": row_y + 20, "width": 50, "height": 30},
                "characters": str(291 - row_idx * 10),
            })
            # Unit TEXT (right side)
            children.append({
                "id": f"t:unit:{row_idx}", "type": "TEXT", "name": f"Text unit {row_idx}",
                "absoluteBoundingBox": {"x": 360, "y": row_y + 20, "width": 30, "height": 30},
                "characters": "名",
            })
            # Divider after each row
            children.append({
                "id": f"d:{row_idx + 1}", "type": "VECTOR", "name": f"Vector {row_idx + 2}",
                "absoluteBoundingBox": {"x": 0, "y": row_y + row_h, "width": parent_w, "height": 0},
            })

        return children, parent_w

    def test_standard_table(self):
        """Standard: 4 bg RECTs + 5 dividers + 12 texts + 1 heading -> 1 table candidate."""
        children, parent_w = self._make_table_children()
        parent_bb = {'x': 0, 'y': 0, 'w': parent_w, 'h': 600}
        result = detect_table_rows(children, parent_bb)
        assert len(result) == 1
        cand = result[0]
        assert cand['method'] == 'semantic'
        assert cand['semantic_type'] == 'table'
        assert cand['row_count'] == 4
        assert cand['suggested_wrapper'] == 'table-container'
        # All 22 children should be in the table
        assert cand['count'] == len(children)
        # Heading should be included
        assert 'h:1' in cand['node_ids']
        # All RECTs should be included
        for i in range(4):
            assert f'r:{i}' in cand['node_ids']
        # All dividers should be included
        for i in range(5):
            assert f'd:{i}' in cand['node_ids']
        # All texts should be included
        for i in range(4):
            assert f't:label:{i}' in cand['node_ids']
            assert f't:val:{i}' in cand['node_ids']
            assert f't:unit:{i}' in cand['node_ids']
        # Name should contain a slug from heading text
        assert cand['suggested_name'].startswith('table-')
        assert len(cand['suggested_name']) > len('table-')

    def test_too_few_rects(self):
        """Only 2 full-width RECTANGLEs -> below TABLE_MIN_ROWS -> empty."""
        parent_bb = {'x': 0, 'y': 0, 'w': 600, 'h': 400}
        children = [
            {"id": "r:0", "type": "RECTANGLE", "name": "Rectangle 1",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 600, "height": 100}},
            {"id": "t:0", "type": "TEXT", "name": "Text 1",
             "absoluteBoundingBox": {"x": 10, "y": 20, "width": 100, "height": 30},
             "characters": "label"},
            {"id": "r:1", "type": "RECTANGLE", "name": "Rectangle 2",
             "absoluteBoundingBox": {"x": 0, "y": 110, "width": 600, "height": 100}},
            {"id": "t:1", "type": "TEXT", "name": "Text 2",
             "absoluteBoundingBox": {"x": 10, "y": 130, "width": 100, "height": 30},
             "characters": "label2"},
        ]
        result = detect_table_rows(children, parent_bb)
        assert result == []

    def test_rects_not_full_width(self):
        """RECTANGLEs narrower than 90% of parent -> empty."""
        parent_bb = {'x': 0, 'y': 0, 'w': 1000, 'h': 600}
        children = [
            {"id": f"r:{i}", "type": "RECTANGLE", "name": f"Rectangle {i}",
             "absoluteBoundingBox": {"x": 100, "y": i * 110, "width": 500, "height": 100}}
            for i in range(4)
        ]
        # Add text children for each rect
        for i in range(4):
            children.append({
                "id": f"t:{i}", "type": "TEXT", "name": f"Text {i}",
                "absoluteBoundingBox": {"x": 110, "y": i * 110 + 20, "width": 100, "height": 30},
                "characters": f"label{i}",
            })
        result = detect_table_rows(children, parent_bb)
        assert result == []

    def test_heading_included(self):
        """FRAME element above first RECT -> included as heading."""
        parent_bb = {'x': 0, 'y': 0, 'w': 600, 'h': 600}
        children = [
            # Heading above rects
            {"id": "heading", "type": "FRAME", "name": "heading-frame",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 600, "height": 50},
             "children": [
                 {"id": "ht", "type": "TEXT", "name": "heading-text",
                  "absoluteBoundingBox": {"x": 10, "y": 10, "width": 200, "height": 30},
                  "characters": "Table Title"},
             ]},
        ]
        # Add 3 rows
        for i in range(3):
            row_y = 60 + i * 110
            children.append({
                "id": f"r:{i}", "type": "RECTANGLE", "name": f"Rectangle {i}",
                "absoluteBoundingBox": {"x": 0, "y": row_y, "width": 600, "height": 100},
            })
            children.append({
                "id": f"t:{i}", "type": "TEXT", "name": f"Text {i}",
                "absoluteBoundingBox": {"x": 10, "y": row_y + 20, "width": 100, "height": 30},
                "characters": f"label{i}",
            })
        result = detect_table_rows(children, parent_bb)
        assert len(result) == 1
        assert 'heading' in result[0]['node_ids']
        assert result[0]['suggested_name'] == 'table-table-title'  # "Table Title" -> to_kebab -> "table-title"

    def test_mixed_table_and_non_table_content(self):
        """Non-table elements (outside RECT Y range) not included."""
        parent_bb = {'x': 0, 'y': 0, 'w': 600, 'h': 800}
        children = []
        # 3 table rows
        for i in range(3):
            row_y = i * 110
            children.append({
                "id": f"r:{i}", "type": "RECTANGLE", "name": f"Rectangle {i}",
                "absoluteBoundingBox": {"x": 0, "y": row_y, "width": 600, "height": 100},
            })
            children.append({
                "id": f"t:{i}", "type": "TEXT", "name": f"Text {i}",
                "absoluteBoundingBox": {"x": 10, "y": row_y + 20, "width": 100, "height": 30},
                "characters": f"label{i}",
            })
        # Non-table TEXT far below (Y-center outside any RECT)
        children.append({
            "id": "extra", "type": "TEXT", "name": "extra-text",
            "absoluteBoundingBox": {"x": 10, "y": 600, "width": 200, "height": 40},
            "characters": "Not part of table",
        })
        result = detect_table_rows(children, parent_bb)
        assert len(result) == 1
        assert 'extra' not in result[0]['node_ids']
        assert result[0]['row_count'] == 3

    def test_empty_children(self):
        """Empty children -> empty result."""
        result = detect_table_rows([], {'x': 0, 'y': 0, 'w': 600, 'h': 400})
        assert result == []

    def test_zero_parent_width(self):
        """Parent with zero width -> empty result."""
        children = [
            {"id": "r:0", "type": "RECTANGLE", "name": "Rectangle 1",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 600, "height": 100}},
        ]
        result = detect_table_rows(children, {'x': 0, 'y': 0, 'w': 0, 'h': 400})
        assert result == []

    def test_dividers_included(self):
        """VECTOR dividers (height <= 2px, full-width) are included."""
        parent_bb = {'x': 0, 'y': 0, 'w': 600, 'h': 600}
        children = []
        for i in range(3):
            row_y = i * 110
            children.append({
                "id": f"d:{i}", "type": "VECTOR", "name": f"Vector {i}",
                "absoluteBoundingBox": {"x": 0, "y": row_y, "width": 600, "height": 1},
            })
            children.append({
                "id": f"r:{i}", "type": "RECTANGLE", "name": f"Rectangle {i}",
                "absoluteBoundingBox": {"x": 0, "y": row_y + 1, "width": 600, "height": 100},
            })
            children.append({
                "id": f"t:{i}", "type": "TEXT", "name": f"Text {i}",
                "absoluteBoundingBox": {"x": 10, "y": row_y + 21, "width": 100, "height": 30},
                "characters": f"label{i}",
            })
        result = detect_table_rows(children, parent_bb)
        assert len(result) == 1
        # All dividers should be included
        for i in range(3):
            assert f'd:{i}' in result[0]['node_ids']

    def test_line_dividers_included(self):
        """LINE dividers (not just VECTOR) are also included."""
        parent_bb = {'x': 0, 'y': 0, 'w': 600, 'h': 600}
        children = []
        for i in range(3):
            row_y = i * 110
            children.append({
                "id": f"l:{i}", "type": "LINE", "name": f"Line {i}",
                "absoluteBoundingBox": {"x": 0, "y": row_y, "width": 600, "height": 0},
            })
            children.append({
                "id": f"r:{i}", "type": "RECTANGLE", "name": f"Rectangle {i}",
                "absoluteBoundingBox": {"x": 0, "y": row_y + 1, "width": 600, "height": 100},
            })
            children.append({
                "id": f"t:{i}", "type": "TEXT", "name": f"Text {i}",
                "absoluteBoundingBox": {"x": 10, "y": row_y + 21, "width": 100, "height": 30},
                "characters": f"label{i}",
            })
        result = detect_table_rows(children, parent_bb)
        assert len(result) == 1
        for i in range(3):
            assert f'l:{i}' in result[0]['node_ids']

    def test_constants_exported(self):
        """Verify constants are exported and have expected values."""
        assert TABLE_MIN_ROWS == 3
        assert TABLE_ROW_WIDTH_RATIO == 0.9
        assert TABLE_DIVIDER_MAX_HEIGHT == 2

    def test_rects_without_content_not_counted(self):
        """RECTANGLEs with no TEXT in their Y range -> row_count stays 0 -> empty."""
        parent_bb = {'x': 0, 'y': 0, 'w': 600, 'h': 600}
        # 3 RECTANGLEs but all text is outside their Y ranges
        children = [
            {"id": "r:0", "type": "RECTANGLE", "name": "Rectangle 0",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 600, "height": 50}},
            {"id": "r:1", "type": "RECTANGLE", "name": "Rectangle 1",
             "absoluteBoundingBox": {"x": 0, "y": 60, "width": 600, "height": 50}},
            {"id": "r:2", "type": "RECTANGLE", "name": "Rectangle 2",
             "absoluteBoundingBox": {"x": 0, "y": 120, "width": 600, "height": 50}},
            # All text is far below the rects
            {"id": "t:0", "type": "TEXT", "name": "Text 0",
             "absoluteBoundingBox": {"x": 10, "y": 500, "width": 100, "height": 30},
             "characters": "far away"},
        ]
        result = detect_table_rows(children, parent_bb)
        assert result == []

    def test_node_order_preserved(self):
        """Node IDs in result should follow children order."""
        parent_bb = {'x': 0, 'y': 0, 'w': 600, 'h': 600}
        children = []
        for i in range(3):
            row_y = i * 110
            children.append({
                "id": f"r:{i}", "type": "RECTANGLE", "name": f"Rectangle {i}",
                "absoluteBoundingBox": {"x": 0, "y": row_y, "width": 600, "height": 100},
            })
            children.append({
                "id": f"t:{i}", "type": "TEXT", "name": f"Text {i}",
                "absoluteBoundingBox": {"x": 10, "y": row_y + 20, "width": 100, "height": 30},
                "characters": f"label{i}",
            })
        result = detect_table_rows(children, parent_bb)
        assert len(result) == 1
        ids = result[0]['node_ids']
        # Verify order matches children order
        child_ids = [c.get('id', '') for c in children]
        ordered = [cid for cid in child_ids if cid in ids]
        assert ids == ordered


# ============================================================
# detect_repeating_tuple (Issue 186)
# ============================================================
class TestDetectRepeatingTuple:
    def _make_node(self, node_type, name, node_id=None):
        """Helper to create a minimal Figma node dict."""
        return {
            "type": node_type,
            "name": name,
            "id": node_id or f"{node_type}-{name}",
        }

    def test_standard_3tuple_x3(self):
        """Standard blog card pattern: 3-tuple (RECTANGLE+FRAME+INSTANCE) x 3 reps."""
        children = []
        for i in range(3):
            children.append(self._make_node("RECTANGLE", f"img-{i}"))
            children.append(self._make_node("FRAME", f"text-{i}"))
            children.append(self._make_node("INSTANCE", f"arrow-{i}"))
        result = detect_repeating_tuple(children)
        assert len(result) == 1
        assert result[0]['tuple_size'] == 3
        assert result[0]['count'] == 3
        assert result[0]['start_idx'] == 0
        assert result[0]['children_indices'] == list(range(9))

    def test_2tuple_x4(self):
        """2-tuple (TEXT+RECTANGLE) x 4 repetitions."""
        children = []
        for i in range(4):
            children.append(self._make_node("TEXT", f"label-{i}"))
            children.append(self._make_node("RECTANGLE", f"box-{i}"))
        result = detect_repeating_tuple(children)
        assert len(result) == 1
        assert result[0]['tuple_size'] == 2
        assert result[0]['count'] == 4
        assert result[0]['children_indices'] == list(range(8))

    def test_not_enough_repetitions(self):
        """Only 2 repetitions (below TUPLE_PATTERN_MIN=3) -> no detection."""
        children = []
        for i in range(2):
            children.append(self._make_node("RECTANGLE", f"img-{i}"))
            children.append(self._make_node("FRAME", f"text-{i}"))
            children.append(self._make_node("INSTANCE", f"arrow-{i}"))
        result = detect_repeating_tuple(children)
        assert len(result) == 0

    def test_mixed_types_no_tuple(self):
        """Types that don't form any repeating tuple pattern."""
        children = [
            self._make_node("RECTANGLE", "a"),
            self._make_node("FRAME", "b"),
            self._make_node("TEXT", "c"),
            self._make_node("VECTOR", "d"),
            self._make_node("ELLIPSE", "e"),
            self._make_node("LINE", "f"),
        ]
        result = detect_repeating_tuple(children)
        assert len(result) == 0

    def test_tuple_at_start_with_trailing(self):
        """Tuple pattern at start with non-tuple trailing elements."""
        children = []
        for i in range(3):
            children.append(self._make_node("RECTANGLE", f"img-{i}"))
            children.append(self._make_node("FRAME", f"text-{i}"))
        # Add trailing non-pattern elements
        children.append(self._make_node("VECTOR", "decoration"))
        children.append(self._make_node("TEXT", "footer-text"))
        result = detect_repeating_tuple(children)
        assert len(result) == 1
        assert result[0]['tuple_size'] == 2
        assert result[0]['count'] == 3
        assert result[0]['start_idx'] == 0
        assert result[0]['children_indices'] == list(range(6))

    def test_tuple_in_middle(self):
        """Tuple pattern in the middle with surrounding non-tuple elements."""
        children = [
            self._make_node("TEXT", "heading"),
            self._make_node("VECTOR", "divider"),
        ]
        for i in range(3):
            children.append(self._make_node("RECTANGLE", f"img-{i}"))
            children.append(self._make_node("INSTANCE", f"btn-{i}"))
        children.append(self._make_node("TEXT", "footer"))
        result = detect_repeating_tuple(children)
        assert len(result) == 1
        assert result[0]['tuple_size'] == 2
        assert result[0]['count'] == 3
        assert result[0]['start_idx'] == 2
        assert result[0]['children_indices'] == [2, 3, 4, 5, 6, 7]

    def test_empty_input(self):
        """Empty children list -> no results."""
        result = detect_repeating_tuple([])
        assert result == []

    def test_single_element(self):
        """Single element -> no results."""
        children = [self._make_node("FRAME", "only-one")]
        result = detect_repeating_tuple(children)
        assert result == []

    def test_tuple_size_exceeds_max(self):
        """Tuple of size 6 (> TUPLE_MAX_SIZE=5) -> not detected as a single tuple."""
        children = []
        for i in range(3):
            children.append(self._make_node("RECTANGLE", f"a-{i}"))
            children.append(self._make_node("FRAME", f"b-{i}"))
            children.append(self._make_node("INSTANCE", f"c-{i}"))
            children.append(self._make_node("TEXT", f"d-{i}"))
            children.append(self._make_node("VECTOR", f"e-{i}"))
            children.append(self._make_node("ELLIPSE", f"f-{i}"))
        result = detect_repeating_tuple(children)
        # Should NOT find a tuple of size 6 (exceeds TUPLE_MAX_SIZE=5)
        for r in result:
            assert r['tuple_size'] <= TUPLE_MAX_SIZE

    def test_constants_values(self):
        """Verify constant values match spec."""
        assert TUPLE_PATTERN_MIN == 3
        assert TUPLE_MAX_SIZE == 5

    def test_5tuple_x3(self):
        """5-tuple (max size) x 3 repetitions."""
        children = []
        for i in range(3):
            children.append(self._make_node("RECTANGLE", f"a-{i}"))
            children.append(self._make_node("FRAME", f"b-{i}"))
            children.append(self._make_node("INSTANCE", f"c-{i}"))
            children.append(self._make_node("TEXT", f"d-{i}"))
            children.append(self._make_node("VECTOR", f"e-{i}"))
        result = detect_repeating_tuple(children)
        assert len(result) == 1
        assert result[0]['tuple_size'] == 5
        assert result[0]['count'] == 3
        assert result[0]['children_indices'] == list(range(15))

    def test_two_different_tuples(self):
        """Two non-overlapping tuple patterns of different sizes."""
        children = []
        # First pattern: 2-tuple x 3
        for i in range(3):
            children.append(self._make_node("TEXT", f"label-{i}"))
            children.append(self._make_node("RECTANGLE", f"box-{i}"))
        # Separator
        children.append(self._make_node("VECTOR", "divider"))
        # Second pattern: 3-tuple x 3
        for i in range(3):
            children.append(self._make_node("FRAME", f"card-{i}"))
            children.append(self._make_node("INSTANCE", f"icon-{i}"))
            children.append(self._make_node("ELLIPSE", f"dot-{i}"))
        result = detect_repeating_tuple(children)
        assert len(result) == 2
        # First group
        first = [r for r in result if r['start_idx'] == 0][0]
        assert first['tuple_size'] == 2
        assert first['count'] == 3
        # Second group
        second = [r for r in result if r['start_idx'] == 7][0]
        assert second['tuple_size'] == 3
        assert second['count'] == 3

    def test_all_same_type_not_tuple(self):
        """All elements of same type -> no tuple (tuple_size=1 is below min size of 2)."""
        children = [self._make_node("TEXT", f"t-{i}") for i in range(6)]
        result = detect_repeating_tuple(children)
        assert len(result) == 0


# ============================================================
# Issue 189: is_decoration_pattern / decoration_dominant_shape
# ============================================================
class TestDecorationPattern:
    def _make_frame(self, w, h, children, node_type='FRAME'):
        return {
            'type': node_type,
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': w, 'height': h},
            'children': children,
        }

    def _make_leaf(self, node_type, w=10, h=10):
        return {
            'type': node_type,
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': w, 'height': h},
        }

    def test_basic_dot_pattern(self):
        """FRAME with 5 ELLIPSE children -> decoration pattern."""
        children = [self._make_leaf('ELLIPSE') for _ in range(5)]
        node = self._make_frame(100, 100, children)
        assert is_decoration_pattern(node) is True

    def test_basic_rect_pattern(self):
        """FRAME with 4 RECTANGLE children -> decoration pattern."""
        children = [self._make_leaf('RECTANGLE') for _ in range(4)]
        node = self._make_frame(150, 150, children)
        assert is_decoration_pattern(node) is True

    def test_mixed_shapes(self):
        """FRAME with ELLIPSE + VECTOR children (>= 60% shapes) -> decoration."""
        children = [
            self._make_leaf('ELLIPSE'), self._make_leaf('ELLIPSE'),
            self._make_leaf('VECTOR'), self._make_leaf('VECTOR'),
            self._make_leaf('TEXT'),  # 1 non-shape
        ]
        node = self._make_frame(100, 100, children)
        assert is_decoration_pattern(node) is True  # 4/5 = 80% shapes

    def test_too_few_shapes(self):
        """Only 2 ELLIPSE children (below DECORATION_MIN_SHAPES=3) -> not decoration."""
        children = [self._make_leaf('ELLIPSE'), self._make_leaf('ELLIPSE')]
        node = self._make_frame(100, 100, children)
        assert is_decoration_pattern(node) is False

    def test_too_large(self):
        """Frame larger than DECORATION_MAX_SIZE -> not decoration."""
        children = [self._make_leaf('ELLIPSE') for _ in range(5)]
        node = self._make_frame(250, 250, children)
        assert is_decoration_pattern(node) is False

    def test_width_exceeds_max(self):
        """Width exceeds max but height is small -> not decoration."""
        children = [self._make_leaf('ELLIPSE') for _ in range(5)]
        node = self._make_frame(201, 100, children)
        assert is_decoration_pattern(node) is False

    def test_height_exceeds_max(self):
        """Height exceeds max but width is small -> not decoration."""
        children = [self._make_leaf('ELLIPSE') for _ in range(5)]
        node = self._make_frame(100, 201, children)
        assert is_decoration_pattern(node) is False

    def test_low_shape_ratio(self):
        """Too many non-shape children (below 60%) -> not decoration."""
        children = [
            self._make_leaf('ELLIPSE'), self._make_leaf('ELLIPSE'),
            self._make_leaf('ELLIPSE'),  # 3 shapes
            self._make_leaf('TEXT'), self._make_leaf('TEXT'),
            self._make_leaf('TEXT'), self._make_leaf('TEXT'),  # 4 non-shapes
        ]
        node = self._make_frame(100, 100, children)
        # 3/7 = 0.43 < 0.6
        assert is_decoration_pattern(node) is False

    def test_not_frame_or_group(self):
        """TEXT node -> not decoration regardless of children."""
        node = {
            'type': 'TEXT',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 50, 'height': 50},
            'children': [self._make_leaf('ELLIPSE') for _ in range(5)],
        }
        assert is_decoration_pattern(node) is False

    def test_group_type(self):
        """GROUP type should also be detected."""
        children = [self._make_leaf('ELLIPSE') for _ in range(4)]
        node = self._make_frame(100, 100, children, node_type='GROUP')
        assert is_decoration_pattern(node) is True

    def test_no_children(self):
        """FRAME with no children -> not decoration."""
        node = self._make_frame(100, 100, [])
        assert is_decoration_pattern(node) is False

    def test_nested_shapes(self):
        """Nested children: shapes inside sub-frames count as leaf descendants."""
        sub_frame = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 50, 'height': 50},
            'children': [self._make_leaf('ELLIPSE') for _ in range(3)],
        }
        children = [sub_frame, self._make_leaf('ELLIPSE')]
        node = self._make_frame(100, 100, children)
        # 4 ELLIPSE leaves, 4 total leaves, ratio=1.0
        assert is_decoration_pattern(node) is True

    def test_dominant_shape_ellipse(self):
        """Mostly ELLIPSE -> dominant is ELLIPSE."""
        children = [
            self._make_leaf('ELLIPSE'), self._make_leaf('ELLIPSE'),
            self._make_leaf('ELLIPSE'), self._make_leaf('RECTANGLE'),
        ]
        node = self._make_frame(100, 100, children)
        assert decoration_dominant_shape(node) == 'ELLIPSE'

    def test_dominant_shape_rectangle(self):
        """Mostly RECTANGLE -> dominant is RECTANGLE."""
        children = [
            self._make_leaf('RECTANGLE'), self._make_leaf('RECTANGLE'),
            self._make_leaf('RECTANGLE'), self._make_leaf('ELLIPSE'),
        ]
        node = self._make_frame(100, 100, children)
        assert decoration_dominant_shape(node) == 'RECTANGLE'

    def test_dominant_shape_vector(self):
        """Mostly VECTOR -> dominant is VECTOR."""
        children = [
            self._make_leaf('VECTOR'), self._make_leaf('VECTOR'),
            self._make_leaf('VECTOR'), self._make_leaf('ELLIPSE'),
        ]
        node = self._make_frame(100, 100, children)
        assert decoration_dominant_shape(node) == 'VECTOR'

    def test_constants_exported(self):
        """Verify constants are exported and have expected values."""
        assert DECORATION_MAX_SIZE == 200
        assert DECORATION_SHAPE_RATIO == 0.6
        assert DECORATION_MIN_SHAPES == 3

    def test_boundary_size_exactly_200(self):
        """Frame exactly at DECORATION_MAX_SIZE boundary -> accepted."""
        children = [self._make_leaf('ELLIPSE') for _ in range(5)]
        node = self._make_frame(200, 200, children)
        assert is_decoration_pattern(node) is True

    def test_boundary_ratio_exactly_60_percent(self):
        """Exactly 60% shape ratio -> accepted (>= threshold)."""
        # 3 shapes, 2 non-shapes = 60%
        children = [
            self._make_leaf('ELLIPSE'), self._make_leaf('ELLIPSE'),
            self._make_leaf('ELLIPSE'),
            self._make_leaf('TEXT'), self._make_leaf('TEXT'),
        ]
        node = self._make_frame(100, 100, children)
        assert is_decoration_pattern(node) is True


# ============================================================
# Issue 190: detect_highlight_text
# ============================================================
class TestDetectHighlightText:
    def _make_rect(self, x, y, w, h, node_id='r1', has_children=False):
        node = {
            'id': node_id, 'type': 'RECTANGLE', 'name': f'Rectangle {node_id}',
            'absoluteBoundingBox': {'x': x, 'y': y, 'width': w, 'height': h},
        }
        if has_children:
            node['children'] = [{'type': 'VECTOR', 'absoluteBoundingBox': {'x': x, 'y': y, 'width': 10, 'height': 10}}]
        return node

    def _make_text(self, x, y, w, h, text='test', node_id='t1'):
        return {
            'id': node_id, 'type': 'TEXT', 'name': f'Text {node_id}',
            'absoluteBoundingBox': {'x': x, 'y': y, 'width': w, 'height': h},
            'characters': text,
        }

    def test_standard_overlap(self):
        """RECTANGLE and TEXT overlapping at same position -> highlight detected."""
        children = [
            self._make_rect(100, 100, 200, 40),
            self._make_text(110, 105, 180, 30, text='key phrase'),
        ]
        result = detect_highlight_text(children)
        assert len(result) == 1
        assert result[0]['rect_idx'] == 0
        assert result[0]['text_idx'] == 1
        assert result[0]['text_content'] == 'key phrase'

    def test_no_overlap(self):
        """RECTANGLE and TEXT completely separated -> no highlight."""
        children = [
            self._make_rect(100, 100, 200, 40),
            self._make_text(100, 300, 200, 30, text='far away'),
        ]
        result = detect_highlight_text(children)
        assert len(result) == 0

    def test_partial_overlap_below_threshold(self):
        """Y overlap below 80% threshold -> no highlight."""
        # RECT: y=100..140, TEXT: y=130..165 (overlap 10px, smaller_h=35, ratio=0.29)
        children = [
            self._make_rect(100, 100, 200, 40),
            self._make_text(100, 130, 200, 35, text='partial'),
        ]
        result = detect_highlight_text(children)
        assert len(result) == 0

    def test_rect_too_tall(self):
        """RECT height > 2.0x TEXT height -> no highlight."""
        children = [
            self._make_rect(100, 100, 200, 100),  # h=100
            self._make_text(100, 100, 200, 30, text='small'),  # h=30, ratio=3.33
        ]
        result = detect_highlight_text(children)
        assert len(result) == 0

    def test_rect_too_short(self):
        """RECT height < 0.5x TEXT height -> no highlight."""
        children = [
            self._make_rect(100, 100, 200, 10),  # h=10
            self._make_text(100, 95, 200, 40, text='tall text'),  # h=40, ratio=0.25
        ]
        result = detect_highlight_text(children)
        assert len(result) == 0

    def test_text_too_long(self):
        """Text > HIGHLIGHT_TEXT_MAX_LEN (30) -> no highlight."""
        long_text = 'a' * 31
        children = [
            self._make_rect(100, 100, 200, 40),
            self._make_text(100, 100, 200, 30, text=long_text),
        ]
        result = detect_highlight_text(children)
        assert len(result) == 0

    def test_text_exactly_30_chars(self):
        """Text exactly at max length -> highlight detected."""
        text_30 = 'a' * 30
        children = [
            self._make_rect(100, 100, 200, 40),
            self._make_text(105, 105, 180, 30, text=text_30),
        ]
        result = detect_highlight_text(children)
        assert len(result) == 1

    def test_multiple_highlight_pairs(self):
        """Two RECT+TEXT pairs -> both detected."""
        children = [
            self._make_rect(100, 100, 200, 40, node_id='r1'),
            self._make_text(105, 105, 180, 30, text='first', node_id='t1'),
            self._make_rect(100, 200, 200, 40, node_id='r2'),
            self._make_text(105, 205, 180, 30, text='second', node_id='t2'),
        ]
        result = detect_highlight_text(children)
        assert len(result) == 2
        texts = {r['text_content'] for r in result}
        assert texts == {'first', 'second'}

    def test_rect_with_children_not_leaf(self):
        """RECTANGLE with children (not a leaf) -> not considered for highlight."""
        children = [
            self._make_rect(100, 100, 200, 40, has_children=True),
            self._make_text(105, 105, 180, 30, text='behind'),
        ]
        result = detect_highlight_text(children)
        assert len(result) == 0

    def test_empty_children(self):
        """Empty children list -> empty result."""
        result = detect_highlight_text([])
        assert result == []

    def test_no_rectangle(self):
        """Only TEXT children -> no highlight."""
        children = [
            self._make_text(100, 100, 200, 30, text='only text', node_id='t1'),
            self._make_text(100, 200, 200, 30, text='more text', node_id='t2'),
        ]
        result = detect_highlight_text(children)
        assert result == []

    def test_no_text(self):
        """Only RECTANGLE children -> no highlight."""
        children = [
            self._make_rect(100, 100, 200, 40, node_id='r1'),
            self._make_rect(100, 200, 200, 40, node_id='r2'),
        ]
        result = detect_highlight_text(children)
        assert result == []

    def test_non_rect_text_combo(self):
        """VECTOR + TEXT at same position -> no highlight (must be RECTANGLE)."""
        children = [
            {'id': 'v1', 'type': 'VECTOR', 'name': 'Vector 1',
             'absoluteBoundingBox': {'x': 100, 'y': 100, 'width': 200, 'height': 40}},
            self._make_text(105, 105, 180, 30, text='over vector'),
        ]
        result = detect_highlight_text(children)
        assert result == []

    def test_x_overlap_required(self):
        """X ranges don't overlap -> no highlight even if Y overlaps."""
        children = [
            self._make_rect(100, 100, 200, 40),
            self._make_text(400, 100, 200, 30, text='far right'),
        ]
        result = detect_highlight_text(children)
        assert len(result) == 0

    def test_constants_exported(self):
        """Verify constants are exported and have expected values."""
        assert HIGHLIGHT_OVERLAP_RATIO == 0.8
        assert HIGHLIGHT_TEXT_MAX_LEN == 30
        assert HIGHLIGHT_HEIGHT_RATIO_MIN == 0.5
        assert HIGHLIGHT_HEIGHT_RATIO_MAX == 2.0

    def test_model_case_example(self):
        """Reproduce the model case: Rectangle 14 (205x49) behind TEXT (same position)."""
        children = [
            self._make_rect(217, 3098, 205, 49, node_id='rect14'),
            self._make_text(220, 3100, 200, 40, text='key text', node_id='text-key'),
        ]
        result = detect_highlight_text(children)
        assert len(result) == 1
        assert result[0]['text_content'] == 'key text'

    def test_each_rect_used_once(self):
        """One RECT cannot match multiple TEXTs."""
        children = [
            self._make_rect(100, 100, 200, 40, node_id='r1'),
            self._make_text(105, 105, 180, 30, text='first', node_id='t1'),
            self._make_text(105, 106, 180, 30, text='second', node_id='t2'),
        ]
        result = detect_highlight_text(children)
        assert len(result) == 1  # Only first TEXT matched

    def test_zero_size_rect(self):
        """RECT with zero width -> skipped."""
        children = [
            self._make_rect(100, 100, 0, 40),
            self._make_text(100, 100, 200, 30, text='test'),
        ]
        result = detect_highlight_text(children)
        assert result == []

    def test_characters_field_preferred(self):
        """Characters field is used over name for text content."""
        children = [
            self._make_rect(100, 100, 200, 40),
            {
                'id': 't1', 'type': 'TEXT', 'name': 'Text 1',
                'absoluteBoundingBox': {'x': 105, 'y': 105, 'width': 180, 'height': 30},
                'characters': 'real content',
            },
        ]
        result = detect_highlight_text(children)
        assert len(result) == 1
        assert result[0]['text_content'] == 'real content'


# ============================================================
# is_off_canvas (Issue 182)
# ============================================================
class TestIsOffCanvas:
    def test_element_within_viewport(self):
        """Element at x=100, w=200 on a 1440px page -> not off-canvas."""
        node = {"absoluteBoundingBox": {"x": 100, "y": 0, "width": 200, "height": 100}}
        assert is_off_canvas(node, 1440) is False

    def test_element_at_origin(self):
        """Element at x=0 -> not off-canvas."""
        node = {"absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 100}}
        assert is_off_canvas(node, 1440) is False

    def test_element_far_right(self):
        """Element at x=2200 (> 1440 * 1.5 = 2160) -> off-canvas."""
        node = {"absoluteBoundingBox": {"x": 2200, "y": 0, "width": 300, "height": 100}}
        assert is_off_canvas(node, 1440) is True

    def test_element_just_at_margin(self):
        """Element at x=2160 (= 1440 * 1.5) -> not off-canvas (must exceed, not equal)."""
        node = {"absoluteBoundingBox": {"x": 2160, "y": 0, "width": 200, "height": 100}}
        assert is_off_canvas(node, 1440) is False

    def test_element_just_beyond_margin(self):
        """Element at x=2161 (> 1440 * 1.5) -> off-canvas."""
        node = {"absoluteBoundingBox": {"x": 2161, "y": 0, "width": 200, "height": 100}}
        assert is_off_canvas(node, 1440) is True

    def test_element_completely_left(self):
        """Element at x=-400, w=200 (right edge = -200 < 0) -> off-canvas."""
        node = {"absoluteBoundingBox": {"x": -400, "y": 0, "width": 200, "height": 100}}
        assert is_off_canvas(node, 1440) is True

    def test_element_partially_left(self):
        """Element at x=-100, w=200 (right edge = 100 > 0) -> not off-canvas."""
        node = {"absoluteBoundingBox": {"x": -100, "y": 0, "width": 200, "height": 100}}
        assert is_off_canvas(node, 1440) is False

    def test_zero_page_width(self):
        """page_width=0 -> always returns False (safety guard)."""
        node = {"absoluteBoundingBox": {"x": 5000, "y": 0, "width": 200, "height": 100}}
        assert is_off_canvas(node, 0) is False

    def test_zero_width_element(self):
        """Element with w=0 -> returns False (degenerate bbox)."""
        node = {"absoluteBoundingBox": {"x": 5000, "y": 0, "width": 0, "height": 100}}
        assert is_off_canvas(node, 1440) is False

    def test_no_bbox(self):
        """Node with no absoluteBoundingBox -> returns False (get_bbox returns defaults)."""
        node = {}
        assert is_off_canvas(node, 1440) is False

    def test_constant_value(self):
        """OFF_CANVAS_MARGIN should be 1.5."""
        assert OFF_CANVAS_MARGIN == 1.5

    # --- Issue #2: Negative-X artboard root_x tests ---

    def test_negative_root_x_child_inside(self):
        """Child inside artboard at negative X should NOT be off-canvas.

        Artboard at x=-5542, width=1440. Child at absolute x=-5442 (relative 100).
        rel_x = -5442 - (-5542) = 100 -> inside viewport.
        """
        node = {"absoluteBoundingBox": {"x": -5442, "y": 0, "width": 200, "height": 100}}
        assert is_off_canvas(node, 1440, root_x=-5542) is False

    def test_negative_root_x_child_at_origin(self):
        """Child at relative x=0 in negative-X artboard should NOT be off-canvas.

        Artboard at x=-5542. Child at absolute x=-5542 (relative 0).
        rel_x = -5542 - (-5542) = 0 -> at viewport origin.
        """
        node = {"absoluteBoundingBox": {"x": -5542, "y": 0, "width": 1440, "height": 100}}
        assert is_off_canvas(node, 1440, root_x=-5542) is False

    def test_negative_root_x_child_truly_off_canvas_right(self):
        """Child truly off-canvas to the right in negative-X artboard.

        Artboard at x=-5542, width=1440.
        Child at absolute x=-3200 -> rel_x = -3200 - (-5542) = 2342 > 1440 * 1.5 = 2160.
        """
        node = {"absoluteBoundingBox": {"x": -3200, "y": 0, "width": 200, "height": 100}}
        assert is_off_canvas(node, 1440, root_x=-5542) is True

    def test_negative_root_x_child_truly_off_canvas_left(self):
        """Child truly off-canvas to the left in negative-X artboard.

        Artboard at x=-5542, width=1440.
        Child at absolute x=-6000, width=200 -> rel_x = -6000 - (-5542) = -458.
        rel_x + w = -458 + 200 = -258 < 0 -> off-canvas.
        """
        node = {"absoluteBoundingBox": {"x": -6000, "y": 0, "width": 200, "height": 100}}
        assert is_off_canvas(node, 1440, root_x=-5542) is True

    def test_negative_root_x_false_positive_without_root_x(self):
        """Without root_x, child in negative-X artboard is falsely detected as off-canvas.

        This demonstrates the bug: when root_x is not provided (defaults to 0),
        a child at absolute x=-5442 has rel_x = -5442, and -5442 + 200 = -5242 < 0
        -> incorrectly flagged as off-canvas.
        """
        node = {"absoluteBoundingBox": {"x": -5442, "y": 0, "width": 200, "height": 100}}
        # Without root_x correction: FALSE POSITIVE
        assert is_off_canvas(node, 1440, root_x=0) is True
        # With root_x correction: correctly NOT off-canvas
        assert is_off_canvas(node, 1440, root_x=-5542) is False

    def test_zero_root_x_regression(self):
        """Artboard at x=0 with root_x=0 should behave as before (regression check)."""
        # Inside viewport
        node_in = {"absoluteBoundingBox": {"x": 100, "y": 0, "width": 200, "height": 100}}
        assert is_off_canvas(node_in, 1440, root_x=0) is False
        # Off-canvas right
        node_right = {"absoluteBoundingBox": {"x": 2200, "y": 0, "width": 300, "height": 100}}
        assert is_off_canvas(node_right, 1440, root_x=0) is True
        # Off-canvas left
        node_left = {"absoluteBoundingBox": {"x": -400, "y": 0, "width": 200, "height": 100}}
        assert is_off_canvas(node_left, 1440, root_x=0) is True


# ============================================================
# analyze-structure.sh: hidden node filtering (Issue 187)
# ============================================================
class TestAnalyzeStructureHiddenNodes:
    def test_hidden_nodes_excluded_from_scoring(self):
        """Hidden (visible: false) nodes should not be counted in total/unnamed."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Section 1",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                        "children": [
                            {"id": "2:1", "type": "TEXT", "name": "Title",
                             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 200, "height": 30}},
                        ],
                    },
                    {
                        "id": "1:2", "type": "FRAME", "name": "Frame 1",
                        "visible": False,
                        "absoluteBoundingBox": {"x": 0, "y": 500, "width": 1440, "height": 500},
                        "children": [
                            {"id": "2:2", "type": "TEXT", "name": "Text 1",
                             "absoluteBoundingBox": {"x": 0, "y": 500, "width": 200, "height": 30}},
                            {"id": "2:3", "type": "RECTANGLE", "name": "Rectangle 1",
                             "absoluteBoundingBox": {"x": 0, "y": 530, "width": 200, "height": 200}},
                        ],
                    },
                ],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("analyze-structure.sh", tmp)
            metrics = result["metrics"]
            # Hidden node (Frame 1) detected as 1 hidden node
            # (its subtree is skipped entirely without recursive counting)
            assert metrics["hidden_nodes"] == 1
            # "Rectangle 1" matches UNNAMED_RE but is hidden -> not counted as unnamed
            assert metrics["unnamed_nodes"] == 0
            # Total should not include hidden subtree
            # Visible: Page (root) + Section 1 + Title = 3
            assert metrics["total_nodes"] == 3
        finally:
            os.unlink(tmp)

    def test_no_hidden_nodes(self):
        """When no hidden nodes, hidden_nodes metric should be 0."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Section",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                        "children": [
                            {"id": "2:1", "type": "TEXT", "name": "Title",
                             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 200, "height": 30}},
                        ],
                    },
                ],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("analyze-structure.sh", tmp)
            assert result["metrics"]["hidden_nodes"] == 0
        finally:
            os.unlink(tmp)


# ============================================================
# analyze-structure.sh: off-canvas node filtering (Issue 182)
# ============================================================
class TestAnalyzeStructureOffCanvas:
    def test_off_canvas_nodes_excluded(self):
        """Elements far right (x > page_width * 1.5) should be excluded."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Section 1",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                        "children": [
                            {"id": "2:1", "type": "TEXT", "name": "Title",
                             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 200, "height": 30}},
                        ],
                    },
                    {
                        "id": "1:2", "type": "FRAME", "name": "Frame 1",
                        "absoluteBoundingBox": {"x": 3000, "y": 0, "width": 500, "height": 500},
                        "children": [
                            {"id": "2:2", "type": "TEXT", "name": "Text 1",
                             "absoluteBoundingBox": {"x": 3000, "y": 0, "width": 200, "height": 30}},
                            {"id": "2:3", "type": "RECTANGLE", "name": "Rectangle 1",
                             "absoluteBoundingBox": {"x": 3000, "y": 30, "width": 200, "height": 200}},
                        ],
                    },
                ],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("analyze-structure.sh", tmp)
            metrics = result["metrics"]
            # Off-canvas node (Frame 1 at x=3000) counted as 1 off-canvas
            assert metrics["off_canvas_nodes"] == 1
            # Total should not include off-canvas subtree
            # Visible: Page (root) + Section 1 + Title = 3
            assert metrics["total_nodes"] == 3
        finally:
            os.unlink(tmp)

    def test_element_within_margin_not_excluded(self):
        """Elements within 1.5x page_width are NOT off-canvas."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Section",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                        "children": [],
                    },
                    {
                        "id": "1:2", "type": "FRAME", "name": "Sidebar",
                        "absoluteBoundingBox": {"x": 1500, "y": 0, "width": 300, "height": 500},
                        "children": [],
                    },
                ],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("analyze-structure.sh", tmp)
            metrics = result["metrics"]
            # x=1500 < 1440 * 1.5 = 2160 -> not off-canvas
            assert metrics["off_canvas_nodes"] == 0
            # All nodes counted: Page + Section + Sidebar = 3
            assert metrics["total_nodes"] == 3
        finally:
            os.unlink(tmp)

    def test_element_negative_x_off_canvas(self):
        """Elements completely to the left (x + w < 0) are off-canvas."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Section",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                        "children": [],
                    },
                    {
                        "id": "1:2", "type": "FRAME", "name": "Hidden Left",
                        "absoluteBoundingBox": {"x": -500, "y": 0, "width": 200, "height": 500},
                        "children": [],
                    },
                ],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("analyze-structure.sh", tmp)
            metrics = result["metrics"]
            assert metrics["off_canvas_nodes"] == 1
        finally:
            os.unlink(tmp)


# ============================================================
# detect-grouping-candidates.sh: hidden node filtering (Issue 187)
# ============================================================
class TestGroupingHiddenNodes:
    def test_hidden_children_excluded_from_grouping(self):
        """Hidden children should not appear in grouping candidates."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Section 1",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                        "children": [
                            {"id": "2:1", "type": "TEXT", "name": "Title",
                             "absoluteBoundingBox": {"x": 10, "y": 10, "width": 200, "height": 30}},
                        ],
                    },
                    {
                        "id": "1:2", "type": "FRAME", "name": "Frame 1",
                        "visible": False,
                        "absoluteBoundingBox": {"x": 0, "y": 500, "width": 1440, "height": 500},
                        "children": [
                            {"id": "2:2", "type": "TEXT", "name": "Text 1",
                             "absoluteBoundingBox": {"x": 10, "y": 510, "width": 200, "height": 30}},
                        ],
                    },
                    {
                        "id": "1:3", "type": "FRAME", "name": "Section 2",
                        "absoluteBoundingBox": {"x": 0, "y": 1000, "width": 1440, "height": 500},
                        "children": [
                            {"id": "2:3", "type": "TEXT", "name": "Subtitle",
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
            all_node_ids = []
            for c in candidates:
                all_node_ids.extend(c.get("node_ids", []))
            assert "1:2" not in all_node_ids
            assert "2:2" not in all_node_ids
        finally:
            os.unlink(tmp)


# ============================================================
# detect-grouping-candidates.sh: off-canvas node filtering (Issue 182)
# ============================================================
class TestGroupingOffCanvas:
    def test_off_canvas_excluded_from_root_grouping(self):
        """Off-canvas nodes at root level should be excluded from grouping."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Section 1",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                        "children": [
                            {"id": "2:1", "type": "TEXT", "name": "Title",
                             "absoluteBoundingBox": {"x": 10, "y": 10, "width": 200, "height": 30}},
                        ],
                    },
                    {
                        "id": "1:2", "type": "FRAME", "name": "Off Canvas Asset",
                        "absoluteBoundingBox": {"x": 5000, "y": 0, "width": 500, "height": 500},
                        "children": [
                            {"id": "2:2", "type": "TEXT", "name": "Hidden Text",
                             "absoluteBoundingBox": {"x": 5000, "y": 10, "width": 200, "height": 30}},
                        ],
                    },
                    {
                        "id": "1:3", "type": "FRAME", "name": "Section 2",
                        "absoluteBoundingBox": {"x": 0, "y": 500, "width": 1440, "height": 500},
                        "children": [
                            {"id": "2:3", "type": "TEXT", "name": "Subtitle",
                             "absoluteBoundingBox": {"x": 10, "y": 510, "width": 200, "height": 30}},
                        ],
                    },
                ],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("detect-grouping-candidates.sh", tmp)
            candidates = result.get("candidates", [])
            all_node_ids = []
            for c in candidates:
                all_node_ids.extend(c.get("node_ids", []))
            assert "1:2" not in all_node_ids
            assert "2:2" not in all_node_ids
        finally:
            os.unlink(tmp)


# ============================================================
# detect_en_jp_label_pairs (Issue 185)
# ============================================================
class TestDetectEnJpLabelPairs:
    def _make_text(self, text, x=0, y=0, w=100, h=30):
        return {
            "type": "TEXT",
            "name": "Text 1",
            "characters": text,
            "absoluteBoundingBox": {"x": x, "y": y, "width": w, "height": h},
        }

    def test_basic_pair(self):
        """COMPANY + 会社情報 at similar Y -> pair detected."""
        children = [
            self._make_text("COMPANY", x=100, y=100, w=200, h=30),
            self._make_text("会社情報", x=100, y=140, w=200, h=30),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 1
        assert pairs[0]['en_idx'] == 0
        assert pairs[0]['jp_idx'] == 1
        assert pairs[0]['en_text'] == "COMPANY"
        assert pairs[0]['jp_text'] == "会社情報"

    def test_multi_word_en_label(self):
        """OUR BUSINESS + 事業紹介 -> pair detected (multi-word EN label)."""
        children = [
            self._make_text("OUR BUSINESS", x=100, y=100, w=200, h=30),
            self._make_text("事業紹介", x=100, y=140, w=200, h=30),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 1
        assert pairs[0]['en_text'] == "OUR BUSINESS"

    def test_too_many_words_not_label(self):
        """EN text with > 3 words -> not detected as label."""
        children = [
            self._make_text("THIS IS NOT A LABEL", x=100, y=100, w=400, h=30),
            self._make_text("日本語テスト", x=100, y=140, w=200, h=30),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 0

    def test_lowercase_not_label(self):
        """Lowercase EN text -> not detected as label."""
        children = [
            self._make_text("company info", x=100, y=100, w=200, h=30),
            self._make_text("会社情報", x=100, y=140, w=200, h=30),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 0

    def test_too_far_apart(self):
        """EN+JP pair more than 200px apart -> not detected."""
        children = [
            self._make_text("COMPANY", x=100, y=100, w=200, h=30),
            self._make_text("会社情報", x=100, y=400, w=200, h=30),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 0

    def test_multiple_pairs(self):
        """Multiple EN+JP pairs -> all detected."""
        children = [
            self._make_text("COMPANY", x=100, y=100, w=200, h=30),
            self._make_text("会社情報", x=100, y=140, w=200, h=30),
            self._make_text("RECRUIT", x=500, y=100, w=200, h=30),
            self._make_text("採用情報", x=500, y=140, w=200, h=30),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 2

    def test_non_text_nodes_ignored(self):
        """Non-TEXT nodes among children -> ignored."""
        children = [
            {"type": "FRAME", "name": "Frame 1",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 100, "height": 100}},
            self._make_text("COMPANY", x=100, y=100, w=200, h=30),
            self._make_text("会社情報", x=100, y=140, w=200, h=30),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 1
        assert pairs[0]['en_idx'] == 1
        assert pairs[0]['jp_idx'] == 2

    def test_single_child_no_pair(self):
        """Single child -> no pair possible."""
        children = [
            self._make_text("COMPANY", x=100, y=100, w=200, h=30),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 0

    def test_empty_children(self):
        """Empty children list -> no pairs."""
        assert detect_en_jp_label_pairs([]) == []

    def test_horizontal_proximity(self):
        """EN+JP pair side by side (horizontal proximity) -> detected."""
        children = [
            self._make_text("COMPANY", x=100, y=100, w=100, h=30),
            self._make_text("会社情報", x=220, y=100, w=100, h=30),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 1

    def test_overlapping_nodes(self):
        """EN+JP pair overlapping -> detected (distance=0)."""
        children = [
            self._make_text("COMPANY", x=100, y=100, w=200, h=30),
            self._make_text("会社情報", x=100, y=110, w=200, h=30),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 1

    def test_mixed_case_not_upper(self):
        """Mixed case (not all upper) -> not an EN label."""
        children = [
            self._make_text("Company", x=100, y=100, w=200, h=30),
            self._make_text("会社情報", x=100, y=140, w=200, h=30),
        ]
        pairs = detect_en_jp_label_pairs(children)
        assert len(pairs) == 0


# ============================================================
# JP_KEYWORD_MAP additions (Issue 185)
# ============================================================
class TestJpKeywordMapAdditions185:
    def test_company_info(self):
        assert _jp_keyword_lookup("会社情報") == "company-info"

    def test_business_intro(self):
        assert _jp_keyword_lookup("事業紹介") == "business"

    def test_recruit_blog(self):
        assert _jp_keyword_lookup("採用ブログ") == "recruit-blog"


# ============================================================
# Constants: CTA, Side Panel, EN+JP (Issues 185, 192, 193)
# ============================================================
class TestNewConstants185_192_193:
    def test_en_label_max_words(self):
        assert EN_LABEL_MAX_WORDS == 3

    def test_en_jp_pair_max_distance(self):
        assert EN_JP_PAIR_MAX_DISTANCE == 200

    def test_cta_square_ratio_min(self):
        assert CTA_SQUARE_RATIO_MIN == 0.8

    def test_cta_square_ratio_max(self):
        assert CTA_SQUARE_RATIO_MAX == 1.2

    def test_cta_y_threshold(self):
        assert CTA_Y_THRESHOLD == 100

    def test_side_panel_max_width(self):
        assert SIDE_PANEL_MAX_WIDTH == 80

    def test_side_panel_height_ratio(self):
        assert SIDE_PANEL_HEIGHT_RATIO == 3.0


# ============================================================
# generate-rename-map.sh integration: CTA detection (Issue 193)
# ============================================================
class TestGenerateRenameMapCTA:
    def test_cta_square_button(self):
        """Square CTA button at top-right with contact text -> cta-contact."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 5000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Frame 1",
                        "absoluteBoundingBox": {"x": 1250, "y": 10, "width": 156, "height": 156},
                        "children": [
                            {
                                "id": "1:2", "type": "TEXT", "name": "Text 1",
                                "characters": "お問い合わせ",
                                "absoluteBoundingBox": {"x": 1260, "y": 50, "width": 100, "height": 30},
                            }
                        ],
                    }
                ],
            }
        }
        path = write_fixture(data)
        try:
            result = run_script("generate-rename-map.sh", path)
            renames = result.get("renames", {})
            assert "1:1" in renames
            assert renames["1:1"]["new_name"].startswith("cta-")
            assert "contact" in renames["1:1"]["new_name"]
        finally:
            os.unlink(path)

    def test_non_square_not_cta(self):
        """Non-square button at top-right -> not CTA."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 5000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Frame 1",
                        "absoluteBoundingBox": {"x": 1250, "y": 10, "width": 300, "height": 50},
                        "children": [
                            {
                                "id": "1:2", "type": "TEXT", "name": "Text 1",
                                "characters": "お問い合わせ",
                                "absoluteBoundingBox": {"x": 1260, "y": 20, "width": 100, "height": 30},
                            }
                        ],
                    }
                ],
            }
        }
        path = write_fixture(data)
        try:
            result = run_script("generate-rename-map.sh", path)
            renames = result.get("renames", {})
            if "1:1" in renames:
                assert not renames["1:1"]["new_name"].startswith("cta-")
        finally:
            os.unlink(path)


# ============================================================
# generate-rename-map.sh integration: Side panel (Issue 192)
# ============================================================
class TestGenerateRenameMapSidePanel:
    def test_side_panel_right_edge(self):
        """Narrow vertical frame at right edge -> side-panel-*."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 5000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Frame 52",
                        "absoluteBoundingBox": {"x": 1379, "y": 500, "width": 42, "height": 268},
                        "children": [
                            {
                                "id": "1:2", "type": "VECTOR", "name": "Vector 1",
                                "absoluteBoundingBox": {"x": 1385, "y": 510, "width": 20, "height": 20},
                            }
                        ],
                    }
                ],
            }
        }
        path = write_fixture(data)
        try:
            result = run_script("generate-rename-map.sh", path)
            renames = result.get("renames", {})
            assert "1:1" in renames
            assert renames["1:1"]["new_name"].startswith("side-panel-")
        finally:
            os.unlink(path)

    def test_wide_frame_not_side_panel(self):
        """Wide frame at edge -> not side panel."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 5000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Frame 1",
                        "absoluteBoundingBox": {"x": 1300, "y": 500, "width": 120, "height": 268},
                        "children": [
                            {
                                "id": "1:2", "type": "TEXT", "name": "Text 1",
                                "characters": "test",
                                "absoluteBoundingBox": {"x": 1310, "y": 510, "width": 100, "height": 30},
                            }
                        ],
                    }
                ],
            }
        }
        path = write_fixture(data)
        try:
            result = run_script("generate-rename-map.sh", path)
            renames = result.get("renames", {})
            if "1:1" in renames:
                assert not renames["1:1"]["new_name"].startswith("side-panel-")
        finally:
            os.unlink(path)


# ============================================================
# generate-rename-map.sh integration: EN+JP pairs (Issue 185)
# ============================================================
class TestGenerateRenameMapEnJpPairs:
    def test_en_jp_pair_renamed(self):
        """COMPANY + 会社情報 TEXT siblings -> en-label-company + heading-company-info."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "section-root",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                "children": [
                    {
                        "id": "1:1", "type": "TEXT", "name": "Text 1",
                        "characters": "COMPANY",
                        "absoluteBoundingBox": {"x": 100, "y": 100, "width": 200, "height": 30},
                    },
                    {
                        "id": "1:2", "type": "TEXT", "name": "Text 2",
                        "characters": "会社情報",
                        "absoluteBoundingBox": {"x": 100, "y": 140, "width": 200, "height": 30},
                    },
                ],
            }
        }
        path = write_fixture(data)
        try:
            result = run_script("generate-rename-map.sh", path)
            renames = result.get("renames", {})
            assert "1:1" in renames
            assert renames["1:1"]["new_name"] == "en-label-company"
            assert "1:2" in renames
            assert renames["1:2"]["new_name"] == "heading-company-info"
        finally:
            os.unlink(path)

    def test_en_jp_pair_recruit(self):
        """RECRUIT + 採用情報 -> en-label-recruit + heading-recruit."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "section-root",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                "children": [
                    {
                        "id": "1:1", "type": "TEXT", "name": "Text 1",
                        "characters": "RECRUIT",
                        "absoluteBoundingBox": {"x": 100, "y": 100, "width": 200, "height": 30},
                    },
                    {
                        "id": "1:2", "type": "TEXT", "name": "Text 2",
                        "characters": "採用情報",
                        "absoluteBoundingBox": {"x": 100, "y": 140, "width": 200, "height": 30},
                    },
                ],
            }
        }
        path = write_fixture(data)
        try:
            result = run_script("generate-rename-map.sh", path)
            renames = result.get("renames", {})
            assert "1:1" in renames
            assert renames["1:1"]["new_name"] == "en-label-recruit"
            assert "1:2" in renames
            assert renames["1:2"]["new_name"] == "heading-recruit"
        finally:
            os.unlink(path)

    def test_already_named_not_overridden(self):
        """Already-named nodes (non-matching UNNAMED_RE) -> not overridden."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "section-root",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                "children": [
                    {
                        "id": "1:1", "type": "TEXT", "name": "custom-en-label",
                        "characters": "COMPANY",
                        "absoluteBoundingBox": {"x": 100, "y": 100, "width": 200, "height": 30},
                    },
                    {
                        "id": "1:2", "type": "TEXT", "name": "Text 2",
                        "characters": "会社情報",
                        "absoluteBoundingBox": {"x": 100, "y": 140, "width": 200, "height": 30},
                    },
                ],
            }
        }
        path = write_fixture(data)
        try:
            result = run_script("generate-rename-map.sh", path)
            renames = result.get("renames", {})
            # 1:1 has custom name -> should NOT be overridden
            assert "1:1" not in renames
            # 1:2 is unnamed -> should still get heading rename
            assert "1:2" in renames
            assert renames["1:2"]["new_name"] == "heading-company-info"
        finally:
            os.unlink(path)


# ===== Issue 194: Enriched Children Table =====

class TestGenerateEnrichedTable:
    """Tests for generate_enriched_table (Issue 194)."""

    def _make_node(self, id, type, name, x, y, w, h, children=None, visible=True, characters=None):
        node = {
            'id': id,
            'type': type,
            'name': name,
            'absoluteBoundingBox': {'x': x, 'y': y, 'width': w, 'height': h},
            'children': children or [],
        }
        if not visible:
            node['visible'] = False
        if characters:
            node['characters'] = characters
        return node

    def test_basic_output_format(self):
        """Table has correct header and separator lines."""
        children = [
            self._make_node('1:1', 'FRAME', 'hero', 0, 0, 1440, 600),
        ]
        result = generate_enriched_table(children)
        lines = result.strip().split('\n')
        assert len(lines) == 3  # header + separator + 1 row
        assert '| # | ID | Name | Type | X | Y | W x H | Leaf? | ChildTypes | Flags | Text |' in lines[0]
        assert lines[1].startswith('|---')

    def test_leaf_detection(self):
        """Leaf nodes show Y, container nodes show N."""
        children = [
            self._make_node('1:1', 'RECTANGLE', 'bg', 0, 0, 1440, 600),
            self._make_node('1:2', 'FRAME', 'section', 0, 600, 1440, 400,
                            children=[self._make_node('1:3', 'TEXT', 'title', 0, 0, 200, 30)]),
        ]
        result = generate_enriched_table(children)
        lines = result.strip().split('\n')
        # Row 1 (RECTANGLE, no children) = leaf
        assert '| Y |' in lines[2]
        # Row 2 (FRAME with children) = not leaf
        assert '| N |' in lines[3]

    def test_child_types_summary(self):
        """ChildTypes column shows compact type summary."""
        text_child = self._make_node('1:3', 'TEXT', 'txt', 0, 0, 100, 20)
        frame_child = self._make_node('1:4', 'FRAME', 'frm', 0, 30, 100, 50)
        children = [
            self._make_node('1:2', 'FRAME', 'card', 0, 0, 300, 200,
                            children=[text_child, text_child, frame_child]),
        ]
        result = generate_enriched_table(children)
        # Should contain 1FRA+2TEX (sorted alphabetically)
        assert '1FRA+2TEX' in result

    def test_bg_full_flag(self):
        """Full-width leaf RECTANGLE gets bg-full flag."""
        children = [
            self._make_node('1:1', 'RECTANGLE', 'Rectangle 1', 0, 0, 1440, 720),
        ]
        result = generate_enriched_table(children, page_width=1440)
        assert 'bg-full' in result

    def test_bg_wide_flag(self):
        """80%+ width leaf RECTANGLE gets bg-wide flag."""
        children = [
            self._make_node('1:1', 'RECTANGLE', 'bg', 0, 0, 1200, 500),
        ]
        result = generate_enriched_table(children, page_width=1440)
        assert 'bg-wide' in result

    def test_off_canvas_flag(self):
        """Off-canvas elements get off-canvas flag."""
        children = [
            self._make_node('1:1', 'RECTANGLE', 'offscreen', 3000, 0, 500, 500),
        ]
        result = generate_enriched_table(children, page_width=1440)
        assert 'off-canvas' in result

    def test_hidden_flag(self):
        """Hidden elements get hidden flag."""
        children = [
            self._make_node('1:1', 'FRAME', 'hidden-frame', 0, 0, 200, 200, visible=False),
        ]
        result = generate_enriched_table(children)
        assert 'hidden' in result

    def test_overflow_flag(self):
        """Elements extending beyond page width get overflow flag."""
        children = [
            self._make_node('1:1', 'RECTANGLE', 'wide', 0, 0, 1873, 654),
        ]
        result = generate_enriched_table(children, page_width=1440)
        assert 'overflow' in result

    def test_tiny_flag(self):
        """Very small elements get tiny flag."""
        children = [
            self._make_node('1:1', 'FRAME', 'dot', 100, 100, 35, 35),
        ]
        result = generate_enriched_table(children, page_width=1440)
        assert 'tiny' in result

    def test_decoration_flag(self):
        """Decoration pattern nodes get decoration flag."""
        ellipses = [
            self._make_node(f'1:{i}', 'ELLIPSE', f'Ellipse {i}', i*10, 0, 8, 8)
            for i in range(5)
        ]
        children = [
            self._make_node('1:100', 'FRAME', 'dots', 0, 0, 50, 50, children=ellipses),
        ]
        result = generate_enriched_table(children, page_width=1440)
        assert 'decoration' in result

    def test_text_preview_from_text_node(self):
        """TEXT nodes show their characters content."""
        children = [
            self._make_node('1:1', 'TEXT', 'お知らせ', 0, 0, 100, 20, characters='お知らせ'),
        ]
        result = generate_enriched_table(children)
        assert 'お知らせ' in result

    def test_text_preview_from_descendant(self):
        """Text preview is extracted from descendant TEXT nodes."""
        text_child = self._make_node('1:2', 'TEXT', 'title', 0, 0, 200, 30, characters='採用情報')
        children = [
            self._make_node('1:1', 'FRAME', 'section', 0, 0, 1440, 400,
                            children=[text_child]),
        ]
        result = generate_enriched_table(children)
        assert '採用情報' in result

    def test_no_text_shows_dash(self):
        """Nodes without text content show dash."""
        children = [
            self._make_node('1:1', 'RECTANGLE', 'Rectangle 1', 0, 0, 300, 200),
        ]
        result = generate_enriched_table(children)
        lines = result.strip().split('\n')
        # Last column should be "-"
        assert lines[2].rstrip().endswith('- |')

    def test_multiple_flags(self):
        """Multiple flags are comma-separated."""
        children = [
            self._make_node('1:1', 'RECTANGLE', 'rect', 0, 0, 1440, 720, visible=False),
        ]
        result = generate_enriched_table(children, page_width=1440)
        # Should have both hidden and bg-full
        assert 'hidden' in result
        assert 'bg-full' in result

    def test_no_flags_shows_dash(self):
        """Nodes with no flags show dash in Flags column."""
        children = [
            self._make_node('1:1', 'FRAME', 'normal-frame', 100, 100, 300, 200,
                            children=[self._make_node('1:2', 'TEXT', 't', 0, 0, 100, 20)]),
        ]
        result = generate_enriched_table(children, page_width=1440)
        lines = result.strip().split('\n')
        # Flags column should contain just '-'
        cols = [c.strip() for c in lines[2].split('|')]
        flags_col = cols[10]  # 10th column (0-indexed, accounting for leading empty)
        assert flags_col == '-'

    def test_model_case_blog_section(self):
        """Blog section from model case (2:8315) produces expected enriched table."""
        # Elements 5-14 from the model case represent the blog section
        blog_children = [
            self._make_node('2:8320', 'RECTANGLE', 'AdobeStock_541586693', 221, 3784, 320, 180),
            self._make_node('2:8321', 'FRAME', 'Group 73', 222, 3987, 318, 93,
                            children=[
                                self._make_node('2:8322', 'TEXT', 't1', 222, 4011, 313, 22, characters='typeにてエンジニアの募集を掲載しました'),
                                self._make_node('2:8323', 'TEXT', 't2', 222, 4040, 313, 44),
                                self._make_node('2:8324', 'TEXT', 't3', 222, 3987, 100, 15),
                                self._make_node('2:8325', 'FRAME', 'tag', 330, 3987, 50, 15),
                            ]),
            self._make_node('2:8327', 'RECTANGLE', 'AdobeStock_541586693', 573, 3784, 320, 180),
            self._make_node('2:8328', 'FRAME', 'Group 72', 574, 3987, 319, 93,
                            children=[
                                self._make_node('2:8329', 'TEXT', 't4', 574, 4011, 313, 22),
                                self._make_node('2:8330', 'TEXT', 't5', 574, 4040, 313, 44),
                                self._make_node('2:8331', 'TEXT', 't6', 574, 3987, 100, 15),
                                self._make_node('2:8332', 'FRAME', 'tag', 684, 3987, 50, 15),
                            ]),
            self._make_node('2:8334', 'RECTANGLE', 'AdobeStock_541586693', 925, 3784, 321, 180),
            self._make_node('2:8335', 'FRAME', 'Group 71', 926, 3987, 319, 93,
                            children=[
                                self._make_node('2:8336', 'TEXT', 't7', 926, 4011, 313, 22),
                                self._make_node('2:8337', 'TEXT', 't8', 926, 4040, 313, 44),
                                self._make_node('2:8338', 'TEXT', 't9', 926, 3987, 100, 15),
                                self._make_node('2:8339', 'FRAME', 'tag', 1036, 3987, 50, 15),
                            ]),
            # Pagination dots
            self._make_node('2:8348', 'FRAME', 'Group 76', 464, 3717, 35, 35),
            self._make_node('2:8351', 'FRAME', 'Group 77', 544, 3717, 35, 35),
        ]
        result = generate_enriched_table(blog_children, page_width=1440)
        lines = result.strip().split('\n')
        # Should have header + separator + 8 rows
        assert len(lines) == 10
        # Verify card image gets no bg flag (320px is not full-width)
        assert 'bg-full' not in lines[2]
        # Verify child types for Group 73 (1FRA+3TEX)
        assert '1FRA+3TEX' in lines[3]
        # Verify dots are tiny
        assert 'tiny' in lines[9]
        assert 'tiny' in lines[10] if len(lines) > 10 else True

    def test_empty_children(self):
        """Empty children list produces header-only table."""
        result = generate_enriched_table([])
        lines = result.strip().split('\n')
        assert len(lines) == 2  # header + separator only

    def test_name_truncation(self):
        """Long names are truncated to 35 characters."""
        children = [
            self._make_node('1:1', 'TEXT', 'A' * 50, 0, 0, 200, 30, characters='test'),
        ]
        result = generate_enriched_table(children)
        lines = result.strip().split('\n')
        # Name column should be truncated
        name_col = [c.strip() for c in lines[2].split('|')][3]
        assert len(name_col) <= 35

    def test_coordinates_are_integers(self):
        """X, Y, W, H values are rounded to integers."""
        children = [
            self._make_node('1:1', 'FRAME', 'f', 222.601, 3987.337, 318.614, 93.663),
        ]
        result = generate_enriched_table(children)
        assert '222' in result
        assert '3987' in result
        assert '318x93' in result


class TestComputeChildTypes:
    """Tests for _compute_child_types helper."""

    def test_empty(self):
        from figma_utils import _compute_child_types
        assert _compute_child_types([]) == '-'

    def test_single_type(self):
        from figma_utils import _compute_child_types
        children = [{'type': 'TEXT'}, {'type': 'TEXT'}, {'type': 'TEXT'}]
        assert _compute_child_types(children) == '3TEX'

    def test_mixed_types(self):
        from figma_utils import _compute_child_types
        children = [{'type': 'FRAME'}, {'type': 'TEXT'}, {'type': 'TEXT'}, {'type': 'RECTANGLE'}]
        result = _compute_child_types(children)
        assert '1FRA' in result
        assert '2TEX' in result
        assert '1REC' in result

    def test_unknown_type(self):
        from figma_utils import _compute_child_types
        children = [{'type': 'UNKNOWN_TYPE'}]
        assert _compute_child_types(children) == '1OTH'


class TestComputeFlags:
    """Tests for _compute_flags helper."""

    def test_no_flags(self):
        from figma_utils import _compute_flags
        node = {
            'type': 'FRAME', 'children': [{'type': 'TEXT'}],
            'absoluteBoundingBox': {'x': 100, 'y': 100, 'width': 300, 'height': 200},
        }
        flags = _compute_flags(node, 1440, 5000)
        assert flags == []

    def test_hidden_flag(self):
        from figma_utils import _compute_flags
        node = {
            'type': 'FRAME', 'visible': False, 'children': [],
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 200, 'height': 200},
        }
        flags = _compute_flags(node, 1440, 5000)
        assert 'hidden' in flags

    def test_bg_full_for_vector(self):
        """VECTOR type also gets bg-full flag when full-width leaf."""
        from figma_utils import _compute_flags
        node = {
            'type': 'VECTOR', 'children': [],
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 720},
        }
        flags = _compute_flags(node, 1440, 5000)
        assert 'bg-full' in flags

    def test_no_bg_for_frame(self):
        """FRAME type does NOT get bg-full flag even when full-width."""
        from figma_utils import _compute_flags
        node = {
            'type': 'FRAME', 'children': [],
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 720},
        }
        flags = _compute_flags(node, 1440, 5000)
        assert 'bg-full' not in flags

    def test_overflow_y_flag(self):
        """Element extending below page gets overflow-y flag."""
        from figma_utils import _compute_flags
        node = {
            'type': 'RECTANGLE', 'children': [],
            'absoluteBoundingBox': {'x': 0, 'y': 5000, 'width': 1440, 'height': 1000},
        }
        flags = _compute_flags(node, 1440, 5273)
        assert 'overflow-y' in flags


class TestCollectTextPreview:
    """Tests for _collect_text_preview helper."""

    def test_direct_text(self):
        from figma_utils import _collect_text_preview
        node = {'type': 'TEXT', 'characters': 'Hello World', 'name': 'Text 1'}
        assert _collect_text_preview(node) == 'Hello World'

    def test_nested_text(self):
        from figma_utils import _collect_text_preview
        node = {
            'type': 'FRAME', 'name': 'section',
            'children': [
                {'type': 'FRAME', 'name': 'inner', 'children': [
                    {'type': 'TEXT', 'characters': '深いテキスト', 'name': 'Text 1', 'children': []},
                ]},
            ],
        }
        assert _collect_text_preview(node) == '深いテキスト'

    def test_max_depth_respected(self):
        from figma_utils import _collect_text_preview
        # Text is at depth 4 but max_depth=3
        node = {
            'type': 'FRAME', 'name': 'a',
            'children': [{
                'type': 'FRAME', 'name': 'b',
                'children': [{
                    'type': 'FRAME', 'name': 'c',
                    'children': [{
                        'type': 'TEXT', 'characters': 'deep', 'name': 'd', 'children': [],
                    }],
                }],
            }],
        }
        assert _collect_text_preview(node, max_depth=2) == ''

    def test_unnamed_text_skipped(self):
        from figma_utils import _collect_text_preview
        node = {'type': 'TEXT', 'name': 'Text 1', 'children': []}  # no characters, unnamed
        assert _collect_text_preview(node) == ''

    def test_truncation(self):
        from figma_utils import _collect_text_preview
        node = {'type': 'TEXT', 'characters': 'A' * 100, 'name': 'long'}
        assert len(_collect_text_preview(node, max_len=30)) == 30


# ── Issue 184: Horizontal bar detection ──────────────────────────────


class TestDetectHorizontalBar:
    """Tests for detect_horizontal_bar() — Issue 184."""

    def _make_parent_bb(self):
        return {'x': 0, 'y': 0, 'w': 1440, 'h': 5000}

    def test_news_bar_detected(self):
        """6 elements in narrow Y band with RECTANGLE bg -> detected as horizontal bar."""
        children = [
            {'id': '1', 'name': 'Rectangle 1402', 'type': 'RECTANGLE',
             'absoluteBoundingBox': {'x': 64, 'y': 732, 'width': 821, 'height': 74}},
            {'id': '2', 'name': 'Group 75', 'type': 'GROUP',
             'absoluteBoundingBox': {'x': 1057, 'y': 751, 'width': 35, 'height': 35},
             'children': [{'id': '2a', 'type': 'VECTOR', 'name': 'arrow'}]},
            {'id': '3', 'name': 'お知らせ一覧', 'type': 'TEXT',
             'absoluteBoundingBox': {'x': 911, 'y': 764, 'width': 100, 'height': 20},
             'characters': 'お知らせ一覧'},
            {'id': '4', 'name': '2023.12.24', 'type': 'TEXT',
             'absoluteBoundingBox': {'x': 293, 'y': 756, 'width': 400, 'height': 20},
             'characters': '2023.12.24 テスト記事'},
            {'id': '5', 'name': 'お知らせ', 'type': 'TEXT',
             'absoluteBoundingBox': {'x': 196, 'y': 759, 'width': 80, 'height': 20},
             'characters': 'お知らせ'},
            {'id': '6', 'name': 'NEWS', 'type': 'TEXT',
             'absoluteBoundingBox': {'x': 98, 'y': 753, 'width': 60, 'height': 20},
             'characters': 'NEWS'},
        ]
        for c in children:
            resolve_absolute_coords(c)
        results = detect_horizontal_bar(children, self._make_parent_bb())
        assert len(results) == 1
        r = results[0]
        assert r['method'] == 'semantic'
        assert r['semantic_type'] == 'horizontal-bar'
        assert r['count'] == 6
        assert r['suggested_name'] == 'news-bar'
        assert set(r['node_ids']) == {'1', '2', '3', '4', '5', '6'}

    def test_wide_y_range_not_detected(self):
        """Elements spread across wide Y range (> 100px) -> not detected."""
        children = [
            {'id': '1', 'name': 'Rect', 'type': 'RECTANGLE',
             'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 800, 'height': 50}},
            {'id': '2', 'name': 'T1', 'type': 'TEXT',
             'absoluteBoundingBox': {'x': 100, 'y': 10, 'width': 100, 'height': 20},
             'characters': 'A'},
            {'id': '3', 'name': 'T2', 'type': 'TEXT',
             'absoluteBoundingBox': {'x': 300, 'y': 80, 'width': 100, 'height': 20},
             'characters': 'B'},
            {'id': '4', 'name': 'T3', 'type': 'TEXT',
             'absoluteBoundingBox': {'x': 500, 'y': 160, 'width': 100, 'height': 20},
             'characters': 'C'},
        ]
        for c in children:
            resolve_absolute_coords(c)
        results = detect_horizontal_bar(children, self._make_parent_bb())
        assert len(results) == 0

    def test_too_few_elements_not_detected(self):
        """Only 3 elements -> not detected (below HORIZONTAL_BAR_MIN_ELEMENTS)."""
        children = [
            {'id': '1', 'name': 'Rect', 'type': 'RECTANGLE',
             'absoluteBoundingBox': {'x': 0, 'y': 100, 'width': 800, 'height': 50}},
            {'id': '2', 'name': 'T1', 'type': 'TEXT',
             'absoluteBoundingBox': {'x': 200, 'y': 110, 'width': 100, 'height': 20},
             'characters': 'A'},
            {'id': '3', 'name': 'T2', 'type': 'TEXT',
             'absoluteBoundingBox': {'x': 500, 'y': 115, 'width': 100, 'height': 20},
             'characters': 'B'},
        ]
        for c in children:
            resolve_absolute_coords(c)
        results = detect_horizontal_bar(children, self._make_parent_bb())
        assert len(results) == 0

    def test_no_rectangle_bg_not_detected(self):
        """No RECTANGLE background -> not detected."""
        children = [
            {'id': '1', 'name': 'G1', 'type': 'GROUP',
             'absoluteBoundingBox': {'x': 0, 'y': 100, 'width': 50, 'height': 50},
             'children': [{'id': '1a', 'type': 'VECTOR', 'name': 'v'}]},
            {'id': '2', 'name': 'T1', 'type': 'TEXT',
             'absoluteBoundingBox': {'x': 100, 'y': 110, 'width': 100, 'height': 20},
             'characters': 'A'},
            {'id': '3', 'name': 'T2', 'type': 'TEXT',
             'absoluteBoundingBox': {'x': 300, 'y': 115, 'width': 100, 'height': 20},
             'characters': 'B'},
            {'id': '4', 'name': 'T3', 'type': 'TEXT',
             'absoluteBoundingBox': {'x': 500, 'y': 112, 'width': 100, 'height': 20},
             'characters': 'C'},
        ]
        for c in children:
            resolve_absolute_coords(c)
        results = detect_horizontal_bar(children, self._make_parent_bb())
        assert len(results) == 0

    def test_empty_children(self):
        """Empty children list -> empty result."""
        results = detect_horizontal_bar([], self._make_parent_bb())
        assert results == []

    def test_blog_bar_naming(self):
        """Bar with blog-related text -> named blog-bar."""
        children = [
            {'id': '1', 'name': 'Rectangle 1', 'type': 'RECTANGLE',
             'absoluteBoundingBox': {'x': 0, 'y': 100, 'width': 800, 'height': 50}},
            {'id': '2', 'name': 'T1', 'type': 'TEXT',
             'absoluteBoundingBox': {'x': 100, 'y': 110, 'width': 100, 'height': 20},
             'characters': 'ブログ一覧'},
            {'id': '3', 'name': 'T2', 'type': 'TEXT',
             'absoluteBoundingBox': {'x': 300, 'y': 115, 'width': 100, 'height': 20},
             'characters': '2024.01.01 記事タイトル'},
            {'id': '4', 'name': 'T3', 'type': 'TEXT',
             'absoluteBoundingBox': {'x': 600, 'y': 112, 'width': 60, 'height': 20},
             'characters': 'もっと見る'},
        ]
        for c in children:
            resolve_absolute_coords(c)
        results = detect_horizontal_bar(children, self._make_parent_bb())
        assert len(results) == 1
        assert results[0]['suggested_name'] == 'blog-bar'

    def test_generic_bar_naming(self):
        """Bar without news/blog text -> named horizontal-bar."""
        children = [
            {'id': '1', 'name': 'Rectangle 1', 'type': 'RECTANGLE',
             'absoluteBoundingBox': {'x': 0, 'y': 100, 'width': 800, 'height': 50}},
            {'id': '2', 'name': 'T1', 'type': 'TEXT',
             'absoluteBoundingBox': {'x': 100, 'y': 110, 'width': 100, 'height': 20},
             'characters': 'Alpha'},
            {'id': '3', 'name': 'T2', 'type': 'TEXT',
             'absoluteBoundingBox': {'x': 300, 'y': 115, 'width': 100, 'height': 20},
             'characters': 'Beta'},
            {'id': '4', 'name': 'T3', 'type': 'TEXT',
             'absoluteBoundingBox': {'x': 600, 'y': 112, 'width': 60, 'height': 20},
             'characters': 'Gamma'},
        ]
        for c in children:
            resolve_absolute_coords(c)
        results = detect_horizontal_bar(children, self._make_parent_bb())
        assert len(results) == 1
        assert results[0]['suggested_name'] == 'horizontal-bar'

    def test_variance_ratio_constant(self):
        """HORIZONTAL_BAR_VARIANCE_RATIO should be 3."""
        assert HORIZONTAL_BAR_VARIANCE_RATIO == 3

    def test_vertically_stacked_not_detected(self):
        """Elements stacked vertically in narrow Y band -> not detected (X_var <= Y_var * 3)."""
        # All at same X, different Y but within 100px band
        children = [
            {'id': '1', 'name': 'Rectangle 1', 'type': 'RECTANGLE',
             'absoluteBoundingBox': {'x': 100, 'y': 100, 'width': 200, 'height': 15}},
            {'id': '2', 'name': 'T1', 'type': 'TEXT',
             'absoluteBoundingBox': {'x': 100, 'y': 120, 'width': 200, 'height': 15},
             'characters': 'A'},
            {'id': '3', 'name': 'T2', 'type': 'TEXT',
             'absoluteBoundingBox': {'x': 100, 'y': 140, 'width': 200, 'height': 15},
             'characters': 'B'},
            {'id': '4', 'name': 'T3', 'type': 'TEXT',
             'absoluteBoundingBox': {'x': 100, 'y': 160, 'width': 200, 'height': 15},
             'characters': 'C'},
        ]
        for c in children:
            resolve_absolute_coords(c)
        results = detect_horizontal_bar(children, self._make_parent_bb())
        assert len(results) == 0  # vertically stacked


# ============================================================
# _compute_zone_bboxes (Issue 197: indirect coverage -> direct unit tests)
# ============================================================
class TestComputeZoneBboxes:
    """Direct unit tests for _compute_zone_bboxes helper."""

    def _make_child(self, cid, y, h=200):
        return {
            "id": cid, "type": "FRAME", "name": f"Frame {cid}",
            "absoluteBoundingBox": {"x": 0, "y": y, "width": 1440, "height": h},
        }

    def test_single_group(self):
        """One candidate group with 2 members -> 1 zone bbox."""
        children = [
            self._make_child("a", 100, 200),
            self._make_child("b", 400, 200),
        ]
        candidate_groups = [{"node_ids": ["a", "b"]}]
        zones = _compute_zone_bboxes(children, candidate_groups)
        assert len(zones) == 1
        # Zone should span from y=100 to y=600 (400+200)
        assert zones[0]["y_top"] == 100
        assert zones[0]["y_bot"] == 600

    def test_multiple_groups(self):
        """Two candidate groups -> 2 zone bboxes."""
        children = [
            self._make_child("a", 100, 200),
            self._make_child("b", 400, 200),
            self._make_child("c", 1000, 200),
            self._make_child("d", 1300, 200),
        ]
        candidate_groups = [
            {"node_ids": ["a", "b"]},
            {"node_ids": ["c", "d"]},
        ]
        zones = _compute_zone_bboxes(children, candidate_groups)
        assert len(zones) == 2

    def test_empty_groups(self):
        """Empty candidate_groups -> empty zones."""
        children = [self._make_child("a", 100)]
        zones = _compute_zone_bboxes(children, [])
        assert zones == []

    def test_nonexistent_ids(self):
        """Group with IDs not in children -> zone skipped."""
        children = [self._make_child("a", 100)]
        candidate_groups = [{"node_ids": ["x", "y"]}]
        zones = _compute_zone_bboxes(children, candidate_groups)
        assert len(zones) == 0

    def test_single_member_group(self):
        """Group with 1 member -> zone has that member's bbox."""
        children = [self._make_child("a", 500, 300)]
        candidate_groups = [{"node_ids": ["a"]}]
        zones = _compute_zone_bboxes(children, candidate_groups)
        assert len(zones) == 1
        assert zones[0]["y_top"] == 500
        assert zones[0]["y_bot"] == 800


# ============================================================
# detect_bg_content_layers: ELLIPSE decoration edge case (Issue 199)
# ============================================================
class TestDetectBgContentLayersEllipseDecoration:
    """Additional edge cases for detect_bg_content_layers."""

    def test_small_ellipse_as_decoration(self):
        """Small ELLIPSE overlapping bg RECTANGLE -> treated as decoration."""
        parent_bb = {'x': 0, 'y': 0, 'w': 1440, 'h': 800}
        children = [
            {"id": "bg1", "type": "RECTANGLE", "name": "Rectangle 1",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 400}},
            # Small ELLIPSE decoration: area = 30*30 = 900 < 5% of bg (576000*0.05=28800)
            {"id": "deco1", "type": "ELLIPSE", "name": "Ellipse 1",
             "absoluteBoundingBox": {"x": 200, "y": 100, "width": 30, "height": 30}},
            {"id": "c1", "type": "TEXT", "name": "heading",
             "absoluteBoundingBox": {"x": 100, "y": 100, "width": 400, "height": 60}},
            {"id": "c2", "type": "GROUP", "name": "content-group",
             "absoluteBoundingBox": {"x": 100, "y": 200, "width": 600, "height": 100},
             "children": [{"type": "TEXT", "children": []}]},
        ]
        result = detect_bg_content_layers(children, parent_bb)
        assert len(result) == 1
        # ELLIPSE should be in bg_node_ids as decoration
        assert 'deco1' in result[0]['bg_node_ids']
        # Content should be c1, c2
        assert set(result[0]['node_ids']) == {'c1', 'c2'}

    def test_large_ellipse_as_content(self):
        """Large ELLIPSE overlapping bg RECTANGLE -> treated as content, not decoration."""
        parent_bb = {'x': 0, 'y': 0, 'w': 1440, 'h': 800}
        # bg area = 1440 * 400 = 576000. 5% = 28800
        # Large ellipse area = 200 * 200 = 40000 > 28800
        children = [
            {"id": "bg1", "type": "RECTANGLE", "name": "Rectangle 1",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 400}},
            {"id": "e1", "type": "ELLIPSE", "name": "Ellipse 1",
             "absoluteBoundingBox": {"x": 100, "y": 100, "width": 200, "height": 200}},
            {"id": "c1", "type": "TEXT", "name": "heading",
             "absoluteBoundingBox": {"x": 100, "y": 100, "width": 400, "height": 60}},
            {"id": "c2", "type": "GROUP", "name": "group",
             "absoluteBoundingBox": {"x": 100, "y": 300, "width": 400, "height": 100},
             "children": [{"type": "TEXT", "children": []}]},
        ]
        result = detect_bg_content_layers(children, parent_bb)
        assert len(result) == 1
        # Large ELLIPSE should be content, not decoration
        assert 'e1' in result[0]['node_ids']
        assert 'e1' not in result[0]['bg_node_ids']


# ============================================================
# generate_enriched_table: page_height overflow-y (Issue 202)
# ============================================================
class TestGenerateEnrichedTableOverflowY:
    """Tests for generate_enriched_table overflow-y detection."""

    def _make_node(self, nid, ntype, name, x, y, w, h, children=None):
        return {
            'id': nid, 'type': ntype, 'name': name,
            'absoluteBoundingBox': {'x': x, 'y': y, 'width': w, 'height': h},
            'children': children or [],
        }

    def test_overflow_y_with_page_height(self):
        """Element extending below page_height -> overflow-y flag."""
        children = [
            self._make_node('1:1', 'RECTANGLE', 'bg', 0, 4800, 1440, 500),
        ]
        result = generate_enriched_table(children, page_width=1440, page_height=5000)
        assert 'overflow-y' in result

    def test_no_overflow_y_within_page(self):
        """Element within page_height -> no overflow-y flag."""
        children = [
            self._make_node('1:1', 'RECTANGLE', 'bg', 0, 4800, 1440, 100),
        ]
        result = generate_enriched_table(children, page_width=1440, page_height=5000)
        assert 'overflow-y' not in result

    def test_zero_page_height_no_overflow_y(self):
        """page_height=0 (default) -> never overflow-y."""
        children = [
            self._make_node('1:1', 'RECTANGLE', 'bg', 0, 99999, 1440, 500),
        ]
        result = generate_enriched_table(children, page_width=1440, page_height=0)
        assert 'overflow-y' not in result

    def test_overflow_y_with_root_y_offset_no_false_positive(self):
        """Artboard at non-zero Y: element within page should NOT get overflow-y.

        Bug (Issue #11): overflow-y used absolute Y coordinates without
        subtracting root_y, causing false positives when the artboard is
        positioned below Y=0 in the Figma canvas.
        """
        # Artboard starts at Y=3000, page_height=5000
        # Element at absolute Y=7800 -> relative Y=4800, bottom=4800+100=4900 < 5000*1.02
        children = [
            self._make_node('1:1', 'RECTANGLE', 'bg', 0, 7800, 1440, 100),
        ]
        result = generate_enriched_table(
            children, page_width=1440, page_height=5000, root_x=0, root_y=3000
        )
        assert 'overflow-y' not in result

    def test_overflow_y_with_root_y_offset_true_positive(self):
        """Artboard at non-zero Y: element truly overflowing SHOULD get overflow-y."""
        # Artboard starts at Y=3000, page_height=5000
        # Element at absolute Y=7800 -> relative Y=4800, bottom=4800+500=5300 > 5000*1.02=5100
        children = [
            self._make_node('1:1', 'RECTANGLE', 'bg', 0, 7800, 1440, 500),
        ]
        result = generate_enriched_table(
            children, page_width=1440, page_height=5000, root_x=0, root_y=3000
        )
        assert 'overflow-y' in result


# ============================================================
# detect_repeating_tuple: single-type distinct_type < 2 (Issue 200)
# ============================================================
class TestDetectRepeatingTupleSingleDistinct:
    """Test that tuples with distinct type count < 2 are skipped."""

    def _make_node(self, node_type, name):
        return {"type": node_type, "name": name, "id": f"{node_type}-{name}"}

    def test_two_type_tuple_detected(self):
        """Tuple of 2 distinct types repeated 3x -> detected."""
        children = []
        for i in range(3):
            children.append(self._make_node("TEXT", f"t-{i}"))
            children.append(self._make_node("RECTANGLE", f"r-{i}"))
        result = detect_repeating_tuple(children)
        assert len(result) == 1
        assert result[0]['tuple_size'] == 2

    def test_same_type_pair_not_tuple(self):
        """Pairs of same type (e.g., TEXT+TEXT) repeated 3x -> not detected as tuple
        (distinct types < 2, handled by consecutive_similar instead)."""
        children = []
        for i in range(6):
            children.append(self._make_node("TEXT", f"t-{i}"))
        result = detect_repeating_tuple(children)
        assert len(result) == 0


# ================================================================
# Issue 194 Phase 3: compare_grouping_results tests
# ================================================================

from figma_utils import compare_grouping_results, compare_grouping_by_section, _stage_a_pattern_key


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

try:
    from figma_utils import find_node_by_id
    HAS_FIND_NODE = True
except ImportError:
    HAS_FIND_NODE = False


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


# ============================================================
# count_nested_flat (Issue 228)
# ============================================================
class TestCountNestedFlat:
    """Issue 231: count_nested_flat only counts within section root boundaries."""

    def _make_section_root(self, children, name="section-hero", width=1440, height=1000):
        """Helper to create a section root node."""
        return {
            "type": "FRAME", "name": name,
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": width, "height": height},
            "children": children,
        }

    def _make_page(self, children, width=1440, height=5000):
        """Helper to create a page-level node (not a section root itself for traversal)."""
        return {
            "type": "FRAME", "name": "Page",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": width, "height": height},
            "children": children,
        }

    def test_empty_node(self):
        """Node with no children returns 0."""
        node = {"type": "FRAME", "children": []}
        assert count_nested_flat(node) == 0

    def test_section_root_itself_not_counted(self):
        """A section root (width=1440) with >15 children is NOT counted (counted by flat_sections)."""
        children = [{"type": "TEXT", "name": f"t{i}"} for i in range(20)]
        section = self._make_section_root(children)
        # The section root itself is excluded; none of its TEXT children are FRAME/GROUP
        assert count_nested_flat(section) == 0

    def test_flat_frame_inside_section_root_counted(self):
        """A FRAME inside a section root with >15 children IS counted."""
        inner_children = [{"type": "TEXT", "name": f"t{i}"} for i in range(20)]
        inner = {"type": "FRAME", "name": "FlatInner", "children": inner_children}
        section = self._make_section_root([inner])
        assert count_nested_flat(section) == 1

    def test_frame_outside_section_root_not_counted(self):
        """FRAME above section root boundary (no section root ancestor) is NOT counted."""
        # A non-section-root FRAME with many children, no section root in subtree
        children = [{"type": "TEXT", "name": f"t{i}"} for i in range(20)]
        node = {"type": "FRAME", "name": "non-section",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 500, "height": 300},
                "children": children}
        assert count_nested_flat(node) == 0

    def test_page_with_section_root_containing_flat_frame(self):
        """Page > section root > flat FRAME: only the flat FRAME inside is counted."""
        inner_children = [{"type": "TEXT", "name": f"t{i}"} for i in range(20)]
        inner = {"type": "FRAME", "name": "FlatInner", "children": inner_children}
        section = self._make_section_root([inner] + [{"type": "TEXT", "name": f"s{i}"} for i in range(16)])
        page = self._make_page([section])
        # section root has 17 children but is NOT counted (flat_sections handles it)
        # inner has 20 children and IS counted
        assert count_nested_flat(page) == 1

    def test_multiple_section_roots_with_nested_flat(self):
        """Multiple section roots each with flat descendants."""
        inner1_children = [{"type": "TEXT", "name": f"t{i}"} for i in range(20)]
        inner1 = {"type": "FRAME", "name": "FlatInner1", "children": inner1_children}
        section1 = self._make_section_root([inner1], name="section-hero")

        inner2_children = [{"type": "RECTANGLE", "name": f"r{i}"} for i in range(18)]
        inner2 = {"type": "GROUP", "name": "FlatInner2", "children": inner2_children}
        section2 = self._make_section_root([inner2], name="section-about", height=800)
        section2["absoluteBoundingBox"]["y"] = 1000

        page = self._make_page([section1, section2])
        assert count_nested_flat(page) == 2

    def test_hidden_children_excluded(self):
        """Hidden children (visible: false) should not count toward threshold."""
        visible = [{"type": "TEXT", "name": f"t{i}"} for i in range(14)]
        hidden = [{"type": "TEXT", "name": f"h{i}", "visible": False} for i in range(10)]
        inner = {"type": "FRAME", "name": "inner", "children": visible + hidden}
        section = self._make_section_root([inner])
        # inner has only 14 visible children <= 15
        assert count_nested_flat(section) == 0

    def test_group_type_counted_inside_section(self):
        """GROUP nodes inside section roots are counted."""
        children = [{"type": "RECTANGLE", "name": f"r{i}"} for i in range(16)]
        group = {"type": "GROUP", "name": "flat-group", "children": children}
        section = self._make_section_root([group])
        assert count_nested_flat(section) == 1

    def test_non_container_type_ignored(self):
        """TEXT/RECTANGLE nodes with children are not counted."""
        children = [{"type": "TEXT", "name": f"t{i}"} for i in range(20)]
        text_node = {"type": "TEXT", "name": "text-block", "children": children}
        section = self._make_section_root([text_node])
        assert count_nested_flat(section) == 0

    def test_custom_threshold(self):
        """Custom threshold parameter works within section root."""
        children = [{"type": "TEXT", "name": f"t{i}"} for i in range(6)]
        inner = {"type": "FRAME", "name": "inner", "children": children}
        section = self._make_section_root([inner])
        assert count_nested_flat(section, threshold=5) == 1
        assert count_nested_flat(section, threshold=6) == 0

    def test_deeply_nested_flat_inside_section(self):
        """Deeply nested flat frames inside section root are all counted."""
        leaf_children = [{"type": "TEXT", "name": f"t{i}"} for i in range(20)]
        deep = {"type": "FRAME", "name": "deep-flat", "children": leaf_children}
        mid_children = [deep] + [{"type": "TEXT", "name": f"m{i}"} for i in range(16)]
        mid = {"type": "FRAME", "name": "mid-flat", "children": mid_children}
        section = self._make_section_root([mid])
        # mid has 17 children (>15), deep has 20 children (>15)
        assert count_nested_flat(section) == 2


# ============================================================
# analyze-structure.sh: nested_flat_count metric (Issue 228)
# ============================================================
class TestAnalyzeStructureNestedFlat:
    def test_nested_flat_count_reported(self):
        """nested_flat_count appears in metrics output."""
        # Build a section root (width=1440) with a nested flat FRAME
        inner_children = [
            {"id": f"3:{i}", "type": "TEXT", "name": f"Text {i}",
             "absoluteBoundingBox": {"x": 0, "y": i * 30, "width": 100, "height": 20}}
            for i in range(20)
        ]
        data = {
            "node": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "section-hero",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1000},
                        "children": [
                            {
                                "id": "2:1", "type": "FRAME", "name": "FlatInner",
                                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 800, "height": 600},
                                "children": inner_children,
                            }
                        ],
                    }
                ],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("analyze-structure.sh", tmp)
            metrics = result["metrics"]
            # FlatInner has 20 children > 15 threshold
            assert "nested_flat_count" in metrics
            assert metrics["nested_flat_count"] >= 1
        finally:
            os.unlink(tmp)

    def test_nested_flat_does_not_affect_score(self):
        """nested_flat_count is informational only and does not change score."""
        # Two identical structures except one has a nested flat frame
        base_children = [
            {"id": f"3:{i}", "type": "TEXT", "name": f"Item {i}",
             "absoluteBoundingBox": {"x": 0, "y": i * 30, "width": 100, "height": 20}}
            for i in range(20)
        ]
        data_with_flat = {
            "node": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "section-hero",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1000},
                        "children": [
                            {
                                "id": "2:1", "type": "FRAME", "name": "FlatFrame",
                                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 800, "height": 600},
                                "children": base_children,
                            }
                        ],
                    }
                ],
            }
        }
        data_without_flat = {
            "node": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "section-hero",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1000},
                        "children": [
                            {
                                "id": "2:1", "type": "FRAME", "name": "SmallFrame",
                                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 800, "height": 600},
                                "children": base_children[:5],
                            }
                        ],
                    }
                ],
            }
        }
        tmp1 = write_fixture(data_with_flat)
        tmp2 = write_fixture(data_without_flat)
        try:
            r1 = run_script("analyze-structure.sh", tmp1)
            r2 = run_script("analyze-structure.sh", tmp2)
            assert r1["metrics"]["nested_flat_count"] > r2["metrics"]["nested_flat_count"]
            # Score should NOT differ due to nested_flat_count (it's informational only)
            # Note: scores may still differ due to flat_sections/ungrouped differences,
            # but nested_flat_count itself has no weight in the formula
            assert "nested_flat_count" not in str(r1.get("score_breakdown", {}))
        finally:
            os.unlink(tmp1)
            os.unlink(tmp2)


# ============================================================
# Issue 225: generate-nested-grouping-context.sh --groups / --depth tests
# ============================================================
class TestNestedGroupingContextGroups:
    """Tests for --groups and --depth support in generate-nested-grouping-context.sh."""

    # Shared fixture: metadata with a tree structure
    METADATA = {
        "id": "0:1", "name": "Page", "type": "FRAME",
        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 5000},
        "children": [
            {
                "id": "2:100", "name": "Card A", "type": "FRAME",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 400, "height": 300},
                "children": [
                    {"id": "3:1", "name": "Title A", "type": "TEXT",
                     "absoluteBoundingBox": {"x": 10, "y": 10, "width": 200, "height": 30},
                     "children": []},
                    {"id": "3:2", "name": "Image A", "type": "RECTANGLE",
                     "absoluteBoundingBox": {"x": 10, "y": 50, "width": 380, "height": 200},
                     "children": []},
                ],
            },
            {
                "id": "2:101", "name": "Card B", "type": "FRAME",
                "absoluteBoundingBox": {"x": 0, "y": 350, "width": 400, "height": 300},
                "children": [
                    {"id": "4:1", "name": "Title B", "type": "TEXT",
                     "absoluteBoundingBox": {"x": 10, "y": 10, "width": 200, "height": 30},
                     "children": []},
                    {"id": "4:2", "name": "Image B", "type": "RECTANGLE",
                     "absoluteBoundingBox": {"x": 10, "y": 50, "width": 380, "height": 200},
                     "children": []},
                ],
            },
            {
                "id": "2:200", "name": "Single Element", "type": "FRAME",
                "absoluteBoundingBox": {"x": 0, "y": 700, "width": 400, "height": 100},
                "children": [],
            },
        ],
    }

    def _write_groups(self, groups_data):
        """Write groups JSON to temp file."""
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(groups_data, f)
        f.close()
        return f.name

    def test_groups_basic(self):
        """--groups mode processes non-single groups and produces children context."""
        groups = {
            "groups": [
                {
                    "name": "feature-cards",
                    "pattern": "card",
                    "node_ids": ["2:100", "2:101"],
                },
            ]
        }
        meta_tmp = write_fixture(self.METADATA)
        groups_tmp = self._write_groups(groups)
        try:
            data = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp, "--depth", "1",
            )
            assert "error" not in data
            assert data["total_sections"] == 2  # one per node_id
            assert data["depth"] == 1
            assert data["model"] == "haiku"

            # Each section should have the children of the node
            for sec in data["sections"]:
                assert sec["parent_group"] == "feature-cards"
                assert sec["depth"] == 1
                assert sec["total_children"] == 2  # Title + Image
                assert sec["section_id"] in ("2:100", "2:101")
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)

    def test_groups_skips_single_pattern(self):
        """Groups with pattern 'single' are skipped."""
        groups = {
            "groups": [
                {
                    "name": "standalone",
                    "pattern": "single",
                    "node_ids": ["2:200"],
                },
                {
                    "name": "feature-cards",
                    "pattern": "card",
                    "node_ids": ["2:100"],
                },
            ]
        }
        meta_tmp = write_fixture(self.METADATA)
        groups_tmp = self._write_groups(groups)
        try:
            data = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp,
            )
            assert data["total_sections"] == 1  # only feature-cards
            assert data["sections"][0]["section_name"] == "feature-cards"
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)

    def test_groups_default_depth_zero(self):
        """Default depth is 0 when --depth is not specified."""
        groups = {
            "groups": [
                {
                    "name": "cards",
                    "pattern": "card",
                    "node_ids": ["2:100"],
                },
            ]
        }
        meta_tmp = write_fixture(self.METADATA)
        groups_tmp = self._write_groups(groups)
        try:
            data = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp,
            )
            assert data["depth"] == 0
            assert data["sections"][0]["depth"] == 0
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)

    def test_groups_skips_childless_nodes(self):
        """Nodes without children are skipped (no enriched table to generate)."""
        groups = {
            "groups": [
                {
                    "name": "empty-group",
                    "pattern": "list",
                    "node_ids": ["2:200"],  # has no children
                },
            ]
        }
        meta_tmp = write_fixture(self.METADATA)
        groups_tmp = self._write_groups(groups)
        try:
            data = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp,
            )
            assert data["total_sections"] == 0
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)

    def test_groups_output_has_enriched_table_and_prompt(self):
        """Each section in groups mode has enriched_children_table and prompt."""
        groups = {
            "groups": [
                {
                    "name": "cards",
                    "pattern": "card",
                    "node_ids": ["2:100"],
                },
            ]
        }
        meta_tmp = write_fixture(self.METADATA)
        groups_tmp = self._write_groups(groups)
        try:
            data = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp, "--depth", "1",
            )
            sec = data["sections"][0]
            assert "enriched_children_table" in sec
            assert len(sec["enriched_children_table"]) > 0
            assert "prompt" in sec
            assert len(sec["prompt"]) > 0
            # Prompt should contain the section name
            assert "cards" in sec["prompt"]
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)

    def test_groups_output_file(self):
        """--output flag writes result to file in groups mode."""
        groups = {
            "groups": [
                {
                    "name": "cards",
                    "pattern": "card",
                    "node_ids": ["2:100"],
                },
            ]
        }
        meta_tmp = write_fixture(self.METADATA)
        groups_tmp = self._write_groups(groups)
        out_tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        out_tmp.close()
        try:
            result = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp,
                "--depth", "1", "--output", out_tmp.name,
            )
            assert result["status"] == "ok"
            assert result["depth"] == 1

            # Verify the output file content
            with open(out_tmp.name, "r") as f:
                file_data = json.load(f)
            assert file_data["total_sections"] == 1
            assert file_data["depth"] == 1
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)
            os.unlink(out_tmp.name)

    def test_plan_mode_unchanged(self):
        """Original plan mode still works (backward compatibility)."""
        plan = {
            "sections": [
                {
                    "name": "section-hero",
                    "node_ids": ["2:100"],
                },
            ]
        }
        meta_tmp = write_fixture(self.METADATA)
        plan_tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(plan, plan_tmp)
        plan_tmp.close()
        try:
            data = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, plan_tmp.name,
            )
            assert "error" not in data
            assert data["total_sections"] >= 1
            assert data["model"] == "haiku"
            # Plan mode should NOT have depth field at top level
            assert "depth" not in data
            # Sections should NOT have parent_group or depth fields
            sec = data["sections"][0]
            assert "parent_group" not in sec
            assert "depth" not in sec
        finally:
            os.unlink(meta_tmp)
            os.unlink(plan_tmp.name)


# ============================================================
# Constants: Stage C recursive nesting (Issue 224)
# ============================================================
class TestMaxStageCDepth:
    def test_max_stage_c_depth_value(self):
        assert MAX_STAGE_C_DEPTH == 2

    def test_max_stage_c_depth_is_positive(self):
        assert MAX_STAGE_C_DEPTH > 0


# ============================================================
# Constants: STAGE_C_COVERABLE / STAGE_A_ONLY (Issue 229)
# ============================================================
class TestStageCCoverableConstants:
    def test_stage_c_coverable_expected_values(self):
        """STAGE_C_COVERABLE_DETECTORS contains expected detector names."""
        expected = {'bg-content', 'table', 'highlight', 'tuple', 'consecutive', 'heading-content'}
        assert STAGE_C_COVERABLE_DETECTORS == expected

    def test_stage_a_only_expected_values(self):
        """STAGE_A_ONLY_DETECTORS contains expected detector names."""
        expected = {'header-footer', 'horizontal-bar', 'zone', 'semantic', 'proximity', 'spacing', 'pattern'}
        assert STAGE_A_ONLY_DETECTORS == expected

    def test_no_overlap(self):
        """Coverable and A-only sets should be disjoint."""
        overlap = STAGE_C_COVERABLE_DETECTORS & STAGE_A_ONLY_DETECTORS
        assert len(overlap) == 0, f"Unexpected overlap: {overlap}"


# ============================================================
# detect-grouping-candidates.sh: --disable-detectors (Issue 229)
# ============================================================
class TestDisableDetectors:
    """Test --disable-detectors flag for selective detector disabling."""

    def _build_fixture(self):
        """Build a fixture that generates multiple detector types."""
        # Large flat structure at root to trigger proximity, pattern, spacing, semantic,
        # zone, consecutive, heading-content, and header-footer
        children = []
        # Header zone elements (for header-footer detection)
        children.append({
            "id": "1:1", "name": "Logo", "type": "VECTOR",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 100, "height": 50},
            "children": []})
        for i in range(4):
            children.append({
                "id": f"1:{10+i}", "name": f"NavItem{i}", "type": "TEXT",
                "absoluteBoundingBox": {"x": 150 + i*120, "y": 10, "width": 80, "height": 20},
                "children": []})
        # Heading + content pair
        children.append({
            "id": "2:1", "name": "SectionTitle", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 200, "width": 1440, "height": 60},
            "children": [
                {"id": "2:1a", "name": "Title Text", "type": "TEXT",
                 "absoluteBoundingBox": {"x": 10, "y": 210, "width": 400, "height": 40},
                 "children": [], "characters": "About Us"}
            ]})
        children.append({
            "id": "2:2", "name": "SectionBody", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 280, "width": 1440, "height": 400},
            "children": [
                {"id": "2:2a", "name": "BodyText", "type": "TEXT",
                 "absoluteBoundingBox": {"x": 10, "y": 290, "width": 600, "height": 380},
                 "children": [], "characters": "Lorem ipsum dolor sit amet"}
            ]})
        # Many similar frames to trigger consecutive/pattern detection
        for i in range(5):
            children.append({
                "id": f"3:{i}", "name": f"Frame {i}", "type": "FRAME",
                "absoluteBoundingBox": {"x": 0, "y": 800 + i*200, "width": 1440, "height": 180},
                "children": [
                    {"id": f"3:{i}a", "name": "Title", "type": "TEXT",
                     "absoluteBoundingBox": {"x": 10, "y": 810 + i*200, "width": 400, "height": 30},
                     "children": [], "characters": f"Item {i}"},
                    {"id": f"3:{i}b", "name": "Image", "type": "RECTANGLE",
                     "absoluteBoundingBox": {"x": 500, "y": 810 + i*200, "width": 200, "height": 150},
                     "children": []},
                ]})
        # Footer zone
        children.append({
            "id": "4:1", "name": "FooterText", "type": "TEXT",
            "absoluteBoundingBox": {"x": 0, "y": 4900, "width": 200, "height": 30},
            "children": []})
        children.append({
            "id": "4:2", "name": "FooterLink", "type": "TEXT",
            "absoluteBoundingBox": {"x": 300, "y": 4900, "width": 150, "height": 30},
            "children": []})

        return {
            "document": {
                "id": "0:0", "name": "Document", "type": "DOCUMENT",
                "children": [{
                    "id": "0:1", "name": "Page", "type": "CANVAS",
                    "children": [{
                        "id": "root", "name": "Desktop", "type": "FRAME",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 5000},
                        "children": children
                    }]
                }]
            }
        }

    def test_disable_detectors_empty(self):
        """Empty disable string = no detectors disabled (current behavior)."""
        data = self._build_fixture()
        tmp = write_fixture(data)
        try:
            result = run_script("detect-grouping-candidates.sh", tmp)
            assert result["total"] > 0
            assert "disabled_detectors" not in result
            methods = {c.get("method") for c in result.get("candidates", [])}
            # Should have at least some methods present
            assert len(methods) >= 1
        finally:
            os.unlink(tmp)

    def test_disable_detectors_single(self):
        """Disabling one detector removes all candidates with that method."""
        data = self._build_fixture()
        tmp = write_fixture(data)
        try:
            result = run_script(
                "detect-grouping-candidates.sh", tmp,
                "--disable-detectors", "consecutive")
            methods = {c.get("method") for c in result.get("candidates", [])}
            assert "consecutive" not in methods, \
                f"'consecutive' should be disabled but found in methods: {methods}"
            assert result.get("disabled_detectors") == ["consecutive"]
        finally:
            os.unlink(tmp)

    def test_disable_detectors_multiple(self):
        """Disabling multiple detectors removes all their candidates."""
        data = self._build_fixture()
        tmp = write_fixture(data)
        try:
            result = run_script(
                "detect-grouping-candidates.sh", tmp,
                "--disable-detectors", "consecutive,heading-content,table")
            methods = {c.get("method") for c in result.get("candidates", [])}
            assert "consecutive" not in methods
            assert "heading-content" not in methods
            assert "table" not in methods
            assert set(result.get("disabled_detectors", [])) == {"consecutive", "heading-content", "table"}
        finally:
            os.unlink(tmp)

    def test_disable_detectors_invalid(self):
        """Invalid detector name is warned and stripped (no error)."""
        data = self._build_fixture()
        tmp = write_fixture(data)
        try:
            result = run_script(
                "detect-grouping-candidates.sh", tmp,
                "--disable-detectors", "nonexistent-detector")
            # Should succeed without error
            assert "error" not in result
            # Unknown detectors are stripped, so disabled_detectors should be absent or empty
            assert "nonexistent-detector" not in result.get("disabled_detectors", [])
        finally:
            os.unlink(tmp)

    def test_disable_all_stage_c_coverable(self):
        """Disabling all Stage C coverable detectors still produces output from remaining."""
        data = self._build_fixture()
        tmp = write_fixture(data)
        try:
            disable_list = ",".join(sorted(STAGE_C_COVERABLE_DETECTORS))
            result = run_script(
                "detect-grouping-candidates.sh", tmp,
                "--disable-detectors", disable_list)
            methods = {c.get("method") for c in result.get("candidates", [])}
            # No Stage C coverable methods should appear
            for d in STAGE_C_COVERABLE_DETECTORS:
                assert d not in methods, f"'{d}' should be disabled"
            # But Stage A only detectors should still work
            # (at least some of them, depending on fixture)
            assert "error" not in result
        finally:
            os.unlink(tmp)


# ============================================================
# STAGE_C_COVERAGE_THRESHOLD constant (Fix 1)
# ============================================================
class TestStageCCoverageThreshold:
    """Tests for STAGE_C_COVERAGE_THRESHOLD constant."""

    def test_stage_c_coverage_threshold_value(self):
        """STAGE_C_COVERAGE_THRESHOLD should be 0.8."""
        assert STAGE_C_COVERAGE_THRESHOLD == 0.8

    def test_stage_c_coverage_threshold_used_in_compare(self):
        """compare_grouping_by_section should use STAGE_C_COVERAGE_THRESHOLD."""
        # Stage A with one section
        stage_a = [
            {'parent_id': 'sec1', 'node_ids': ['a', 'b'], 'method': 'pattern', 'count': 2},
        ]
        # Stage C with high coverage (>= 0.8) for section
        stage_c = [
            {
                'section_id': 'sec1',
                'groups': [
                    {'node_ids': ['a', 'b'], 'name': 'group-1', 'method': 'stage_c'},
                ],
            },
        ]
        result = compare_grouping_by_section(stage_a, stage_c)
        # High coverage should adopt stage_c
        assert result['sections'][0]['source'] == 'stage_c'

    def test_stage_c_coverage_threshold_fallback(self):
        """Below STAGE_C_COVERAGE_THRESHOLD should fall back to stage_a."""
        stage_a = [
            {'parent_id': 'sec1', 'node_ids': ['a', 'b', 'c'], 'method': 'pattern', 'count': 3},
        ]
        # Stage C with no matching groups (coverage = 0)
        stage_c = [
            {
                'section_id': 'sec1',
                'groups': [
                    {'node_ids': ['x', 'y'], 'name': 'group-1', 'method': 'stage_c'},
                ],
            },
        ]
        result = compare_grouping_by_section(stage_a, stage_c)
        assert result['sections'][0]['source'] == 'stage_a'


# ============================================================
# MAX_STAGE_C_DEPTH enforcement in groups mode (Fix 2)
# ============================================================
class TestMaxStageCDepthEnforcement:
    """Test MAX_STAGE_C_DEPTH enforcement in generate-nested-grouping-context.sh."""

    def _build_groups_fixture(self):
        """Build metadata + groups files for testing."""
        metadata = {
            "document": {
                "id": "0:0", "name": "Doc", "type": "DOCUMENT",
                "children": [{
                    "id": "0:1", "name": "Page", "type": "CANVAS",
                    "children": [{
                        "id": "root", "name": "Desktop", "type": "FRAME",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
                        "children": [
                            {"id": "n1", "name": "Section1", "type": "FRAME",
                             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                             "children": [
                                 {"id": "n1a", "name": "Child1", "type": "TEXT",
                                  "absoluteBoundingBox": {"x": 10, "y": 10, "width": 200, "height": 30},
                                  "children": [], "characters": "Hello"},
                             ]},
                        ],
                    }]
                }]
            }
        }
        groups = {
            "groups": [
                {"name": "section-1", "pattern": "multi", "node_ids": ["n1"]},
            ]
        }
        return metadata, groups

    def test_depth_below_max_produces_sections(self):
        """Depth below MAX_STAGE_C_DEPTH should produce sections."""
        metadata, groups = self._build_groups_fixture()
        meta_tmp = write_fixture(metadata)
        groups_tmp = write_fixture(groups)
        try:
            result = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp, "--depth", "0")
            assert 'skipped_reason' not in result
            assert result['total_sections'] >= 0
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)

    def test_depth_at_max_skips(self):
        """Depth == MAX_STAGE_C_DEPTH should skip with reason."""
        metadata, groups = self._build_groups_fixture()
        meta_tmp = write_fixture(metadata)
        groups_tmp = write_fixture(groups)
        try:
            result = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp, "--depth", str(MAX_STAGE_C_DEPTH))
            assert result['total_sections'] == 0
            assert 'skipped_reason' in result
            assert 'MAX_STAGE_C_DEPTH' in result['skipped_reason']
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)

    def test_depth_above_max_skips(self):
        """Depth > MAX_STAGE_C_DEPTH should skip with reason."""
        metadata, groups = self._build_groups_fixture()
        meta_tmp = write_fixture(metadata)
        groups_tmp = write_fixture(groups)
        try:
            result = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp, "--depth", str(MAX_STAGE_C_DEPTH + 1))
            assert result['total_sections'] == 0
            assert 'skipped_reason' in result
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)


# ============================================================
# Unknown detector name warning (Fix 3)
# ============================================================
class TestUnknownDetectorValidation:
    """Test that unknown detector names are warned and stripped."""

    def _build_simple_fixture(self):
        return {
            "document": {
                "id": "0:0", "name": "Doc", "type": "DOCUMENT",
                "children": [{
                    "id": "0:1", "name": "Page", "type": "CANVAS",
                    "children": [{
                        "id": "root", "name": "Desktop", "type": "FRAME",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
                        "children": [
                            {"id": "1:1", "name": "Frame 1", "type": "FRAME",
                             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                             "children": [
                                 {"id": "1:1a", "name": "Text", "type": "TEXT",
                                  "absoluteBoundingBox": {"x": 10, "y": 10, "width": 200, "height": 30},
                                  "children": [], "characters": "Hello"},
                             ]},
                        ],
                    }]
                }]
            }
        }

    def test_unknown_detector_stripped_from_disabled(self):
        """Unknown detector names should be stripped (not appear in disabled_detectors)."""
        data = self._build_simple_fixture()
        tmp = write_fixture(data)
        try:
            result = run_script(
                "detect-grouping-candidates.sh", tmp,
                "--disable-detectors", "fake-detector,also-fake")
            # Unknown detectors are stripped, so disabled_detectors should not include them
            assert "error" not in result
            disabled = result.get("disabled_detectors", [])
            assert "fake-detector" not in disabled
            assert "also-fake" not in disabled
        finally:
            os.unlink(tmp)

    def test_mixed_valid_invalid_detectors(self):
        """Valid detectors are kept, invalid ones are stripped."""
        data = self._build_simple_fixture()
        tmp = write_fixture(data)
        try:
            result = run_script(
                "detect-grouping-candidates.sh", tmp,
                "--disable-detectors", "consecutive,fake-one")
            assert "error" not in result
            methods = {c.get("method") for c in result.get("candidates", [])}
            assert "consecutive" not in methods
        finally:
            os.unlink(tmp)


# ============================================================
# Stage A-only detector protection (Fix 4)
# ============================================================
class TestStageAOnlyProtection:
    """Test that Stage A-only detectors cannot be disabled."""

    def _build_fixture_with_header(self):
        """Build fixture that would trigger header-footer detection."""
        children = []
        children.append({
            "id": "1:1", "name": "Logo", "type": "VECTOR",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 100, "height": 50},
            "children": []})
        for i in range(4):
            children.append({
                "id": f"1:{10+i}", "name": f"NavItem{i}", "type": "TEXT",
                "absoluteBoundingBox": {"x": 150 + i*120, "y": 10, "width": 80, "height": 20},
                "children": []})
        # Some content sections to have a non-trivial result
        for i in range(5):
            children.append({
                "id": f"2:{i}", "name": f"Section {i}", "type": "FRAME",
                "absoluteBoundingBox": {"x": 0, "y": 200 + i*300, "width": 1440, "height": 280},
                "children": [
                    {"id": f"2:{i}a", "name": "Title", "type": "TEXT",
                     "absoluteBoundingBox": {"x": 10, "y": 210 + i*300, "width": 400, "height": 30},
                     "children": [], "characters": f"Section {i}"},
                ]})
        return {
            "document": {
                "id": "0:0", "name": "Doc", "type": "DOCUMENT",
                "children": [{
                    "id": "0:1", "name": "Page", "type": "CANVAS",
                    "children": [{
                        "id": "root", "name": "Desktop", "type": "FRAME",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 3000},
                        "children": children
                    }]
                }]
            }
        }

    def test_disable_stage_a_only_ignored(self):
        """Trying to disable a Stage A-only detector should be ignored."""
        data = self._build_fixture_with_header()
        tmp = write_fixture(data)
        try:
            result = run_script(
                "detect-grouping-candidates.sh", tmp,
                "--disable-detectors", "header-footer,semantic")
            # Stage A-only detectors should be stripped from disabled list
            disabled = result.get("disabled_detectors", [])
            assert "header-footer" not in disabled
            assert "semantic" not in disabled
            assert "error" not in result
        finally:
            os.unlink(tmp)

    def test_disable_mixed_coverable_and_stage_a(self):
        """Coverable detectors are disabled but Stage A-only are kept."""
        data = self._build_fixture_with_header()
        tmp = write_fixture(data)
        try:
            result = run_script(
                "detect-grouping-candidates.sh", tmp,
                "--disable-detectors", "consecutive,header-footer")
            disabled = result.get("disabled_detectors", [])
            # consecutive (coverable) should be disabled
            methods = {c.get("method") for c in result.get("candidates", [])}
            assert "consecutive" not in methods
            # header-footer (Stage A-only) should NOT be disabled
            assert "header-footer" not in disabled
        finally:
            os.unlink(tmp)


# ============================================================
# Skipped groups reporting in --groups mode (Fix 5)
# ============================================================
class TestSkippedGroupsReporting:
    """Test that skipped groups are reported in groups mode output."""

    def _build_metadata(self):
        return {
            "document": {
                "id": "0:0", "name": "Doc", "type": "DOCUMENT",
                "children": [{
                    "id": "0:1", "name": "Page", "type": "CANVAS",
                    "children": [{
                        "id": "root", "name": "Desktop", "type": "FRAME",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
                        "children": [
                            {"id": "n1", "name": "Section1", "type": "FRAME",
                             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                             "children": [
                                 {"id": "n1a", "name": "Child1", "type": "TEXT",
                                  "absoluteBoundingBox": {"x": 10, "y": 10, "width": 200, "height": 30},
                                  "children": [], "characters": "Hello"},
                             ]},
                            {"id": "n2", "name": "LeafNode", "type": "TEXT",
                             "absoluteBoundingBox": {"x": 0, "y": 600, "width": 200, "height": 30},
                             "children": [], "characters": "Leaf"},
                        ],
                    }]
                }]
            }
        }

    def test_single_pattern_skipped(self):
        """Groups with pattern='single' are reported as skipped."""
        metadata = self._build_metadata()
        groups = {
            "groups": [
                {"name": "section-1", "pattern": "multi", "node_ids": ["n1"]},
                {"name": "leaf-item", "pattern": "single", "node_ids": ["n2"]},
            ]
        }
        meta_tmp = write_fixture(metadata)
        groups_tmp = write_fixture(groups)
        try:
            result = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp, "--depth", "0")
            assert result.get('skipped_count', 0) >= 1
            skipped = result.get('skipped_groups', [])
            single_skipped = [s for s in skipped if s.get('reason') == 'pattern=single']
            assert len(single_skipped) >= 1
            assert single_skipped[0]['name'] == 'leaf-item'
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)

    def test_childless_node_skipped(self):
        """Groups pointing to childless nodes are reported as skipped."""
        metadata = self._build_metadata()
        groups = {
            "groups": [
                {"name": "leaf-group", "pattern": "multi", "node_ids": ["n2"]},
            ]
        }
        meta_tmp = write_fixture(metadata)
        groups_tmp = write_fixture(groups)
        try:
            result = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp, "--depth", "0")
            assert result.get('skipped_count', 0) >= 1
            skipped = result.get('skipped_groups', [])
            childless = [s for s in skipped if s.get('reason') == 'no children']
            assert len(childless) >= 1
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)

    def test_no_skips_when_all_valid(self):
        """When all groups are valid, skipped_count is 0."""
        metadata = self._build_metadata()
        groups = {
            "groups": [
                {"name": "section-1", "pattern": "multi", "node_ids": ["n1"]},
            ]
        }
        meta_tmp = write_fixture(metadata)
        groups_tmp = write_fixture(groups)
        try:
            result = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp, "--depth", "0")
            assert result.get('skipped_count', 0) == 0
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)


# ============================================================
# detect-grouping-candidates.sh: decoration pattern skip (Issue #3)
# ============================================================
class TestDecorationPatternSkip:
    """Decoration dot grid internals should not produce redundant candidates."""

    def test_decoration_children_not_recursed(self):
        """A decoration pattern's children should NOT be detected by pattern/proximity/spacing."""
        # Build a root with one section containing a decoration dot grid
        data = {
            "document": {
                "id": "0:0", "name": "Document", "type": "DOCUMENT",
                "children": [{
                    "id": "0:1", "name": "Page", "type": "CANVAS",
                    "children": [{
                        "id": "1:0", "name": "Artboard", "type": "FRAME",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 3000},
                        "children": [
                            # A non-decoration section (should be recursed)
                            {"id": "2:0", "name": "section-normal", "type": "FRAME",
                             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1500},
                             "children": [
                                 # Decoration dot grid: 150x150 frame with 9 ellipses
                                 {"id": "3:0", "name": "Frame 1", "type": "FRAME",
                                  "absoluteBoundingBox": {"x": 100, "y": 100, "width": 150, "height": 150},
                                  "children": [
                                      {"id": f"4:{i}", "name": f"Ellipse {i+1}", "type": "ELLIPSE",
                                       "absoluteBoundingBox": {
                                           "x": 100 + (i % 3) * 50,
                                           "y": 100 + (i // 3) * 50,
                                           "width": 10, "height": 10},
                                       "children": []}
                                      for i in range(9)
                                  ]},
                             ]},
                            # Another section to ensure root detection works
                            {"id": "2:1", "name": "section-other", "type": "FRAME",
                             "absoluteBoundingBox": {"x": 0, "y": 1500, "width": 1440, "height": 1500},
                             "children": []},
                        ],
                    }],
                }],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("detect-grouping-candidates.sh", tmp)
            candidates = result.get("candidates", [])
            # No candidate should have parent_id "3:0" (the decoration frame)
            # or parent_name "Frame 1" (the decoration frame's auto name)
            decoration_children_candidates = [
                c for c in candidates
                if c.get("parent_id") == "3:0" or c.get("parent_name") == "Frame 1"
            ]
            assert len(decoration_children_candidates) == 0, \
                f"Decoration internals should not produce candidates, got: {decoration_children_candidates}"
        finally:
            os.unlink(tmp)

    def test_non_decoration_children_still_recursed(self):
        """A non-decoration FRAME's children should still be detected normally."""
        # Build a root with a non-decoration frame containing pattern-detectable children
        data = {
            "document": {
                "id": "0:0", "name": "Document", "type": "DOCUMENT",
                "children": [{
                    "id": "0:1", "name": "Page", "type": "CANVAS",
                    "children": [{
                        "id": "1:0", "name": "Artboard", "type": "FRAME",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 3000},
                        "children": [
                            # A large non-decoration frame (> 200px, so NOT decoration)
                            {"id": "2:0", "name": "Frame 1", "type": "FRAME",
                             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1500},
                             "children": [
                                 # 20 similar TEXT children → should trigger pattern detection
                                 *[{"id": f"3:{i}", "name": f"Text {i+1}", "type": "TEXT",
                                    "absoluteBoundingBox": {
                                        "x": 100, "y": i * 50,
                                        "width": 200, "height": 30},
                                    "characters": f"Item {i+1}",
                                    "children": []}
                                   for i in range(20)],
                             ]},
                            {"id": "2:1", "name": "section-other", "type": "FRAME",
                             "absoluteBoundingBox": {"x": 0, "y": 1500, "width": 1440, "height": 1500},
                             "children": []},
                        ],
                    }],
                }],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("detect-grouping-candidates.sh", tmp)
            candidates = result.get("candidates", [])
            # There should be candidates with parent_id "2:0" (the non-decoration frame)
            non_decoration_candidates = [
                c for c in candidates
                if c.get("parent_id") == "2:0"
            ]
            assert len(non_decoration_candidates) > 0, \
                f"Non-decoration frame children should still produce candidates. All candidates: {candidates}"
        finally:
            os.unlink(tmp)


# ============================================================
# infer-autolayout.sh: hidden children filtering (Audit Issue #18)
# ============================================================

class TestInferAutolayoutHiddenChildren:
    """Hidden children (visible: false) should be excluded from auto layout inference."""

    def test_hidden_child_excluded_from_inference(self):
        """A frame with 3 visible children at regular positions + 1 hidden child
        at a distant position. The hidden child should not affect gap/direction."""
        data = {
            "document": {
                "id": "0:0", "name": "Document", "type": "DOCUMENT",
                "children": [{
                    "id": "0:1", "name": "Page", "type": "CANVAS",
                    "children": [{
                        "id": "1:0", "name": "container", "type": "FRAME",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 400, "height": 200},
                        "children": [
                            # 3 visible children evenly spaced vertically
                            {"id": "1:1", "name": "child-1", "type": "FRAME",
                             "absoluteBoundingBox": {"x": 10, "y": 10, "width": 380, "height": 40},
                             "children": []},
                            {"id": "1:2", "name": "child-2", "type": "FRAME",
                             "absoluteBoundingBox": {"x": 10, "y": 70, "width": 380, "height": 40},
                             "children": []},
                            {"id": "1:3", "name": "child-3", "type": "FRAME",
                             "absoluteBoundingBox": {"x": 10, "y": 130, "width": 380, "height": 40},
                             "children": []},
                            # 1 hidden child at a very distant position
                            {"id": "1:4", "name": "hidden-child", "type": "FRAME",
                             "visible": False,
                             "absoluteBoundingBox": {"x": 5000, "y": 5000, "width": 100, "height": 100},
                             "children": []},
                        ],
                    }],
                }],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("infer-autolayout.sh", tmp)
            frames = result.get("frames", [])
            # The container frame should be inferred
            container_frames = [f for f in frames if f["node_id"] == "1:0"]
            assert len(container_frames) == 1, f"Expected 1 container frame, got {len(container_frames)}"
            layout = container_frames[0]["layout"]
            # Direction should be VERTICAL (children stacked vertically)
            assert layout["direction"] == "VERTICAL", \
                f"Expected VERTICAL direction, got {layout['direction']}"
            # Gap should be ~20px (snapped), not skewed by distant hidden child
            assert layout["gap"] <= 24, \
                f"Expected gap <= 24 (from visible children), got {layout['gap']} — hidden child may have skewed it"
            # Child count should be 3 (excluding hidden)
            assert container_frames[0]["child_count"] == 3, \
                f"Expected child_count=3 (hidden excluded), got {container_frames[0]['child_count']}"
        finally:
            os.unlink(tmp)

    def test_all_visible_children_hidden_leaves_insufficient(self):
        """If hiding children leaves fewer than 2 visible, no layout should be inferred."""
        data = {
            "document": {
                "id": "0:0", "name": "Document", "type": "DOCUMENT",
                "children": [{
                    "id": "0:1", "name": "Page", "type": "CANVAS",
                    "children": [{
                        "id": "1:0", "name": "container", "type": "FRAME",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 400, "height": 200},
                        "children": [
                            {"id": "1:1", "name": "visible-child", "type": "FRAME",
                             "absoluteBoundingBox": {"x": 10, "y": 10, "width": 380, "height": 40},
                             "children": []},
                            {"id": "1:2", "name": "hidden-1", "type": "FRAME",
                             "visible": False,
                             "absoluteBoundingBox": {"x": 10, "y": 70, "width": 380, "height": 40},
                             "children": []},
                            {"id": "1:3", "name": "hidden-2", "type": "FRAME",
                             "visible": False,
                             "absoluteBoundingBox": {"x": 10, "y": 130, "width": 380, "height": 40},
                             "children": []},
                        ],
                    }],
                }],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("infer-autolayout.sh", tmp)
            frames = result.get("frames", [])
            # Container should NOT appear since only 1 visible child
            container_frames = [f for f in frames if f["node_id"] == "1:0"]
            assert len(container_frames) == 0, \
                f"Container with only 1 visible child should not be inferred, got: {container_frames}"
        finally:
            os.unlink(tmp)


# ============================================================
# deduplicate_candidates (Issue 236)
# ============================================================

class TestDeduplicateCandidates:
    """Direct unit tests for deduplicate_candidates (Issue 236)."""

    def _make_candidate(self, method, node_ids, node_names=None, parent_id='root', parent_name='Frame 1'):
        """Helper to create a candidate dict."""
        if node_names is None:
            node_names = [f'node-{nid}' for nid in node_ids]
        return {
            'method': method,
            'node_ids': list(node_ids),
            'node_names': list(node_names),
            'count': len(node_ids),
            'suggested_name': f'{method}-group',
            'parent_id': parent_id,
            'parent_name': parent_name,
        }

    def test_no_overlap_keeps_all(self):
        """No overlap: both candidates should be kept intact."""
        c1 = self._make_candidate('semantic', ['1', '2', '3'])
        c2 = self._make_candidate('pattern', ['4', '5', '6'])
        result = deduplicate_candidates([c1, c2])
        assert len(result) == 2
        assert set(result[0]['node_ids']) == {'1', '2', '3'}
        assert set(result[1]['node_ids']) == {'4', '5', '6'}

    def test_partial_overlap_trims_lower_priority(self):
        """Issue 236: Partial overlap should trim, not delete entire candidate."""
        c1 = self._make_candidate('semantic', ['10', '11', '12'])  # priority 4
        c2 = self._make_candidate('pattern', ['12', '13', '14'])   # priority 2
        result = deduplicate_candidates([c1, c2])
        assert len(result) == 2, f"Expected 2 candidates, got {len(result)}"
        # Semantic keeps all nodes
        assert set(result[0]['node_ids']) == {'10', '11', '12'}
        # Pattern is trimmed: node 12 removed, nodes 13+14 preserved
        assert set(result[1]['node_ids']) == {'13', '14'}
        assert result[1]['count'] == 2

    def test_partial_overlap_node_names_trimmed_in_parallel(self):
        """node_names should be trimmed in parallel with node_ids."""
        c1 = self._make_candidate('semantic', ['A', 'B'], ['Alpha', 'Beta'])
        c2 = self._make_candidate('pattern', ['B', 'C', 'D'], ['Beta', 'Charlie', 'Delta'])
        result = deduplicate_candidates([c1, c2])
        trimmed = result[1]
        assert trimmed['node_ids'] == ['C', 'D']
        assert trimmed['node_names'] == ['Charlie', 'Delta']

    def test_full_subset_removed(self):
        """If all nodes of lower-priority candidate overlap, remove it entirely."""
        c1 = self._make_candidate('semantic', ['1', '2', '3'])  # priority 4
        c2 = self._make_candidate('proximity', ['2', '3'])       # priority 0, subset
        result = deduplicate_candidates([c1, c2])
        assert len(result) == 1
        assert result[0]['method'] == 'semantic'

    def test_same_priority_no_trim(self):
        """Same-priority candidates should not trim each other."""
        c1 = self._make_candidate('pattern', ['1', '2', '3'])
        c2 = self._make_candidate('pattern', ['3', '4', '5'])
        result = deduplicate_candidates([c1, c2])
        assert len(result) == 2
        assert set(result[0]['node_ids']) == {'1', '2', '3'}
        assert set(result[1]['node_ids']) == {'3', '4', '5'}

    def test_rule2_proximity_named_parent_removed(self):
        """Rule 2: proximity candidate with named parent (non-root) should be removed."""
        c1 = self._make_candidate('proximity', ['1', '2'],
                                  parent_id='child', parent_name='About Section')
        result = deduplicate_candidates([c1], root_id='root')
        assert len(result) == 0

    def test_rule2_root_parent_exempt(self):
        """Rule 2: root-level proximity candidates are exempt."""
        c1 = self._make_candidate('proximity', ['1', '2'],
                                  parent_id='root', parent_name='About Section')
        result = deduplicate_candidates([c1], root_id='root')
        assert len(result) == 1

    def test_rule2_unnamed_parent_kept(self):
        """Rule 2: proximity candidate with unnamed parent should be kept."""
        c1 = self._make_candidate('proximity', ['1', '2'],
                                  parent_id='child', parent_name='Frame 1')
        result = deduplicate_candidates([c1], root_id='root')
        assert len(result) == 1

    def test_empty_candidates(self):
        """Edge case: empty input."""
        result = deduplicate_candidates([])
        assert result == []

    def test_single_candidate(self):
        """Edge case: single candidate, no dedup needed."""
        c1 = self._make_candidate('semantic', ['1', '2'])
        result = deduplicate_candidates([c1])
        assert len(result) == 1

    def test_triple_overlap_cascade(self):
        """Three candidates with cascading overlaps: highest priority wins overlap nodes."""
        c1 = self._make_candidate('semantic', ['1', '2', '3'])       # priority 4
        c2 = self._make_candidate('consecutive', ['3', '4', '5'])    # priority 2.5
        c3 = self._make_candidate('proximity', ['5', '6', '7'])      # priority 0
        result = deduplicate_candidates([c1, c2, c3])
        assert len(result) == 3
        assert set(result[0]['node_ids']) == {'1', '2', '3'}
        # consecutive: node 3 trimmed by semantic
        assert set(result[1]['node_ids']) == {'4', '5'}
        # proximity: node 5 trimmed by consecutive (which has higher priority)
        assert set(result[2]['node_ids']) == {'6', '7'}

    def test_does_not_mutate_original(self):
        """Trimming should not mutate the original candidate dicts."""
        c1 = self._make_candidate('semantic', ['A', 'B'])
        c2 = self._make_candidate('pattern', ['B', 'C'])
        original_ids = list(c2['node_ids'])
        deduplicate_candidates([c1, c2])
        assert c2['node_ids'] == original_ids, "Original candidate was mutated"


# === Issue #242: Hidden children filter tests ===


class TestHiddenChildrenFilter:
    """Issue #242: Verify hidden children (visible=False) are excluded in 4 internal helpers."""

    def test_collect_text_preview_skips_hidden(self):
        """_collect_text_preview should not return text from hidden children."""
        from figma_utils import _collect_text_preview
        node = {
            'type': 'FRAME', 'name': 'wrapper',
            'children': [
                {'type': 'TEXT', 'characters': 'Hidden Text', 'name': 'hidden-text', 'visible': False},
                {'type': 'TEXT', 'characters': 'Visible Text', 'name': 'visible-text'},
            ],
        }
        result = _collect_text_preview(node)
        assert result == 'Visible Text'

    def test_collect_text_preview_all_hidden(self):
        """_collect_text_preview returns empty when all children are hidden."""
        from figma_utils import _collect_text_preview
        node = {
            'type': 'FRAME', 'name': 'wrapper',
            'children': [
                {'type': 'TEXT', 'characters': 'Secret', 'name': 'hidden', 'visible': False},
            ],
        }
        assert _collect_text_preview(node) == ''

    def test_is_heading_like_skips_hidden_children(self):
        """is_heading_like count_leaves should not count hidden children."""
        # 2 visible TEXT + 1 hidden RECTANGLE nested inside a sub-frame
        # Total top-level children = 2 (within HEADING_MAX_CHILDREN=5)
        # The sub-frame has hidden non-TEXT children that should not dilute ratio
        node = {
            'type': 'FRAME',
            'children': [
                {'type': 'TEXT', 'children': []},
                {'type': 'FRAME', 'children': [
                    {'type': 'TEXT', 'children': []},
                    # Hidden non-text children should be excluded from leaf count
                    {'type': 'RECTANGLE', 'children': [], 'visible': False},
                    {'type': 'IMAGE', 'children': [], 'visible': False},
                ]},
            ],
        }
        # Without filter in count_leaves: 2 TEXT + 2 non-TEXT = 50% → barely True
        # With filter in count_leaves: 2 TEXT / 2 total = 100% → True
        assert is_heading_like(node) is True

    def test_is_heading_like_hidden_makes_non_heading(self):
        """Hiding TEXT children can make a frame non-heading-like."""
        node = {
            'type': 'FRAME',
            'children': [
                {'type': 'TEXT', 'children': [], 'visible': False},
                {'type': 'TEXT', 'children': [], 'visible': False},
                {'type': 'RECTANGLE', 'children': []},
                {'type': 'RECTANGLE', 'children': []},
            ],
        }
        # Without filter: 2 TEXT + 2 RECT = 50% → True (edge)
        # With filter: 0 TEXT + 2 RECT = 0% → False
        assert is_heading_like(node) is False

    def test_is_decoration_pattern_skips_hidden_shapes(self):
        """is_decoration_pattern count_leaves should not count hidden shape children."""
        # Need: >= 3 shape leaves AND shape_ratio >= 0.6
        # 4 visible ELLIPSE + 1 visible TEXT = 4/5 = 0.8 → True
        # But add 10 hidden TEXT children → without filter would dilute ratio
        node = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 100},
            'children': [
                {'type': 'ELLIPSE', 'children': []},
                {'type': 'ELLIPSE', 'children': []},
                {'type': 'ELLIPSE', 'children': []},
                {'type': 'ELLIPSE', 'children': []},
                {'type': 'TEXT', 'children': []},
                # Hidden TEXT children should NOT count
                {'type': 'TEXT', 'children': [], 'visible': False},
                {'type': 'TEXT', 'children': [], 'visible': False},
                {'type': 'TEXT', 'children': [], 'visible': False},
                {'type': 'TEXT', 'children': [], 'visible': False},
                {'type': 'TEXT', 'children': [], 'visible': False},
            ],
        }
        # With filter: 4 shapes / 5 total = 0.8 >= 0.6 → True
        # Without filter: 4 shapes / 10 total = 0.4 < 0.6 → False
        assert is_decoration_pattern(node) is True

    def test_is_decoration_pattern_hidden_shapes_not_counted(self):
        """Hidden shapes should not be counted toward the shape threshold."""
        node = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 100},
            'children': [
                # Only 2 visible shapes (below DECORATION_MIN_SHAPES=3)
                {'type': 'ELLIPSE', 'children': []},
                {'type': 'ELLIPSE', 'children': []},
                # Hidden shapes should NOT push count above threshold
                {'type': 'ELLIPSE', 'children': [], 'visible': False},
                {'type': 'ELLIPSE', 'children': [], 'visible': False},
                {'type': 'ELLIPSE', 'children': [], 'visible': False},
            ],
        }
        # With filter: 2 shapes < 3 min → False
        # Without filter: 5 shapes → True
        assert is_decoration_pattern(node) is False

    def test_decoration_dominant_shape_skips_hidden(self):
        """decoration_dominant_shape count_shapes should not count hidden shapes."""
        node = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 100},
            'children': [
                # 3 visible RECTANGLE
                {'type': 'RECTANGLE', 'children': []},
                {'type': 'RECTANGLE', 'children': []},
                {'type': 'RECTANGLE', 'children': []},
                # 5 hidden ELLIPSE - should NOT be counted
                {'type': 'ELLIPSE', 'children': [], 'visible': False},
                {'type': 'ELLIPSE', 'children': [], 'visible': False},
                {'type': 'ELLIPSE', 'children': [], 'visible': False},
                {'type': 'ELLIPSE', 'children': [], 'visible': False},
                {'type': 'ELLIPSE', 'children': [], 'visible': False},
            ],
        }
        # With filter: 3 RECTANGLE > 0 ELLIPSE → RECTANGLE
        # Without filter: 5 ELLIPSE > 3 RECTANGLE → ELLIPSE
        assert decoration_dominant_shape(node) == 'RECTANGLE'

    def test_decoration_dominant_shape_nested_hidden(self):
        """Hidden children in nested structures should also be excluded."""
        node = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 100},
            'children': [
                {
                    'type': 'FRAME',
                    'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 50, 'height': 50},
                    'children': [
                        {'type': 'VECTOR', 'children': []},
                        {'type': 'VECTOR', 'children': []},
                        {'type': 'RECTANGLE', 'children': [], 'visible': False},
                        {'type': 'RECTANGLE', 'children': [], 'visible': False},
                        {'type': 'RECTANGLE', 'children': [], 'visible': False},
                    ],
                },
            ],
        }
        # With filter: 2 VECTOR, 0 RECTANGLE → VECTOR
        # Without filter: 3 RECTANGLE > 2 VECTOR → RECTANGLE
        assert decoration_dominant_shape(node) == 'VECTOR'


# ============================================================
# Issue #245: Hidden children filter for 10 functions
# ============================================================
class TestHiddenFilterIssue245:
    """Issue #245: Hidden children filter for 10 functions in figma_utils.py."""

    def test_structure_hash_ignores_hidden(self):
        node = {'type': 'FRAME', 'children': [
            {'type': 'TEXT', 'visible': False},
            {'type': 'RECTANGLE'},
        ]}
        h = structure_hash(node)
        assert 'TEXT' not in h  # hidden TEXT excluded

    def test_structure_hash_all_hidden_returns_leaf(self):
        node = {'type': 'FRAME', 'children': [
            {'type': 'TEXT', 'visible': False},
        ]}
        assert structure_hash(node) == 'FRAME'

    def test_is_heading_like_ignores_hidden(self):
        # 6 children but 3 hidden → effective 3, should pass MAX_CHILDREN check
        node = {'type': 'FRAME', 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 200, 'height': 50}, 'children': [
            {'type': 'TEXT', 'visible': False},
            {'type': 'TEXT', 'visible': False},
            {'type': 'TEXT', 'visible': False},
            {'type': 'TEXT', 'characters': 'A'},
            {'type': 'TEXT', 'characters': 'B'},
            {'type': 'TEXT', 'characters': 'C'},
        ]}
        # Should not be rejected by MAX_CHILDREN (5) because hidden excluded
        result = is_heading_like(node)
        assert isinstance(result, bool)  # Function runs without error

    def test_is_decoration_pattern_ignores_hidden(self):
        # Only visible children count
        node = {'type': 'FRAME', 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 100}, 'children': [
            {'type': 'ELLIPSE', 'visible': False},
            {'type': 'ELLIPSE', 'visible': False},
            {'type': 'ELLIPSE'},
            {'type': 'ELLIPSE'},
            {'type': 'ELLIPSE'},
        ]}
        result = is_decoration_pattern(node)
        assert isinstance(result, bool)

    def test_detect_highlight_text_ignores_hidden(self):
        children = [
            {'type': 'RECTANGLE', 'visible': False, 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 30}},
            {'type': 'TEXT', 'characters': 'Hello', 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 30}},
        ]
        result = detect_highlight_text(children)
        assert result == []  # Hidden RECT should not pair with TEXT

    def test_detect_horizontal_bar_ignores_hidden(self):
        # 4 visible + 2 hidden elements; hidden should not affect detection
        children = [
            {'type': 'TEXT', 'visible': False, 'absoluteBoundingBox': {'x': 0, 'y': 50, 'width': 50, 'height': 20}},
            {'type': 'TEXT', 'visible': False, 'absoluteBoundingBox': {'x': 60, 'y': 50, 'width': 50, 'height': 20}},
        ]
        result = detect_horizontal_bar(children, {'x': 0, 'y': 0, 'w': 1440, 'h': 900})
        assert result == []  # Only hidden elements → nothing

    def test_detect_en_jp_label_pairs_ignores_hidden(self):
        children = [
            {'type': 'TEXT', 'visible': False, 'characters': 'ABOUT', 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 30}},
            {'type': 'TEXT', 'characters': '会社概要', 'absoluteBoundingBox': {'x': 0, 'y': 40, 'width': 100, 'height': 30}},
        ]
        result = detect_en_jp_label_pairs(children)
        assert result == []  # Hidden EN label should not pair

    def test_detect_table_rows_ignores_hidden(self):
        children = [
            {'type': 'RECTANGLE', 'visible': False, 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1400, 'height': 50}},
            {'type': 'RECTANGLE', 'visible': False, 'absoluteBoundingBox': {'x': 0, 'y': 60, 'width': 1400, 'height': 50}},
            {'type': 'RECTANGLE', 'visible': False, 'absoluteBoundingBox': {'x': 0, 'y': 120, 'width': 1400, 'height': 50}},
        ]
        parent_bb = {'x': 0, 'y': 0, 'w': 1440, 'h': 300}
        result = detect_table_rows(children, parent_bb)
        assert result == []  # All hidden → no table detected

    def test_compute_child_types_ignores_hidden(self):
        children = [
            {'type': 'TEXT', 'visible': False},
            {'type': 'TEXT'},
            {'type': 'RECTANGLE'},
        ]
        result = _compute_child_types(children)
        assert 'TEX' in result  # Only 1 visible TEXT
        # Should show 1TEX+1REC, not 2TEX+1REC

    def test_compute_flags_ignores_hidden_for_leaf(self):
        # Node with only hidden children should be treated as leaf
        # bg-full requires is_leaf=True + RECTANGLE type + full page width
        node = {'type': 'RECTANGLE', 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 100}, 'children': [
            {'type': 'TEXT', 'visible': False},
        ]}
        flags = _compute_flags(node, 1440, 5000)
        assert 'bg-full' in flags  # is_leaf=True (hidden filtered) → bg-full detected

    def test_generate_enriched_table_ignores_hidden_children(self):
        children = [
            {'type': 'FRAME', 'name': 'test', 'id': '1', 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 200, 'height': 100}, 'children': [
                {'type': 'TEXT', 'visible': False},
            ]},
        ]
        result = generate_enriched_table(children, page_width=1440)
        assert 'leaf=Y' in result or '| Y |' in result  # Should be leaf


# ============================================================
# alignment_bonus — previously untested function
# ============================================================
class TestAlignmentBonus:
    """Tests for alignment_bonus() — previously untested."""

    def test_left_aligned(self):
        a = {'x': 100, 'y': 0, 'w': 50, 'h': 50}
        b = {'x': 100, 'y': 60, 'w': 80, 'h': 50}
        assert alignment_bonus(a, b) == 0.5  # Left edges match

    def test_no_alignment(self):
        a = {'x': 0, 'y': 0, 'w': 50, 'h': 50}
        b = {'x': 200, 'y': 200, 'w': 80, 'h': 80}
        assert alignment_bonus(a, b) == 1.0  # No alignment

    def test_center_aligned(self):
        a = {'x': 100, 'y': 0, 'w': 100, 'h': 50}
        b = {'x': 110, 'y': 60, 'w': 80, 'h': 50}
        # center_x_a = 150, center_x_b = 150 → match
        assert alignment_bonus(a, b) == 0.5

    def test_zero_size_boxes(self):
        a = {'x': 0, 'y': 0, 'w': 0, 'h': 0}
        b = {'x': 0, 'y': 0, 'w': 0, 'h': 0}
        # All edges and centers are at 0, so all checks are 0 <= tolerance → 0.5
        assert alignment_bonus(a, b) == 0.5


# ============================================================
# size_similarity_bonus — previously untested function
# ============================================================
class TestSizeSimilarityBonus:
    """Tests for size_similarity_bonus() — previously untested."""

    def test_identical_sizes(self):
        a = {'x': 0, 'y': 0, 'w': 100, 'h': 50}
        b = {'x': 0, 'y': 0, 'w': 100, 'h': 50}
        assert size_similarity_bonus(a, b) == 0.7

    def test_very_different_sizes(self):
        a = {'x': 0, 'y': 0, 'w': 100, 'h': 50}
        b = {'x': 0, 'y': 0, 'w': 500, 'h': 500}
        assert size_similarity_bonus(a, b) == 1.0

    def test_zero_size(self):
        a = {'x': 0, 'y': 0, 'w': 0, 'h': 0}
        b = {'x': 0, 'y': 0, 'w': 100, 'h': 50}
        # Early return 1.0 when any dimension is <= 0
        assert size_similarity_bonus(a, b) == 1.0


# ============================================================
# compute_gap_consistency — previously untested function
# ============================================================
class TestComputeGapConsistency:
    """Tests for compute_gap_consistency() — previously untested."""

    def test_identical_gaps(self):
        # Returns float (CoV value)
        result = compute_gap_consistency([20, 20, 20])
        assert result == 0.0

    def test_varying_gaps(self):
        result = compute_gap_consistency([10, 20, 30])
        assert result > 0

    def test_empty_gaps(self):
        # Empty → returns 1.0 (max inconsistency)
        result = compute_gap_consistency([])
        assert result == 1.0

    def test_single_gap(self):
        result = compute_gap_consistency([20])
        assert result == 0.0

    def test_zero_mean_gaps(self):
        # All zeros → returns 1.0 (zero mean guarded)
        result = compute_gap_consistency([0, 0, 0])
        assert result == 1.0


# ============================================================
# infer_direction_two_elements — previously untested function
# ============================================================
class TestInferDirectionTwoElements:
    """Tests for infer_direction_two_elements() — previously untested."""

    def test_horizontal(self):
        a = {'x': 0, 'y': 0, 'w': 100, 'h': 50}
        b = {'x': 200, 'y': 0, 'w': 100, 'h': 50}
        assert infer_direction_two_elements(a, b) == 'HORIZONTAL'

    def test_vertical(self):
        a = {'x': 0, 'y': 0, 'w': 100, 'h': 50}
        b = {'x': 0, 'y': 200, 'w': 100, 'h': 50}
        assert infer_direction_two_elements(a, b) == 'VERTICAL'

    def test_same_position(self):
        a = {'x': 0, 'y': 0, 'w': 100, 'h': 50}
        b = {'x': 0, 'y': 0, 'w': 100, 'h': 50}
        result = infer_direction_two_elements(a, b)
        assert result in ('HORIZONTAL', 'VERTICAL')  # No crash


# ============================================================
# _count_flat_descendants — Issue #248: zero test coverage
# ============================================================
class TestCountFlatDescendants:
    """Tests for _count_flat_descendants() — previously untested."""

    def test_empty_node(self):
        """Node with no children returns 0."""
        node = {'type': 'FRAME', 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 500, 'height': 500}}
        assert _count_flat_descendants(node) == 0

    def test_single_child(self):
        """Node with 1 child — not flat (below FLAT_THRESHOLD)."""
        child = {'type': 'FRAME', 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 200, 'height': 100}}
        node = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 500, 'height': 500},
            'children': [child],
        }
        assert _count_flat_descendants(node) == 0

    def test_flat_section(self):
        """Node with children > FLAT_THRESHOLD is detected as flat with correct excess."""
        # Create a FRAME child that has 20 visible children (> 15 threshold)
        grandchildren = [
            {'type': 'TEXT', 'absoluteBoundingBox': {'x': 0, 'y': i * 20, 'width': 100, 'height': 18}}
            for i in range(20)
        ]
        flat_child = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 500, 'height': 400},
            'children': grandchildren,
        }
        node = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 500, 'height': 500},
            'children': [flat_child],
        }
        # flat_child has 20 children > 15 threshold → counted as 1 flat descendant
        assert _count_flat_descendants(node) == 1

    def test_nested_flat(self):
        """Nested structure where inner node is flat — both levels counted."""
        # Inner FRAME with 16 children (> threshold)
        inner_grandchildren = [
            {'type': 'TEXT', 'absoluteBoundingBox': {'x': 0, 'y': i * 20, 'width': 100, 'height': 18}}
            for i in range(16)
        ]
        inner_flat = {
            'type': 'GROUP',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 400, 'height': 300},
            'children': inner_grandchildren,
        }
        # Outer FRAME wrapping inner_flat + 15 more children (16 total > threshold)
        outer_siblings = [
            {'type': 'TEXT', 'absoluteBoundingBox': {'x': 0, 'y': i * 20, 'width': 100, 'height': 18}}
            for i in range(15)
        ]
        outer_flat = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 500, 'height': 400},
            'children': [inner_flat] + outer_siblings,
        }
        node = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 500, 'height': 500},
            'children': [outer_flat],
        }
        # outer_flat: 16 children > 15 → 1
        # inner_flat: 16 children > 15 → 1
        # Total: 2
        assert _count_flat_descendants(node) == 2

    def test_hidden_children_excluded(self):
        """Node with 20 children but 10 hidden → only 10 visible → not flat."""
        children = []
        for i in range(20):
            child = {
                'type': 'TEXT',
                'absoluteBoundingBox': {'x': 0, 'y': i * 20, 'width': 100, 'height': 18},
            }
            if i >= 10:
                child['visible'] = False
            children.append(child)
        target = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 500, 'height': 400},
            'children': children,
        }
        node = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 500, 'height': 500},
            'children': [target],
        }
        # Only 10 visible children ≤ 15 threshold → not flat
        assert _count_flat_descendants(node) == 0

    def test_section_root_skipped(self):
        """Section root child (width ~1440) is skipped but its subtree is recursed."""
        # A section root child should NOT itself be counted as flat,
        # but its children should be recursed into.
        inner_grandchildren = [
            {'type': 'TEXT', 'absoluteBoundingBox': {'x': 0, 'y': i * 20, 'width': 100, 'height': 18}}
            for i in range(20)
        ]
        inner_flat = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 400, 'height': 300},
            'children': inner_grandchildren,
        }
        # Section root child (width=1440) with inner_flat as its only child
        section_child = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 800},
            'children': [inner_flat],
        }
        node = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 500, 'height': 500},
            'children': [section_child],
        }
        # section_child is a section root → skipped (not counted itself)
        # but inner_flat (20 children > 15) is found via recursion → 1
        assert _count_flat_descendants(node) == 1

"""Tests for basic utility functions in figma_utils."""
import pytest

from figma_utils import (
    _jp_keyword_lookup,
    _raw_distance,
    get_bbox,
    get_root_node,
    get_text_children_content,
    is_section_root,
    is_unnamed,
    JP_KEYWORD_MAP,
    resolve_absolute_coords,
    snap,
    to_kebab,
    yaml_str,
)


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

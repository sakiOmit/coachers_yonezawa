"""Tests for enriched table pattern detection: TestDetectHorizontalBar, TestComputeZoneBboxes, TestDetectBgContentLayersEllipseDecoration, TestDetectRepeatingTupleSingleDistinct."""
import pytest

from figma_utils import (
    _collect_text_preview,
    _compute_child_types,
    _compute_flags,
    _compute_zone_bboxes,
    detect_bg_content_layers,
    detect_horizontal_bar,
    detect_repeating_tuple,
    generate_enriched_table,
    HORIZONTAL_BAR_MAX_HEIGHT,
    HORIZONTAL_BAR_MIN_ELEMENTS,
    HORIZONTAL_BAR_VARIANCE_RATIO,
    TUPLE_PATTERN_MIN,
    resolve_absolute_coords,
)


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

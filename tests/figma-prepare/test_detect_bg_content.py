"""Tests for detect_bg_content_layers (Issue 180)."""
import pytest

from figma_utils import (
    BG_DECORATION_MAX_AREA_RATIO,
    BG_MIN_HEIGHT_RATIO,
    BG_WIDTH_RATIO,
    OVERFLOW_BG_MIN_WIDTH,
    detect_bg_content_layers,
)


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

    def test_hidden_children_filtered(self):
        """Hidden children should be excluded from bg-content detection (Issue #264)."""
        parent_bb = {'x': 0, 'y': 0, 'w': 1440, 'h': 800}
        children = [
            # bg RECTANGLE (visible)
            {"id": "bg1", "type": "RECTANGLE", "name": "Rectangle 1",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 400}},
            # Hidden RECTANGLE that would be a second bg candidate if not filtered
            {"id": "bg2", "type": "RECTANGLE", "name": "Rectangle 2",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 400},
             "visible": False},
            # Content elements
            {"id": "c1", "type": "TEXT", "name": "text1",
             "absoluteBoundingBox": {"x": 100, "y": 100, "width": 400, "height": 60}},
            {"id": "c2", "type": "GROUP", "name": "content",
             "absoluteBoundingBox": {"x": 100, "y": 200, "width": 400, "height": 60},
             "children": [{"type": "TEXT", "children": []}]},
        ]
        result = detect_bg_content_layers(children, parent_bb)
        # Without hidden filter, 2 bg RECTANGLEs would cause empty result (ambiguous).
        # With hidden filter, only 1 visible bg RECTANGLE -> detection succeeds.
        assert len(result) == 1
        assert 'bg1' in result[0]['bg_node_ids']
        assert set(result[0]['node_ids']) == {'c1', 'c2'}

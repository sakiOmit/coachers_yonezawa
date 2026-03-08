"""Tests for semantic detection: bg layers, tables, tuples, decorations, highlights."""
import pytest

from figma_utils import (
    BG_DECORATION_MAX_AREA_RATIO,
    BG_MIN_HEIGHT_RATIO,
    BG_WIDTH_RATIO,
    DECORATION_MAX_SIZE,
    DECORATION_MIN_SHAPES,
    DECORATION_SHAPE_RATIO,
    HIGHLIGHT_HEIGHT_RATIO_MAX,
    HIGHLIGHT_HEIGHT_RATIO_MIN,
    HIGHLIGHT_OVERLAP_RATIO,
    HIGHLIGHT_TEXT_MAX_LEN,
    OVERFLOW_BG_MIN_WIDTH,
    TABLE_DIVIDER_MAX_HEIGHT,
    TABLE_MIN_ROWS,
    TABLE_ROW_WIDTH_RATIO,
    TUPLE_MAX_SIZE,
    TUPLE_PATTERN_MIN,
    decoration_dominant_shape,
    detect_bg_content_layers,
    detect_highlight_text,
    detect_repeating_tuple,
    detect_table_rows,
    is_decoration_pattern,
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

    def test_hidden_children_filtered(self):
        """Hidden children should be excluded from tuple detection (Issue #264)."""
        children = []
        for i in range(3):
            children.append(self._make_node("RECTANGLE", f"img-{i}"))
            children.append(self._make_node("FRAME", f"text-{i}"))
            children.append(self._make_node("INSTANCE", f"arrow-{i}"))
        # Insert hidden elements that would break the pattern if not filtered
        children.insert(3, {"type": "VECTOR", "name": "hidden-el", "id": "hidden-1", "visible": False})
        children.insert(7, {"type": "TEXT", "name": "hidden-el-2", "id": "hidden-2", "visible": False})
        result = detect_repeating_tuple(children)
        # Hidden elements should be filtered out; pattern should still be detected
        assert len(result) == 1
        assert result[0]['tuple_size'] == 3
        assert result[0]['count'] == 3


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



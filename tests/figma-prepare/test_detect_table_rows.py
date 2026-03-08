"""Tests for detect_table_rows (Issue 181)."""
import pytest

from figma_utils import (
    TABLE_DIVIDER_MAX_HEIGHT,
    TABLE_MIN_ROWS,
    TABLE_ROW_WIDTH_RATIO,
    detect_table_rows,
)


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

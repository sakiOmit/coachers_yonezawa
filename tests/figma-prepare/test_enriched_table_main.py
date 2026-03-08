"""Tests for enriched table generation: TestGenerateEnrichedTable (core table generation)."""
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
        assert '| # | ID | Name | Type | X | Y | Col | W x H | Leaf? | ChildTypes | Flags | Text |' in lines[0]
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
        flags_col = cols[11]  # 11th column (0-indexed, accounting for leading empty + Col column)
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

    def test_col_dash_when_all_same_x(self):
        """All elements at same X position → x_span=0 → Col='-' for all (Issue 261)."""
        children = [
            self._make_node('1:1', 'FRAME', 'item-a', 100, 0, 200, 100),
            self._make_node('1:2', 'FRAME', 'item-b', 100, 120, 200, 100),
            self._make_node('1:3', 'FRAME', 'item-c', 100, 240, 200, 100),
        ]
        result = generate_enriched_table(children, page_width=1440)
        lines = result.strip().split('\n')
        # All 3 data rows should have Col='-'
        for line in lines[2:]:
            cols = [c.strip() for c in line.split('|')]
            col_val = cols[7]  # Col column
            assert col_val == '-', f"Expected Col='-' but got '{col_val}' in: {line}"

    def test_col_left_right_assignment(self):
        """Two elements clearly separated left and right get Col='L' and Col='R' (Issue 271)."""
        children = [
            self._make_node('1:1', 'FRAME', 'left-panel', 0, 0, 300, 400),
            self._make_node('1:2', 'FRAME', 'right-panel', 800, 0, 300, 400),
        ]
        result = generate_enriched_table(children, page_width=1440)
        lines = result.strip().split('\n')
        cols_row1 = [c.strip() for c in lines[2].split('|')]
        cols_row2 = [c.strip() for c in lines[3].split('|')]
        assert cols_row1[7] == 'L', f"Expected Col='L' for left element, got '{cols_row1[7]}'"
        assert cols_row2[7] == 'R', f"Expected Col='R' for right element, got '{cols_row2[7]}'"

    def test_col_full_width(self):
        """A wide element spanning both columns gets Col='F' (Issue 271)."""
        children = [
            self._make_node('1:1', 'FRAME', 'left-panel', 0, 0, 300, 400),
            self._make_node('1:2', 'RECTANGLE', 'divider', 0, 400, 1400, 2),
            self._make_node('1:3', 'FRAME', 'right-panel', 800, 420, 300, 400),
        ]
        result = generate_enriched_table(children, page_width=1440)
        lines = result.strip().split('\n')
        cols_row1 = [c.strip() for c in lines[2].split('|')]
        cols_row2 = [c.strip() for c in lines[3].split('|')]
        cols_row3 = [c.strip() for c in lines[4].split('|')]
        assert cols_row1[7] == 'L', f"Expected Col='L' for left element, got '{cols_row1[7]}'"
        assert cols_row2[7] == 'F', f"Expected Col='F' for full-width divider, got '{cols_row2[7]}'"
        assert cols_row3[7] == 'R', f"Expected Col='R' for right element, got '{cols_row3[7]}'"

    def test_col_center(self):
        """An element spanning mid-region gets Col='C' when not full-width (Issue 271)."""
        children = [
            self._make_node('1:1', 'FRAME', 'left-col', 0, 0, 200, 400),
            self._make_node('1:2', 'FRAME', 'center-block', 400, 0, 400, 300),
            self._make_node('1:3', 'FRAME', 'right-col', 1000, 0, 200, 400),
        ]
        result = generate_enriched_table(children, page_width=1440)
        lines = result.strip().split('\n')
        cols_row1 = [c.strip() for c in lines[2].split('|')]
        cols_row2 = [c.strip() for c in lines[3].split('|')]
        cols_row3 = [c.strip() for c in lines[4].split('|')]
        assert cols_row1[7] == 'L', f"Expected Col='L' for left element, got '{cols_row1[7]}'"
        assert cols_row2[7] == 'C', f"Expected Col='C' for center element, got '{cols_row2[7]}'"
        assert cols_row3[7] == 'R', f"Expected Col='R' for right element, got '{cols_row3[7]}'"

    def test_col_single_element_no_columns(self):
        """A single element always gets Col='-' since 2+ elements needed for column detection (Issue 271)."""
        children = [
            self._make_node('1:1', 'FRAME', 'only-element', 0, 0, 1400, 600),
        ]
        result = generate_enriched_table(children, page_width=1440)
        lines = result.strip().split('\n')
        cols_row = [c.strip() for c in lines[2].split('|')]
        assert cols_row[7] == '-', f"Expected Col='-' for single element, got '{cols_row[7]}'"

    def test_flag_overflow_y(self):
        """Element extending beyond page height gets overflow-y flag (Issue 271)."""
        children = [
            self._make_node('1:1', 'FRAME', 'tall-section', 0, 4800, 1440, 400,
                            children=[self._make_node('1:2', 'TEXT', 't', 0, 0, 100, 20)]),
        ]
        result = generate_enriched_table(children, page_width=1440, page_height=5000)
        lines = result.strip().split('\n')
        cols = [c.strip() for c in lines[2].split('|')]
        flags_val = cols[11]
        assert 'overflow-y' in flags_val, f"Expected 'overflow-y' in flags, got '{flags_val}'"

    def test_flag_bg_wide_not_full(self):
        """RECTANGLE at 85% width gets bg-wide but not bg-full (Issue 271)."""
        children = [
            self._make_node('1:1', 'RECTANGLE', 'bg-rect', 0, 0, 1224, 500),
        ]
        result = generate_enriched_table(children, page_width=1440)
        lines = result.strip().split('\n')
        cols = [c.strip() for c in lines[2].split('|')]
        flags_val = cols[11]
        assert 'bg-wide' in flags_val, f"Expected 'bg-wide' in flags, got '{flags_val}'"
        assert 'bg-full' not in flags_val, f"'bg-full' should not appear for 85% width, got '{flags_val}'"

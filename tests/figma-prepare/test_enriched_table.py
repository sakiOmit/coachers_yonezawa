"""Tests for enriched table generation, flags, horizontal bar, and zone bboxes."""
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

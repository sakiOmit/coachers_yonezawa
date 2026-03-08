"""Comprehensive tests for figma_utils.autolayout module.

Covers all 10 public/private functions:
  - _direction_hint_from_name
  - _infer_direction_by_grid
  - _infer_direction
  - _infer_gap
  - _infer_padding
  - _infer_alignment
  - infer_layout
  - layout_from_enrichment
  - walk_and_infer
  - run_autolayout_inference
"""

import json
import os
import tempfile

import pytest

from figma_utils.autolayout import (
    _direction_hint_from_name,
    _infer_direction,
    _infer_direction_by_grid,
    _infer_alignment,
    _infer_gap,
    _infer_padding,
    infer_layout,
    layout_from_enrichment,
    walk_and_infer,
    run_autolayout_inference,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bb(x, y, w, h):
    """Shorthand to create a bounding box dict."""
    return {'x': x, 'y': y, 'w': w, 'h': h}


def _node(name='Frame', ntype='FRAME', x=0, y=0, w=100, h=100, children=None, visible=True, **extra):
    """Create a minimal Figma node dict for testing."""
    node = {
        'name': name,
        'type': ntype,
        'absoluteBoundingBox': {'x': x, 'y': y, 'width': w, 'height': h},
        'children': children or [],
    }
    if not visible:
        node['visible'] = False
    node.update(extra)
    return node


# ===========================================================================
# _direction_hint_from_name
# ===========================================================================

class TestDirectionHintFromName:
    """Tests for name-based direction hint inference."""

    # --- Normal cases ---

    def test_nav_returns_horizontal(self):
        d, c = _direction_hint_from_name('nav-main')
        assert d == 'HORIZONTAL'
        assert c == 0.7

    def test_sidebar_returns_vertical(self):
        d, c = _direction_hint_from_name('sidebar-left')
        assert d == 'VERTICAL'
        assert c == 0.7

    def test_card_list_returns_wrap(self):
        d, c = _direction_hint_from_name('card-list-features')
        assert d == 'WRAP'
        assert c == 0.7

    def test_grid_returns_wrap(self):
        d, c = _direction_hint_from_name('photo-grid')
        assert d == 'WRAP'
        assert c == 0.7

    def test_breadcrumb_horizontal(self):
        d, c = _direction_hint_from_name('breadcrumb-path')
        assert d == 'HORIZONTAL'
        assert c == 0.7

    def test_toolbar_horizontal(self):
        d, c = _direction_hint_from_name('toolbar-actions')
        assert d == 'HORIZONTAL'
        assert c == 0.7

    def test_menu_vertical(self):
        d, c = _direction_hint_from_name('menu-side')
        assert d == 'VERTICAL'
        assert c == 0.7

    def test_footer_links_vertical(self):
        d, c = _direction_hint_from_name('footer-links')
        assert d == 'VERTICAL'
        assert c == 0.7

    # --- Suffix patterns ---

    def test_suffix_list(self):
        d, c = _direction_hint_from_name('feature-list')
        assert d == 'HORIZONTAL'
        assert c == 0.6

    def test_suffix_items(self):
        d, c = _direction_hint_from_name('benefit-items')
        assert d == 'HORIZONTAL'
        assert c == 0.6

    # --- Two-column prefix ---

    def test_two_column_prefix(self):
        d, c = _direction_hint_from_name('two-column-layout')
        assert d == 'HORIZONTAL'
        assert c == 0.8

    def test_2col_prefix(self):
        d, c = _direction_hint_from_name('2col-content')
        assert d == 'HORIZONTAL'
        assert c == 0.8

    # --- Case insensitivity ---

    def test_case_insensitive(self):
        d, c = _direction_hint_from_name('NAV-MAIN')
        assert d == 'HORIZONTAL'
        assert c == 0.7

    # --- Edge cases ---

    def test_empty_string(self):
        d, c = _direction_hint_from_name('')
        assert d is None
        assert c == 0

    def test_none_input(self):
        d, c = _direction_hint_from_name(None)
        assert d is None
        assert c == 0

    def test_generic_frame_name(self):
        d, c = _direction_hint_from_name('Frame 123')
        assert d is None
        assert c == 0

    def test_no_match(self):
        d, c = _direction_hint_from_name('hero-section')
        assert d is None
        assert c == 0


# ===========================================================================
# _infer_direction_by_grid
# ===========================================================================

class TestInferDirectionByGrid:
    """Tests for row/column counting fallback direction inference."""

    def test_single_row_horizontal(self):
        bbs = [_bb(0, 0, 50, 50), _bb(80, 0, 50, 50), _bb(160, 0, 50, 50)]
        assert _infer_direction_by_grid(bbs) == 'HORIZONTAL'

    def test_single_column_vertical(self):
        bbs = [_bb(0, 0, 50, 50), _bb(0, 80, 50, 50), _bb(0, 160, 50, 50)]
        assert _infer_direction_by_grid(bbs) == 'VERTICAL'

    def test_equal_rows_cols_defaults_horizontal(self):
        """2x2 grid: equal rows and cols => default HORIZONTAL."""
        bbs = [_bb(0, 0, 50, 50), _bb(100, 0, 50, 50),
               _bb(0, 100, 50, 50), _bb(100, 100, 50, 50)]
        assert _infer_direction_by_grid(bbs) == 'HORIZONTAL'

    def test_more_cols_than_rows(self):
        """3 cols x 2 rows => HORIZONTAL (fewer rows)."""
        bbs = [_bb(0, 0, 40, 40), _bb(60, 0, 40, 40), _bb(120, 0, 40, 40),
               _bb(0, 60, 40, 40), _bb(60, 60, 40, 40), _bb(120, 60, 40, 40)]
        assert _infer_direction_by_grid(bbs) == 'HORIZONTAL'

    def test_more_rows_than_cols(self):
        """2 cols x 3 rows => VERTICAL (fewer cols)."""
        bbs = [_bb(0, 0, 40, 40), _bb(60, 0, 40, 40),
               _bb(0, 60, 40, 40), _bb(60, 60, 40, 40),
               _bb(0, 120, 40, 40), _bb(60, 120, 40, 40)]
        assert _infer_direction_by_grid(bbs) == 'VERTICAL'

    # --- Edge cases ---

    def test_all_same_x_same_y(self):
        """All at identical position: 1 row, 1 col => HORIZONTAL (default)."""
        bbs = [_bb(0, 0, 50, 50), _bb(0, 0, 50, 50)]
        assert _infer_direction_by_grid(bbs) == 'HORIZONTAL'

    def test_elements_within_tolerance(self):
        """Elements within ROW_TOLERANCE (20px) count as same row/col."""
        # All Y within 15px => 1 row, but X spread => multiple cols => HORIZONTAL
        bbs = [_bb(0, 0, 40, 40), _bb(100, 10, 40, 40), _bb(200, 5, 40, 40)]
        assert _infer_direction_by_grid(bbs) == 'HORIZONTAL'


# ===========================================================================
# _infer_direction
# ===========================================================================

class TestInferDirection:
    """Tests for the main direction inference combining all stages."""

    def test_two_elements_horizontal(self):
        bbs = [_bb(0, 0, 100, 100), _bb(200, 0, 100, 100)]
        result = _infer_direction(bbs)
        assert result is not None
        direction, is_wrap = result
        assert direction == 'HORIZONTAL'
        assert is_wrap is False

    def test_two_elements_vertical(self):
        bbs = [_bb(0, 0, 100, 100), _bb(0, 200, 100, 100)]
        result = _infer_direction(bbs)
        assert result is not None
        direction, _ = result
        assert direction == 'VERTICAL'

    def test_clear_horizontal_variance(self):
        """x_var >> y_var * VARIANCE_RATIO => HORIZONTAL (Stage 1)."""
        bbs = [_bb(0, 0, 50, 50), _bb(200, 5, 50, 50), _bb(400, 0, 50, 50)]
        result = _infer_direction(bbs)
        assert result is not None
        direction, _ = result
        assert direction == 'HORIZONTAL'

    def test_clear_vertical_variance(self):
        """y_var >> x_var * VARIANCE_RATIO => VERTICAL (Stage 1)."""
        bbs = [_bb(0, 0, 50, 50), _bb(5, 200, 50, 50), _bb(0, 400, 50, 50)]
        result = _infer_direction(bbs)
        assert result is not None
        direction, _ = result
        assert direction == 'VERTICAL'

    def test_ambiguous_with_name_hint(self):
        """Ambiguous variance but name hint present (Stage 1.5)."""
        # Near-equal x_var and y_var
        bbs = [_bb(0, 0, 50, 50), _bb(100, 100, 50, 50), _bb(200, 200, 50, 50)]
        result = _infer_direction(bbs, frame_name='sidebar-content')
        assert result is not None
        direction, _ = result
        assert direction == 'VERTICAL'

    def test_all_same_position_returns_none(self):
        bbs = [_bb(50, 50, 100, 100), _bb(50, 50, 100, 100), _bb(50, 50, 100, 100)]
        assert _infer_direction(bbs) is None

    def test_wrap_detection(self):
        """4+ HORIZONTAL elements in 2+ rows => WRAP."""
        bbs = [_bb(0, 0, 80, 80), _bb(100, 0, 80, 80),
               _bb(0, 100, 80, 80), _bb(100, 100, 80, 80)]
        result = _infer_direction(bbs)
        assert result is not None
        direction, is_wrap = result
        assert direction == 'WRAP'
        assert is_wrap is True

    # --- Edge case: negative coords ---

    def test_negative_coords_horizontal(self):
        bbs = [_bb(-200, 0, 50, 50), _bb(0, 0, 50, 50), _bb(200, 0, 50, 50)]
        result = _infer_direction(bbs)
        assert result is not None
        direction, _ = result
        assert direction == 'HORIZONTAL'


# ===========================================================================
# _infer_gap
# ===========================================================================

class TestInferGap:
    """Tests for gap inference between children."""

    def test_uniform_horizontal_gap(self):
        bbs = [_bb(0, 0, 100, 50), _bb(120, 0, 100, 50), _bb(240, 0, 100, 50)]
        gap, cov = _infer_gap(bbs, 'HORIZONTAL', False)
        assert gap == 20  # 120-100=20, snapped to 20 (multiple of 4)
        assert cov == 0.0  # uniform gaps

    def test_uniform_vertical_gap(self):
        bbs = [_bb(0, 0, 100, 50), _bb(0, 66, 100, 50), _bb(0, 132, 100, 50)]
        gap, cov = _infer_gap(bbs, 'VERTICAL', False)
        assert gap == 16  # median(16, 16) snapped to 16
        assert cov == 0.0

    def test_non_uniform_gap(self):
        bbs = [_bb(0, 0, 100, 50), _bb(120, 0, 100, 50), _bb(260, 0, 100, 50)]
        gap, cov = _infer_gap(bbs, 'HORIZONTAL', False)
        # gaps: [20, 40], median = 30 → snap(30) = 32
        assert gap == 32
        assert cov > 0  # non-uniform

    def test_wrap_gap_per_row(self):
        """WRAP mode: compute gap within each row."""
        bbs = [_bb(0, 0, 80, 80), _bb(100, 0, 80, 80),
               _bb(0, 100, 80, 80), _bb(100, 100, 80, 80)]
        gap, cov = _infer_gap(bbs, 'HORIZONTAL', True)
        assert gap == 20  # 100-80=20 per row, uniform

    def test_overlapping_elements_gap_zero(self):
        """Overlapping elements: negative gap clamped to 0."""
        bbs = [_bb(0, 0, 100, 50), _bb(80, 0, 100, 50)]
        gap, cov = _infer_gap(bbs, 'HORIZONTAL', False)
        assert gap == 0

    # --- Edge case: single gap ---

    def test_two_children_single_gap(self):
        bbs = [_bb(0, 0, 100, 50), _bb(124, 0, 100, 50)]
        gap, cov = _infer_gap(bbs, 'HORIZONTAL', False)
        assert gap == 24  # 124-100=24, snap(24)=24
        assert cov == 0.0  # single gap


# ===========================================================================
# _infer_padding
# ===========================================================================

class TestInferPadding:
    """Tests for padding inference."""

    def test_even_padding(self):
        frame_bb = _bb(0, 0, 400, 200)
        child_bbs = [_bb(20, 20, 160, 160), _bb(200, 20, 180, 160)]
        p = _infer_padding(frame_bb, child_bbs)
        assert p['top'] == 20
        assert p['left'] == 20
        assert p['bottom'] == 20
        assert p['right'] == 20

    def test_asymmetric_padding(self):
        frame_bb = _bb(0, 0, 500, 300)
        child_bbs = [_bb(40, 20, 420, 260)]
        p = _infer_padding(frame_bb, child_bbs)
        assert p['top'] == 20
        assert p['left'] == 40
        assert p['bottom'] == 20
        assert p['right'] == 40

    def test_snap_to_grid(self):
        """Padding snaps to 4px grid."""
        frame_bb = _bb(0, 0, 400, 200)
        child_bbs = [_bb(13, 7, 370, 180)]
        p = _infer_padding(frame_bb, child_bbs)
        # 13 → snap(13) = 12, 7 → snap(7) = 8
        assert p['left'] == 12
        assert p['top'] == 8

    def test_zero_padding(self):
        frame_bb = _bb(0, 0, 200, 100)
        child_bbs = [_bb(0, 0, 200, 100)]
        p = _infer_padding(frame_bb, child_bbs)
        assert p == {'top': 0, 'right': 0, 'bottom': 0, 'left': 0}

    # --- Edge case: children outside frame (negative padding clamped to 0) ---

    def test_children_outside_frame(self):
        frame_bb = _bb(100, 100, 200, 200)
        child_bbs = [_bb(50, 50, 300, 300)]
        p = _infer_padding(frame_bb, child_bbs)
        assert p['top'] == 0
        assert p['left'] == 0
        assert p['bottom'] == 0
        assert p['right'] == 0


# ===========================================================================
# _infer_alignment
# ===========================================================================

class TestInferAlignment:
    """Tests for alignment inference."""

    def test_horizontal_center_aligned(self):
        """All children have same Y center => CENTER counter-axis."""
        bbs = [_bb(0, 10, 100, 80), _bb(120, 10, 100, 80), _bb(240, 10, 100, 80)]
        frame_bb = _bb(0, 0, 400, 100)
        primary, counter = _infer_alignment(bbs, 'HORIZONTAL', frame_bb)
        assert counter == 'CENTER'

    def test_horizontal_top_aligned(self):
        """All children share same top Y => MIN counter-axis."""
        bbs = [_bb(0, 0, 100, 50), _bb(120, 0, 100, 80), _bb(240, 0, 100, 60)]
        frame_bb = _bb(0, 0, 400, 100)
        primary, counter = _infer_alignment(bbs, 'HORIZONTAL', frame_bb)
        assert counter == 'MIN'

    def test_horizontal_bottom_aligned(self):
        """All children share same bottom Y => MAX counter-axis."""
        bbs = [_bb(0, 50, 100, 50), _bb(120, 20, 100, 80), _bb(240, 40, 100, 60)]
        frame_bb = _bb(0, 0, 400, 100)
        primary, counter = _infer_alignment(bbs, 'HORIZONTAL', frame_bb)
        assert counter == 'MAX'

    def test_vertical_center_aligned(self):
        bbs = [_bb(10, 0, 80, 50), _bb(10, 60, 80, 50), _bb(10, 120, 80, 50)]
        frame_bb = _bb(0, 0, 100, 200)
        primary, counter = _infer_alignment(bbs, 'VERTICAL', frame_bb)
        assert counter == 'CENTER'

    def test_vertical_left_aligned(self):
        """All children share same left X => MIN counter-axis."""
        bbs = [_bb(0, 0, 50, 50), _bb(0, 60, 80, 50), _bb(0, 120, 60, 50)]
        frame_bb = _bb(0, 0, 100, 200)
        primary, counter = _infer_alignment(bbs, 'VERTICAL', frame_bb)
        assert counter == 'MIN'

    def test_vertical_right_aligned(self):
        """All children share same right X => MAX counter-axis."""
        bbs = [_bb(50, 0, 50, 50), _bb(20, 60, 80, 50), _bb(40, 120, 60, 50)]
        frame_bb = _bb(0, 0, 100, 200)
        primary, counter = _infer_alignment(bbs, 'VERTICAL', frame_bb)
        assert counter == 'MAX'

    def test_space_between_primary(self):
        """First child at start edge, last at end edge => SPACE_BETWEEN."""
        bbs = [_bb(0, 0, 50, 50), _bb(150, 0, 50, 50)]
        frame_bb = _bb(0, 0, 200, 50)
        primary, counter = _infer_alignment(bbs, 'HORIZONTAL', frame_bb)
        assert primary == 'SPACE_BETWEEN'

    def test_min_primary(self):
        """Children don't touch both edges => MIN."""
        bbs = [_bb(20, 0, 50, 50), _bb(100, 0, 50, 50)]
        frame_bb = _bb(0, 0, 300, 50)
        primary, counter = _infer_alignment(bbs, 'HORIZONTAL', frame_bb)
        assert primary == 'MIN'


# ===========================================================================
# infer_layout
# ===========================================================================

class TestInferLayout:
    """Tests for the main infer_layout function."""

    def test_basic_horizontal_layout(self):
        frame = _node('row', 'FRAME', 0, 0, 400, 100, children=[
            _node('a', 'FRAME', 20, 20, 100, 60),
            _node('b', 'FRAME', 140, 20, 100, 60),
            _node('c', 'FRAME', 260, 20, 100, 60),
        ])
        result = infer_layout(frame)
        assert result is not None
        assert result['direction'] == 'HORIZONTAL'
        assert isinstance(result['gap'], int)
        assert 'padding' in result
        assert result['confidence'] in ('high', 'medium', 'low')

    def test_basic_vertical_layout(self):
        frame = _node('col', 'FRAME', 0, 0, 200, 400, children=[
            _node('a', 'FRAME', 20, 20, 160, 80),
            _node('b', 'FRAME', 20, 120, 160, 80),
            _node('c', 'FRAME', 20, 220, 160, 80),
        ])
        result = infer_layout(frame)
        assert result is not None
        assert result['direction'] == 'VERTICAL'

    def test_two_children_medium_confidence(self):
        frame = _node('pair', 'FRAME', 0, 0, 400, 100, children=[
            _node('a', 'FRAME', 20, 20, 150, 60),
            _node('b', 'FRAME', 200, 20, 150, 60),
        ])
        result = infer_layout(frame)
        assert result is not None
        assert result['confidence'] == 'medium'

    # --- Edge cases ---

    def test_zero_children_returns_none(self):
        frame = _node('empty', 'FRAME', 0, 0, 400, 100, children=[])
        assert infer_layout(frame) is None

    def test_one_child_returns_none(self):
        frame = _node('single', 'FRAME', 0, 0, 400, 100, children=[
            _node('only', 'FRAME', 20, 20, 100, 60),
        ])
        assert infer_layout(frame) is None

    def test_zero_dimension_frame_returns_none(self):
        frame = _node('zero-w', 'FRAME', 0, 0, 0, 100, children=[
            _node('a', 'FRAME', 0, 0, 50, 50),
            _node('b', 'FRAME', 60, 0, 50, 50),
        ])
        assert infer_layout(frame) is None

    def test_zero_height_frame_returns_none(self):
        frame = _node('zero-h', 'FRAME', 0, 0, 400, 0, children=[
            _node('a', 'FRAME', 0, 0, 50, 50),
            _node('b', 'FRAME', 60, 0, 50, 50),
        ])
        assert infer_layout(frame) is None

    def test_hidden_children_filtered(self):
        """Hidden children should be excluded, leaving < 2 visible => None."""
        frame = _node('mixed', 'FRAME', 0, 0, 400, 100, children=[
            _node('visible', 'FRAME', 20, 20, 100, 60),
            _node('hidden', 'FRAME', 200, 20, 100, 60, visible=False),
        ])
        assert infer_layout(frame) is None

    def test_all_same_position_returns_none(self):
        """All children stacked => direction can't be inferred."""
        frame = _node('stacked', 'FRAME', 0, 0, 200, 200, children=[
            _node('a', 'FRAME', 50, 50, 100, 100),
            _node('b', 'FRAME', 50, 50, 100, 100),
            _node('c', 'FRAME', 50, 50, 100, 100),
        ])
        assert infer_layout(frame) is None

    def test_name_hint_used(self):
        """Frame name 'nav-main' should influence direction to HORIZONTAL."""
        # Ambiguous positioning (diagonal)
        frame = _node('nav-main', 'FRAME', 0, 0, 500, 500, children=[
            _node('a', 'FRAME', 0, 0, 50, 50),
            _node('b', 'FRAME', 100, 100, 50, 50),
            _node('c', 'FRAME', 200, 200, 50, 50),
        ])
        result = infer_layout(frame)
        assert result is not None
        assert result['direction'] == 'HORIZONTAL'


# ===========================================================================
# layout_from_enrichment
# ===========================================================================

class TestLayoutFromEnrichment:
    """Tests for extracting Auto Layout from enriched metadata."""

    def test_horizontal_layout(self):
        frame = {
            'layoutMode': 'HORIZONTAL',
            'itemSpacing': 16,
            'paddingTop': 20,
            'paddingRight': 24,
            'paddingBottom': 20,
            'paddingLeft': 24,
            'primaryAxisAlignItems': 'MIN',
            'counterAxisAlignItems': 'CENTER',
        }
        result = layout_from_enrichment(frame)
        assert result is not None
        assert result['direction'] == 'HORIZONTAL'
        assert result['gap'] == 16
        assert result['padding'] == {'top': 20, 'right': 24, 'bottom': 20, 'left': 24}
        assert result['primary_axis_align'] == 'MIN'
        assert result['counter_axis_align'] == 'CENTER'
        assert result['confidence'] == 'exact'

    def test_vertical_layout(self):
        frame = {'layoutMode': 'VERTICAL', 'itemSpacing': 8}
        result = layout_from_enrichment(frame)
        assert result is not None
        assert result['direction'] == 'VERTICAL'
        assert result['gap'] == 8

    def test_wrap_layout(self):
        """layoutWrap == 'WRAP' converts direction to WRAP."""
        frame = {'layoutMode': 'HORIZONTAL', 'layoutWrap': 'WRAP', 'itemSpacing': 12}
        result = layout_from_enrichment(frame)
        assert result is not None
        assert result['direction'] == 'WRAP'

    def test_no_layout_mode_returns_none(self):
        frame = {'name': 'no-layout', 'type': 'FRAME'}
        assert layout_from_enrichment(frame) is None

    def test_empty_layout_mode_returns_none(self):
        frame = {'layoutMode': ''}
        assert layout_from_enrichment(frame) is None

    def test_defaults_when_fields_missing(self):
        frame = {'layoutMode': 'HORIZONTAL'}
        result = layout_from_enrichment(frame)
        assert result['gap'] == 0
        assert result['padding'] == {'top': 0, 'right': 0, 'bottom': 0, 'left': 0}
        assert result['primary_axis_align'] == 'MIN'
        assert result['counter_axis_align'] == 'MIN'

    def test_values_not_snapped(self):
        """Enriched values should NOT be snapped to grid (preserves Figma intent)."""
        frame = {'layoutMode': 'HORIZONTAL', 'itemSpacing': 13, 'paddingTop': 7}
        result = layout_from_enrichment(frame)
        assert result['gap'] == 13  # not snapped to 12
        assert result['padding']['top'] == 7  # not snapped to 8


# ===========================================================================
# walk_and_infer
# ===========================================================================

class TestWalkAndInfer:
    """Tests for recursive tree walking with layout inference."""

    def test_single_frame_with_children(self):
        root = _node('root', 'FRAME', 0, 0, 400, 100, children=[
            _node('a', 'FRAME', 20, 20, 100, 60),
            _node('b', 'FRAME', 140, 20, 100, 60),
            _node('c', 'FRAME', 260, 20, 100, 60),
        ])
        results = walk_and_infer(root)
        assert len(results) >= 1
        assert results[0]['node_name'] == 'root'
        assert results[0]['source'] == 'inferred'
        assert results[0]['applicable'] is True

    def test_nested_frames(self):
        """Both parent and child frames with 2+ children get inferred."""
        inner = _node('inner', 'FRAME', 0, 0, 200, 200, children=[
            _node('c1', 'FRAME', 10, 10, 80, 80),
            _node('c2', 'FRAME', 10, 100, 80, 80),
        ])
        root = _node('outer', 'FRAME', 0, 0, 500, 300, children=[
            inner,
            _node('sibling', 'FRAME', 220, 0, 200, 200),
        ])
        results = walk_and_infer(root)
        names = [r['node_name'] for r in results]
        assert 'outer' in names
        assert 'inner' in names

    def test_hidden_children_excluded(self):
        """Hidden children don't count toward the 2-child minimum."""
        root = _node('root', 'FRAME', 0, 0, 400, 100, children=[
            _node('visible', 'FRAME', 20, 20, 100, 60),
            _node('hidden', 'FRAME', 200, 20, 100, 60, visible=False),
        ])
        results = walk_and_infer(root)
        # root has only 1 visible child => not eligible for layout inference
        root_results = [r for r in results if r['node_name'] == 'root']
        assert len(root_results) == 0

    def test_enriched_layout_mode(self):
        """Nodes with layoutMode use enriched data, source='exact'."""
        root = _node('auto-layout', 'FRAME', 0, 0, 400, 100, children=[
            _node('a', 'FRAME', 0, 0, 100, 100),
            _node('b', 'FRAME', 120, 0, 100, 100),
        ], layoutMode='HORIZONTAL', itemSpacing=20)
        results = walk_and_infer(root)
        assert len(results) >= 1
        assert results[0]['source'] == 'exact'
        assert results[0]['layout']['confidence'] == 'exact'

    def test_instance_not_applicable(self):
        """INSTANCE nodes are flagged as applicable=False."""
        root = _node('inst', 'INSTANCE', 0, 0, 400, 100, children=[
            _node('a', 'FRAME', 20, 20, 100, 60),
            _node('b', 'FRAME', 200, 20, 100, 60),
        ])
        results = walk_and_infer(root)
        assert len(results) >= 1
        assert results[0]['applicable'] is False

    def test_component_not_applicable(self):
        """COMPONENT nodes are flagged as applicable=False."""
        root = _node('comp', 'COMPONENT', 0, 0, 400, 100, children=[
            _node('a', 'FRAME', 20, 20, 100, 60),
            _node('b', 'FRAME', 200, 20, 100, 60),
        ])
        results = walk_and_infer(root)
        assert len(results) >= 1
        assert results[0]['applicable'] is False

    def test_section_type_eligible(self):
        """SECTION type nodes should also be eligible."""
        root = _node('sec', 'SECTION', 0, 0, 400, 100, children=[
            _node('a', 'FRAME', 20, 20, 100, 60),
            _node('b', 'FRAME', 200, 20, 100, 60),
        ])
        results = walk_and_infer(root)
        assert len(results) >= 1
        assert results[0]['node_type'] == 'SECTION'

    def test_text_node_ignored(self):
        """TEXT nodes should not be inferred."""
        root = _node('text', 'TEXT', 0, 0, 100, 20)
        results = walk_and_infer(root)
        assert len(results) == 0

    # --- Edge case: empty tree ---

    def test_empty_node_no_children(self):
        root = _node('empty', 'FRAME', 0, 0, 400, 100)
        results = walk_and_infer(root)
        assert len(results) == 0

    def test_results_accumulation(self):
        """Passing an existing results list should accumulate."""
        root = _node('root', 'FRAME', 0, 0, 400, 100, children=[
            _node('a', 'FRAME', 20, 20, 100, 60),
            _node('b', 'FRAME', 200, 20, 100, 60),
        ])
        existing = [{'node_id': 'pre-existing', 'node_name': 'old'}]
        results = walk_and_infer(root, results=existing)
        assert len(results) >= 2
        assert results[0]['node_name'] == 'old'


# ===========================================================================
# run_autolayout_inference
# ===========================================================================

class TestRunAutolayoutInference:
    """Tests for the main entry point."""

    @pytest.fixture
    def metadata_file(self, tmp_path):
        """Create a temporary metadata JSON file."""
        data = {
            'document': _node('page', 'FRAME', 0, 0, 1440, 900, children=[
                _node('section', 'FRAME', 0, 0, 1440, 400, children=[
                    _node('card-1', 'FRAME', 20, 20, 300, 360),
                    _node('card-2', 'FRAME', 340, 20, 300, 360),
                    _node('card-3', 'FRAME', 660, 20, 300, 360),
                ]),
            ])
        }
        f = tmp_path / 'metadata.json'
        f.write_text(json.dumps(data), encoding='utf-8')
        return str(f)

    def test_returns_json_without_output(self, metadata_file):
        result_str = run_autolayout_inference(metadata_file)
        result = json.loads(result_str)
        assert 'total' in result
        assert 'frames' in result
        assert result['status'] == 'dry-run'
        assert result['total'] >= 1

    def test_writes_yaml_with_output(self, metadata_file, tmp_path):
        output_file = str(tmp_path / 'autolayout.yaml')
        result_str = run_autolayout_inference(metadata_file, output_file=output_file)
        result = json.loads(result_str)
        assert result['status'] == 'dry-run'
        assert result['output'] == output_file
        assert os.path.exists(output_file)

        with open(output_file, 'r') as f:
            content = f.read()
        assert 'Figma Auto Layout Plan' in content
        assert 'direction:' in content
        assert 'gap:' in content
        assert 'source:' in content

    def test_empty_page_returns_zero(self, tmp_path):
        """Page with no eligible frames returns total=0."""
        data = {'document': _node('page', 'FRAME', 0, 0, 1440, 900)}
        f = tmp_path / 'empty.json'
        f.write_text(json.dumps(data), encoding='utf-8')
        result_str = run_autolayout_inference(str(f))
        result = json.loads(result_str)
        assert result['total'] == 0

    def test_instance_flagged_in_yaml(self, tmp_path):
        """INSTANCE nodes should have applicable: false in YAML output."""
        data = {
            'document': _node('page', 'FRAME', 0, 0, 1440, 900, children=[
                _node('inst', 'INSTANCE', 0, 0, 400, 100, children=[
                    _node('a', 'FRAME', 20, 20, 100, 60),
                    _node('b', 'FRAME', 200, 20, 100, 60),
                ]),
            ])
        }
        f = tmp_path / 'instance.json'
        f.write_text(json.dumps(data), encoding='utf-8')
        output_file = str(tmp_path / 'out.yaml')
        run_autolayout_inference(str(f), output_file=output_file)
        with open(output_file, 'r') as fh:
            content = fh.read()
        assert 'applicable: false' in content

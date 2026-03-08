"""Tests for autolayout direction inference functions.

Covers:
  - _direction_hint_from_name
  - _infer_direction_by_grid
  - _infer_direction
"""

from figma_utils.autolayout import (
    _direction_hint_from_name,
    _infer_direction,
    _infer_direction_by_grid,
)

from autolayout_helpers import _bb


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

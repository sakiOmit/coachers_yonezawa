"""Tests for name-primed Auto Layout direction (Phase 3 → Phase 4 integration)."""
import pytest
from figma_utils.autolayout import _direction_hint_from_name, _infer_direction


def _bb(x, y, w, h):
    return {'x': x, 'y': y, 'w': w, 'h': h}


class TestDirectionHintFromName:
    def test_nav_horizontal(self):
        d, c = _direction_hint_from_name('nav-main')
        assert d == 'HORIZONTAL'
        assert c >= 0.6

    def test_card_list_wrap(self):
        d, c = _direction_hint_from_name('card-list-features')
        assert d == 'WRAP'

    def test_sidebar_vertical(self):
        d, c = _direction_hint_from_name('sidebar-left')
        assert d == 'VERTICAL'

    def test_two_column(self):
        d, c = _direction_hint_from_name('two-column-layout')
        assert d == 'HORIZONTAL'
        assert c >= 0.7

    def test_generic_list_suffix(self):
        d, c = _direction_hint_from_name('feature-items')
        assert d == 'HORIZONTAL'

    def test_no_hint(self):
        d, c = _direction_hint_from_name('Frame 123')
        assert d is None
        assert c == 0

    def test_empty_name(self):
        d, c = _direction_hint_from_name('')
        assert d is None

    def test_none_name(self):
        d, c = _direction_hint_from_name(None)
        assert d is None

    def test_grid_wrap(self):
        d, c = _direction_hint_from_name('photo-grid')
        assert d == 'WRAP'

    def test_case_insensitive(self):
        d, c = _direction_hint_from_name('NAV-MAIN')
        assert d == 'HORIZONTAL'

    def test_breadcrumb_horizontal(self):
        d, c = _direction_hint_from_name('breadcrumb-path')
        assert d == 'HORIZONTAL'
        assert c >= 0.6

    def test_toolbar_horizontal(self):
        d, c = _direction_hint_from_name('toolbar-actions')
        assert d == 'HORIZONTAL'

    def test_pagination_horizontal(self):
        d, c = _direction_hint_from_name('pagination')
        assert d == 'HORIZONTAL'

    def test_menu_vertical(self):
        d, c = _direction_hint_from_name('menu-side')
        assert d == 'VERTICAL'

    def test_tag_list_wrap(self):
        d, c = _direction_hint_from_name('tag-list')
        assert d == 'WRAP'

    def test_badge_list_wrap(self):
        d, c = _direction_hint_from_name('badge-list-skills')
        assert d == 'WRAP'

    def test_2col_prefix(self):
        d, c = _direction_hint_from_name('2col-layout')
        assert d == 'HORIZONTAL'
        assert c >= 0.7

    def test_footer_links_vertical(self):
        d, c = _direction_hint_from_name('footer-links')
        assert d == 'VERTICAL'

    def test_list_suffix_lower_confidence(self):
        """Suffix-based hints have lower confidence than pattern matches."""
        d_suffix, c_suffix = _direction_hint_from_name('feature-list')
        # 'feature-list' does NOT match any _NAME_DIRECTION_HINTS pattern,
        # but matches the -list suffix → confidence 0.6
        assert d_suffix == 'HORIZONTAL'
        assert c_suffix == 0.6


class TestInferDirectionWithName:
    def test_ambiguous_geometry_uses_name_hint(self):
        """When variance ratio is ambiguous, name hint takes priority."""
        # 2x2 grid: x_var ≈ y_var (ambiguous geometry)
        bbs = [_bb(0, 0, 100, 100), _bb(120, 0, 100, 100),
               _bb(0, 120, 100, 100), _bb(120, 120, 100, 100)]

        # With sidebar name: should suggest VERTICAL
        result_sidebar = _infer_direction(bbs, frame_name='sidebar-content')
        assert result_sidebar is not None
        assert result_sidebar[0] == 'VERTICAL'

    def test_ambiguous_geometry_nav_horizontal(self):
        """Nav name primes HORIZONTAL on ambiguous geometry (3 items, mild variance)."""
        # 3 items with similar x and y spread (ambiguous variance ratio)
        bbs = [_bb(0, 0, 80, 80), _bb(100, 20, 80, 80), _bb(200, 0, 80, 80)]
        result = _infer_direction(bbs, frame_name='nav-main')
        assert result is not None
        assert result[0] == 'HORIZONTAL'

    def test_ambiguous_geometry_card_list_wrap(self):
        """card-list name primes WRAP on ambiguous geometry."""
        bbs = [_bb(0, 0, 100, 100), _bb(120, 0, 100, 100),
               _bb(0, 120, 100, 100), _bb(120, 120, 100, 100)]
        result = _infer_direction(bbs, frame_name='card-list-features')
        assert result is not None
        # WRAP hint + detect_wrap may both trigger; direction should be WRAP
        assert result[0] == 'WRAP'

    def test_clear_geometry_overrides_name(self):
        """Clear horizontal geometry wins over vertical name hint."""
        # 3 items in a clear horizontal row
        bbs = [_bb(0, 0, 100, 50), _bb(150, 0, 100, 50), _bb(300, 0, 100, 50)]
        result = _infer_direction(bbs, frame_name='sidebar-links')
        assert result is not None
        assert result[0] == 'HORIZONTAL'  # geometry wins

    def test_clear_vertical_geometry_not_overridden(self):
        """Clear vertical geometry is not overridden by horizontal name hint."""
        bbs = [_bb(0, 0, 100, 50), _bb(0, 100, 100, 50), _bb(0, 200, 100, 50)]
        result = _infer_direction(bbs, frame_name='nav-horizontal')
        assert result is not None
        assert result[0] == 'VERTICAL'  # geometry wins

    def test_backward_compat_no_name(self):
        """Without frame_name, behaves same as before."""
        bbs = [_bb(0, 0, 100, 50), _bb(150, 0, 100, 50), _bb(300, 0, 100, 50)]
        result = _infer_direction(bbs)
        assert result is not None
        assert result[0] == 'HORIZONTAL'

    def test_backward_compat_empty_name(self):
        """Empty frame_name falls through to grid counting."""
        bbs = [_bb(0, 0, 100, 100), _bb(120, 0, 100, 100),
               _bb(0, 120, 100, 100), _bb(120, 120, 100, 100)]
        result_empty = _infer_direction(bbs, frame_name='')
        result_default = _infer_direction(bbs)
        # Both should produce the same result (grid fallback)
        assert result_empty[0] == result_default[0]

    def test_two_elements_ignores_name(self):
        """Two-element case uses dx/dy, not name hints."""
        bbs = [_bb(0, 0, 100, 100), _bb(0, 120, 100, 100)]
        result = _infer_direction(bbs, frame_name='nav-main')
        assert result is not None
        # Two elements stacked vertically → VERTICAL regardless of name
        assert result[0] == 'VERTICAL'

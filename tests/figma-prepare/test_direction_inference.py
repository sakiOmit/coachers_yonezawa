"""Tests for improved direction inference with grid fallback."""
import pytest
from figma_utils.autolayout import _infer_direction, _infer_direction_by_grid


def _bb(x, y, w, h):
    return {'x': x, 'y': y, 'w': w, 'h': h}


class TestInferDirectionByGrid:
    def test_horizontal_row(self):
        """3 items in a single row -> HORIZONTAL"""
        bbs = [_bb(0, 0, 100, 100), _bb(120, 0, 100, 100), _bb(240, 0, 100, 100)]
        assert _infer_direction_by_grid(bbs) == 'HORIZONTAL'

    def test_vertical_column(self):
        """3 items in a single column -> VERTICAL"""
        bbs = [_bb(0, 0, 100, 100), _bb(0, 120, 100, 100), _bb(0, 240, 100, 100)]
        assert _infer_direction_by_grid(bbs) == 'VERTICAL'

    def test_2x2_grid(self):
        """2x2 grid -> HORIZONTAL (default for equal rows/cols)"""
        bbs = [_bb(0, 0, 100, 100), _bb(120, 0, 100, 100),
               _bb(0, 120, 100, 100), _bb(120, 120, 100, 100)]
        assert _infer_direction_by_grid(bbs) == 'HORIZONTAL'

    def test_3x2_grid(self):
        """3 cols x 2 rows -> HORIZONTAL (fewer rows than cols, primary axis is horizontal)"""
        bbs = [_bb(0, 0, 80, 80), _bb(100, 0, 80, 80), _bb(200, 0, 80, 80),
               _bb(0, 100, 80, 80), _bb(100, 100, 80, 80), _bb(200, 100, 80, 80)]
        assert _infer_direction_by_grid(bbs) == 'HORIZONTAL'

    def test_2x3_grid(self):
        """2 cols x 3 rows -> VERTICAL (fewer cols than rows, primary axis is vertical)"""
        bbs = [_bb(0, 0, 80, 80), _bb(100, 0, 80, 80),
               _bb(0, 100, 80, 80), _bb(100, 100, 80, 80),
               _bb(0, 200, 80, 80), _bb(100, 200, 80, 80)]
        assert _infer_direction_by_grid(bbs) == 'VERTICAL'


class TestImprovedInferDirection:
    def test_clear_horizontal(self):
        """Clear horizontal layout still works"""
        bbs = [_bb(0, 0, 100, 50), _bb(150, 0, 100, 50), _bb(300, 0, 100, 50)]
        result = _infer_direction(bbs)
        assert result is not None
        direction, _ = result
        assert direction == 'HORIZONTAL'

    def test_clear_vertical(self):
        """Clear vertical layout still works"""
        bbs = [_bb(0, 0, 100, 50), _bb(0, 100, 100, 50), _bb(0, 200, 100, 50)]
        result = _infer_direction(bbs)
        assert result is not None
        direction, _ = result
        assert direction == 'VERTICAL'

    def test_square_layout_uses_grid_fallback(self):
        """Square-ish layout (variance ratio < 1.5) falls through to grid counting.
        2x2 grid with 4 elements: grid fallback picks HORIZONTAL, then detect_wrap
        sees 4+ HORIZONTAL elements in 2 rows and upgrades to WRAP."""
        bbs = [_bb(0, 0, 100, 100), _bb(120, 0, 100, 100),
               _bb(0, 120, 100, 100), _bb(120, 120, 100, 100)]
        result = _infer_direction(bbs)
        assert result is not None
        direction, is_wrap = result
        # Grid fallback picks HORIZONTAL, then WRAP detection triggers (4 elements, 2 rows)
        assert direction == 'WRAP'
        assert is_wrap is True

    def test_ambiguous_3_elements_row(self):
        """3 elements in near-square layout but single row -> HORIZONTAL (no WRAP)"""
        # x_var ~ y_var but only 3 elements (< 4), no WRAP possible
        bbs = [_bb(0, 0, 100, 100), _bb(120, 5, 100, 100), _bb(240, 0, 100, 100)]
        result = _infer_direction(bbs)
        assert result is not None
        direction, is_wrap = result
        assert direction == 'HORIZONTAL'
        assert is_wrap is False

    def test_all_same_position_returns_none(self):
        """All children at same position -> None"""
        bbs = [_bb(0, 0, 100, 100), _bb(0, 0, 100, 100), _bb(0, 0, 100, 100)]
        assert _infer_direction(bbs) is None

    def test_two_elements_horizontal(self):
        """Two elements side by side -> HORIZONTAL"""
        bbs = [_bb(0, 0, 100, 100), _bb(200, 0, 100, 100)]
        result = _infer_direction(bbs)
        assert result is not None
        direction, _ = result
        assert direction == 'HORIZONTAL'

    def test_two_elements_vertical(self):
        """Two elements stacked -> VERTICAL"""
        bbs = [_bb(0, 0, 100, 100), _bb(0, 200, 100, 100)]
        result = _infer_direction(bbs)
        assert result is not None
        direction, _ = result
        assert direction == 'VERTICAL'

    def test_clear_vertical_with_ratio(self):
        """y_var >> x_var * VARIANCE_RATIO -> VERTICAL (Stage 1)"""
        # All at same X, spread vertically
        bbs = [_bb(0, 0, 100, 50), _bb(5, 200, 100, 50), _bb(2, 400, 100, 50)]
        result = _infer_direction(bbs)
        assert result is not None
        direction, _ = result
        assert direction == 'VERTICAL'

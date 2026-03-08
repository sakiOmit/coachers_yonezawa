"""Tests for autolayout gap, padding, alignment, and infer_layout functions.

Covers:
  - _infer_gap
  - _infer_padding
  - _infer_alignment
  - infer_layout
"""

from figma_utils.autolayout import (
    _infer_alignment,
    _infer_gap,
    _infer_padding,
    infer_layout,
)

from autolayout_helpers import _bb, _node


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

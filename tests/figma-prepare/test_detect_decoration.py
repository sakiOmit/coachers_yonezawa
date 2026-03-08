"""Tests for is_decoration_pattern and decoration_dominant_shape (Issue 189)."""
import pytest

from figma_utils import (
    DECORATION_MAX_SIZE,
    DECORATION_MIN_SHAPES,
    DECORATION_SHAPE_RATIO,
    decoration_dominant_shape,
    is_decoration_pattern,
)


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

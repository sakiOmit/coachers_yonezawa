"""Tests for rename benchmark improvements.

Covers 3 accuracy improvements to _infer_from_shape():
1. IMAGE nodes get img- prefix (not bg-)
2. Small ELLIPSE nodes get bullet- prefix (not circle-)
3. Full-width RECTANGLE nodes get section-bg- prefix (not bg-)
"""

import pytest

from figma_utils.rename_strategies import _infer_from_shape
from figma_utils.constants import SECTION_ROOT_WIDTH, BULLET_MAX_SIZE, SECTION_BG_WIDTH_RATIO


# ---------------------------------------------------------------------------
# Improvement 1: IMAGE nodes → img- prefix
# ---------------------------------------------------------------------------

class TestImageNodePrefix:
    """IMAGE type nodes should always get img- prefix."""

    def test_image_node_gets_img_prefix(self):
        """IMAGE node type should return img-N, not bg-N."""
        node = {
            'type': 'IMAGE',
            'name': 'Image 5',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 300, 'height': 200},
        }
        result = _infer_from_shape(node, 'IMAGE', [], 300, 200, 0)
        assert result == 'img-0'

    def test_image_node_with_sibling_index(self):
        """IMAGE node with non-zero sibling index."""
        node = {
            'type': 'IMAGE',
            'name': 'Image 12',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 600, 'height': 400},
        }
        result = _infer_from_shape(node, 'IMAGE', [], 600, 400, 3)
        assert result == 'img-3'

    def test_rectangle_with_image_fill_gets_img(self):
        """RECTANGLE with IMAGE fill should still get img- prefix."""
        node = {
            'type': 'RECTANGLE',
            'name': 'Rectangle 1',
            'fills': [{'type': 'IMAGE', 'imageRef': 'abc123'}],
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 300, 'height': 200},
        }
        result = _infer_from_shape(node, 'RECTANGLE', [], 300, 200, 0)
        assert result == 'img-0'


# ---------------------------------------------------------------------------
# Improvement 2: Small ELLIPSE → bullet- prefix
# ---------------------------------------------------------------------------

class TestSmallEllipseBullet:
    """Small ELLIPSE nodes (<=12px) should get bullet- prefix."""

    def test_small_ellipse_gets_bullet_prefix(self):
        """9x9 ELLIPSE should return bullet-N."""
        node = {
            'type': 'ELLIPSE',
            'name': 'Ellipse 30',
            'absoluteBoundingBox': {'x': 100, 'y': 200, 'width': 9, 'height': 9},
        }
        result = _infer_from_shape(node, 'ELLIPSE', [], 9, 9, 0)
        assert result == 'bullet-0'

    def test_ellipse_at_max_bullet_size(self):
        """ELLIPSE at exactly BULLET_MAX_SIZE (12px) should still be bullet."""
        node = {
            'type': 'ELLIPSE',
            'name': 'Ellipse 5',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 12, 'height': 12},
        }
        result = _infer_from_shape(node, 'ELLIPSE', [], 12, 12, 2)
        assert result == 'bullet-2'

    def test_large_ellipse_gets_circle_prefix(self):
        """Large ELLIPSE (>12px) should still get circle-N."""
        node = {
            'type': 'ELLIPSE',
            'name': 'Ellipse 1',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 50, 'height': 50},
        }
        result = _infer_from_shape(node, 'ELLIPSE', [], 50, 50, 0)
        assert result == 'circle-0'

    def test_ellipse_just_above_bullet_threshold(self):
        """ELLIPSE at 13px should get circle-N, not bullet-N."""
        node = {
            'type': 'ELLIPSE',
            'name': 'Ellipse 7',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 13, 'height': 13},
        }
        result = _infer_from_shape(node, 'ELLIPSE', [], 13, 13, 1)
        assert result == 'circle-1'

    def test_small_ellipse_with_children_skipped(self):
        """ELLIPSE with children should be skipped (not a leaf)."""
        node = {
            'type': 'ELLIPSE',
            'name': 'Ellipse 2',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 9, 'height': 9},
        }
        children = [{'type': 'TEXT', 'name': 'Text 1'}]
        result = _infer_from_shape(node, 'ELLIPSE', children, 9, 9, 0)
        assert result is None


# ---------------------------------------------------------------------------
# Improvement 3: Section-level background RECTANGLE → section-bg-
# ---------------------------------------------------------------------------

class TestSectionBgPrefix:
    """Full-width RECTANGLEs should get section-bg- prefix."""

    def test_full_width_rect_gets_section_bg(self):
        """RECTANGLE at 1440px width should return section-bg-N."""
        node = {
            'type': 'RECTANGLE',
            'name': 'Rectangle 95',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 607},
        }
        result = _infer_from_shape(node, 'RECTANGLE', [], 1440, 607, 0)
        assert result == 'section-bg-0'

    def test_normal_rect_gets_bg(self):
        """Normal-sized RECTANGLE should return bg-N."""
        node = {
            'type': 'RECTANGLE',
            'name': 'Rectangle 42',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 300, 'height': 200},
        }
        result = _infer_from_shape(node, 'RECTANGLE', [], 300, 200, 0)
        assert result == 'bg-0'

    def test_section_bg_at_exact_threshold(self):
        """Width = 1296 (exactly 0.9 * 1440) should get section-bg-."""
        threshold = SECTION_ROOT_WIDTH * SECTION_BG_WIDTH_RATIO  # 1296
        node = {
            'type': 'RECTANGLE',
            'name': 'Rectangle 10',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': threshold, 'height': 500},
        }
        result = _infer_from_shape(node, 'RECTANGLE', [], threshold, 500, 5)
        assert result == 'section-bg-5'

    def test_section_bg_just_below_threshold(self):
        """Width = 1295 (just below 1296) should get bg-."""
        threshold = SECTION_ROOT_WIDTH * SECTION_BG_WIDTH_RATIO  # 1296
        node = {
            'type': 'RECTANGLE',
            'name': 'Rectangle 11',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': threshold - 1, 'height': 500},
        }
        result = _infer_from_shape(node, 'RECTANGLE', [], threshold - 1, 500, 0)
        assert result == 'bg-0'

    def test_thin_wide_rect_still_divider(self):
        """Full-width but thin RECTANGLE should still be divider (divider check first)."""
        node = {
            'type': 'RECTANGLE',
            'name': 'Rectangle 20',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 2},
        }
        result = _infer_from_shape(node, 'RECTANGLE', [], 1440, 2, 0)
        assert result == 'divider-0'

    def test_rect_with_image_fill_not_section_bg(self):
        """RECTANGLE with IMAGE fill should get img- regardless of width."""
        node = {
            'type': 'RECTANGLE',
            'name': 'Rectangle 30',
            'fills': [{'type': 'IMAGE', 'imageRef': 'hero-bg'}],
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 800},
        }
        result = _infer_from_shape(node, 'RECTANGLE', [], 1440, 800, 0)
        assert result == 'img-0'

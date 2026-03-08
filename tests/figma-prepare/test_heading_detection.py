"""Tests for heading classification and heading-content pairing."""
import pytest

from figma_utils import (
    detect_heading_content_pairs,
    is_heading_like,
)


# ============================================================
# is_heading_like / detect_heading_content_pairs (Issue 166)
# ============================================================
class TestIsHeadingLike:
    def test_text_heavy_frame(self):
        """Frame with mostly TEXT/VECTOR children → heading-like."""
        node = {
            "type": "FRAME",
            "children": [
                {"type": "TEXT", "children": []},
                {"type": "TEXT", "children": []},
                {"type": "VECTOR", "children": []},
            ],
        }
        assert is_heading_like(node) is True

    def test_image_heavy_frame(self):
        """Frame with mostly RECTANGLE/IMAGE → not heading-like."""
        node = {
            "type": "FRAME",
            "children": [
                {"type": "RECTANGLE", "children": []},
                {"type": "IMAGE", "children": []},
                {"type": "TEXT", "children": []},
            ],
        }
        assert is_heading_like(node) is False

    def test_empty_frame(self):
        """Frame with no children → not heading-like."""
        assert is_heading_like({"type": "FRAME", "children": []}) is False

    def test_leaf_node(self):
        """Leaf node (no children key) → not heading-like."""
        assert is_heading_like({"type": "TEXT"}) is False

    def test_too_many_children(self):
        """Frame with > HEADING_MAX_CHILDREN → not heading-like."""
        node = {
            "type": "FRAME",
            "children": [{"type": "TEXT", "children": []} for _ in range(6)],
        }
        assert is_heading_like(node) is False

    def test_nested_text(self):
        """Frame with nested TEXT descendants → heading-like."""
        node = {
            "type": "FRAME",
            "children": [
                {"type": "FRAME", "children": [
                    {"type": "TEXT", "children": []},
                    {"type": "TEXT", "children": []},
                ]},
                {"type": "ELLIPSE", "children": []},
            ],
        }
        assert is_heading_like(node) is True

    # --- Issue 175: ELLIPSE decoration false positive ---

    def test_is_heading_like_ellipse_only_false(self):
        """Frame with 3 ELLIPSE children, 0 TEXT → not heading-like."""
        node = {
            "type": "FRAME",
            "children": [
                {"type": "ELLIPSE", "children": []},
                {"type": "ELLIPSE", "children": []},
                {"type": "ELLIPSE", "children": []},
            ],
        }
        assert is_heading_like(node) is False

    def test_is_heading_like_ellipse_dominated_false(self):
        """Frame with 3 ELLIPSE + 1 TEXT → not heading-like (ELLIPSE > TEXT)."""
        node = {
            "type": "FRAME",
            "children": [
                {"type": "ELLIPSE", "children": []},
                {"type": "ELLIPSE", "children": []},
                {"type": "ELLIPSE", "children": []},
                {"type": "TEXT", "children": []},
            ],
        }
        assert is_heading_like(node) is False

    def test_is_heading_like_text_with_ellipse_true(self):
        """Frame with 2 TEXT + 1 ELLIPSE → heading-like (TEXT > ELLIPSE)."""
        node = {
            "type": "FRAME",
            "children": [
                {"type": "TEXT", "children": []},
                {"type": "TEXT", "children": []},
                {"type": "ELLIPSE", "children": []},
            ],
        }
        assert is_heading_like(node) is True

    def test_is_heading_like_equal_text_ellipse_true(self):
        """Frame with 2 TEXT + 2 ELLIPSE → heading-like (TEXT == ELLIPSE)."""
        node = {
            "type": "FRAME",
            "children": [
                {"type": "TEXT", "children": []},
                {"type": "TEXT", "children": []},
                {"type": "ELLIPSE", "children": []},
                {"type": "ELLIPSE", "children": []},
            ],
        }
        assert is_heading_like(node) is True


class TestDetectHeadingContentPairs:
    def test_heading_content_pair(self):
        """Small heading frame (h=215) + large content frame (h=746) → pair."""
        children = [
            {
                "type": "FRAME", "name": "section-heading",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 215},
                "children": [
                    {"type": "TEXT", "children": []},
                    {"type": "VECTOR", "children": []},
                ],
            },
            {
                "type": "FRAME", "name": "section-content",
                "absoluteBoundingBox": {"x": 0, "y": 215, "width": 1440, "height": 746},
                "children": [
                    {"type": "TEXT", "children": []},
                    {"type": "FRAME", "children": [
                        {"type": "TEXT", "children": []},
                    ]},
                ],
            },
        ]
        pairs = detect_heading_content_pairs(children)
        assert len(pairs) == 1
        assert pairs[0]['heading_idx'] == 0
        assert pairs[0]['content_idx'] == 1

    def test_equal_height_not_paired(self):
        """Two frames of equal height → no pair."""
        children = [
            {
                "type": "FRAME", "name": "a",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                "children": [{"type": "TEXT", "children": []}],
            },
            {
                "type": "FRAME", "name": "b",
                "absoluteBoundingBox": {"x": 0, "y": 500, "width": 1440, "height": 500},
                "children": [{"type": "TEXT", "children": []}],
            },
        ]
        pairs = detect_heading_content_pairs(children)
        assert len(pairs) == 0

    def test_content_must_be_frame(self):
        """Heading followed by TEXT (not FRAME) → no pair."""
        children = [
            {
                "type": "FRAME", "name": "heading",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 100},
                "children": [{"type": "TEXT", "children": []}],
            },
            {
                "type": "TEXT", "name": "text",
                "absoluteBoundingBox": {"x": 0, "y": 100, "width": 1440, "height": 500},
            },
        ]
        pairs = detect_heading_content_pairs(children)
        assert len(pairs) == 0

    def test_content_must_have_children(self):
        """Heading followed by empty FRAME → no pair."""
        children = [
            {
                "type": "FRAME", "name": "heading",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 100},
                "children": [{"type": "TEXT", "children": []}],
            },
            {
                "type": "FRAME", "name": "empty",
                "absoluteBoundingBox": {"x": 0, "y": 100, "width": 1440, "height": 500},
                "children": [],
            },
        ]
        pairs = detect_heading_content_pairs(children)
        assert len(pairs) == 0

    def test_single_child(self):
        """Only one child → no pairs."""
        children = [
            {
                "type": "FRAME", "name": "only",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 100},
                "children": [{"type": "TEXT", "children": []}],
            },
        ]
        pairs = detect_heading_content_pairs(children)
        assert len(pairs) == 0

    def test_multiple_pairs(self):
        """Two heading-content pairs in sequence."""
        children = [
            {
                "type": "FRAME", "name": "h1",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 100},
                "children": [{"type": "TEXT", "children": []}],
            },
            {
                "type": "FRAME", "name": "c1",
                "absoluteBoundingBox": {"x": 0, "y": 100, "width": 1440, "height": 600},
                "children": [{"type": "TEXT", "children": []}],
            },
            {
                "type": "FRAME", "name": "h2",
                "absoluteBoundingBox": {"x": 0, "y": 700, "width": 1440, "height": 80},
                "children": [{"type": "TEXT", "children": []}, {"type": "VECTOR", "children": []}],
            },
            {
                "type": "FRAME", "name": "c2",
                "absoluteBoundingBox": {"x": 0, "y": 780, "width": 1440, "height": 500},
                "children": [{"type": "FRAME", "children": [{"type": "TEXT", "children": []}]}],
            },
        ]
        pairs = detect_heading_content_pairs(children)
        assert len(pairs) == 2

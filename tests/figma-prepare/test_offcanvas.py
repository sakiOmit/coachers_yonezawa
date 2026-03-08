"""Tests for off-canvas detection, hidden node filtering in analyze-structure and grouping."""
import json
import os
import pytest

from helpers import run_script, write_fixture

from figma_utils import (
    is_off_canvas,
    OFF_CANVAS_MARGIN,
)


class TestIsOffCanvas:
    def test_element_within_viewport(self):
        """Element at x=100, w=200 on a 1440px page -> not off-canvas."""
        node = {"absoluteBoundingBox": {"x": 100, "y": 0, "width": 200, "height": 100}}
        assert is_off_canvas(node, 1440) is False

    def test_element_at_origin(self):
        """Element at x=0 -> not off-canvas."""
        node = {"absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 100}}
        assert is_off_canvas(node, 1440) is False

    def test_element_far_right(self):
        """Element at x=2200 (> 1440 * 1.5 = 2160) -> off-canvas."""
        node = {"absoluteBoundingBox": {"x": 2200, "y": 0, "width": 300, "height": 100}}
        assert is_off_canvas(node, 1440) is True

    def test_element_just_at_margin(self):
        """Element at x=2160 (= 1440 * 1.5) -> not off-canvas (must exceed, not equal)."""
        node = {"absoluteBoundingBox": {"x": 2160, "y": 0, "width": 200, "height": 100}}
        assert is_off_canvas(node, 1440) is False

    def test_element_just_beyond_margin(self):
        """Element at x=2161 (> 1440 * 1.5) -> off-canvas."""
        node = {"absoluteBoundingBox": {"x": 2161, "y": 0, "width": 200, "height": 100}}
        assert is_off_canvas(node, 1440) is True

    def test_element_completely_left(self):
        """Element at x=-400, w=200 (right edge = -200 < 0) -> off-canvas."""
        node = {"absoluteBoundingBox": {"x": -400, "y": 0, "width": 200, "height": 100}}
        assert is_off_canvas(node, 1440) is True

    def test_element_partially_left(self):
        """Element at x=-100, w=200 (right edge = 100 > 0) -> not off-canvas."""
        node = {"absoluteBoundingBox": {"x": -100, "y": 0, "width": 200, "height": 100}}
        assert is_off_canvas(node, 1440) is False

    def test_zero_page_width(self):
        """page_width=0 -> always returns False (safety guard)."""
        node = {"absoluteBoundingBox": {"x": 5000, "y": 0, "width": 200, "height": 100}}
        assert is_off_canvas(node, 0) is False

    def test_zero_width_element(self):
        """Element with w=0 -> returns False (degenerate bbox)."""
        node = {"absoluteBoundingBox": {"x": 5000, "y": 0, "width": 0, "height": 100}}
        assert is_off_canvas(node, 1440) is False

    def test_no_bbox(self):
        """Node with no absoluteBoundingBox -> returns False (get_bbox returns defaults)."""
        node = {}
        assert is_off_canvas(node, 1440) is False

    def test_constant_value(self):
        """OFF_CANVAS_MARGIN should be 1.5."""
        assert OFF_CANVAS_MARGIN == 1.5

    # --- Issue #2: Negative-X artboard root_x tests ---

    def test_negative_root_x_child_inside(self):
        """Child inside artboard at negative X should NOT be off-canvas.

        Artboard at x=-5542, width=1440. Child at absolute x=-5442 (relative 100).
        rel_x = -5442 - (-5542) = 100 -> inside viewport.
        """
        node = {"absoluteBoundingBox": {"x": -5442, "y": 0, "width": 200, "height": 100}}
        assert is_off_canvas(node, 1440, root_x=-5542) is False

    def test_negative_root_x_child_at_origin(self):
        """Child at relative x=0 in negative-X artboard should NOT be off-canvas.

        Artboard at x=-5542. Child at absolute x=-5542 (relative 0).
        rel_x = -5542 - (-5542) = 0 -> at viewport origin.
        """
        node = {"absoluteBoundingBox": {"x": -5542, "y": 0, "width": 1440, "height": 100}}
        assert is_off_canvas(node, 1440, root_x=-5542) is False

    def test_negative_root_x_child_truly_off_canvas_right(self):
        """Child truly off-canvas to the right in negative-X artboard.

        Artboard at x=-5542, width=1440.
        Child at absolute x=-3200 -> rel_x = -3200 - (-5542) = 2342 > 1440 * 1.5 = 2160.
        """
        node = {"absoluteBoundingBox": {"x": -3200, "y": 0, "width": 200, "height": 100}}
        assert is_off_canvas(node, 1440, root_x=-5542) is True

    def test_negative_root_x_child_truly_off_canvas_left(self):
        """Child truly off-canvas to the left in negative-X artboard.

        Artboard at x=-5542, width=1440.
        Child at absolute x=-6000, width=200 -> rel_x = -6000 - (-5542) = -458.
        rel_x + w = -458 + 200 = -258 < 0 -> off-canvas.
        """
        node = {"absoluteBoundingBox": {"x": -6000, "y": 0, "width": 200, "height": 100}}
        assert is_off_canvas(node, 1440, root_x=-5542) is True

    def test_negative_root_x_false_positive_without_root_x(self):
        """Without root_x, child in negative-X artboard is falsely detected as off-canvas.

        This demonstrates the bug: when root_x is not provided (defaults to 0),
        a child at absolute x=-5442 has rel_x = -5442, and -5442 + 200 = -5242 < 0
        -> incorrectly flagged as off-canvas.
        """
        node = {"absoluteBoundingBox": {"x": -5442, "y": 0, "width": 200, "height": 100}}
        # Without root_x correction: FALSE POSITIVE
        assert is_off_canvas(node, 1440, root_x=0) is True
        # With root_x correction: correctly NOT off-canvas
        assert is_off_canvas(node, 1440, root_x=-5542) is False

    def test_zero_root_x_regression(self):
        """Artboard at x=0 with root_x=0 should behave as before (regression check)."""
        # Inside viewport
        node_in = {"absoluteBoundingBox": {"x": 100, "y": 0, "width": 200, "height": 100}}
        assert is_off_canvas(node_in, 1440, root_x=0) is False
        # Off-canvas right
        node_right = {"absoluteBoundingBox": {"x": 2200, "y": 0, "width": 300, "height": 100}}
        assert is_off_canvas(node_right, 1440, root_x=0) is True
        # Off-canvas left
        node_left = {"absoluteBoundingBox": {"x": -400, "y": 0, "width": 200, "height": 100}}
        assert is_off_canvas(node_left, 1440, root_x=0) is True


# ============================================================
# analyze-structure.sh: hidden node filtering (Issue 187)
# ============================================================
class TestAnalyzeStructureHiddenNodes:
    def test_hidden_nodes_excluded_from_scoring(self):
        """Hidden (visible: false) nodes should not be counted in total/unnamed."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Section 1",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                        "children": [
                            {"id": "2:1", "type": "TEXT", "name": "Title",
                             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 200, "height": 30}},
                        ],
                    },
                    {
                        "id": "1:2", "type": "FRAME", "name": "Frame 1",
                        "visible": False,
                        "absoluteBoundingBox": {"x": 0, "y": 500, "width": 1440, "height": 500},
                        "children": [
                            {"id": "2:2", "type": "TEXT", "name": "Text 1",
                             "absoluteBoundingBox": {"x": 0, "y": 500, "width": 200, "height": 30}},
                            {"id": "2:3", "type": "RECTANGLE", "name": "Rectangle 1",
                             "absoluteBoundingBox": {"x": 0, "y": 530, "width": 200, "height": 200}},
                        ],
                    },
                ],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("analyze-structure.sh", tmp)
            metrics = result["metrics"]
            # Hidden node (Frame 1) detected as 1 hidden node
            # (its subtree is skipped entirely without recursive counting)
            assert metrics["hidden_nodes"] == 1
            # "Rectangle 1" matches UNNAMED_RE but is hidden -> not counted as unnamed
            assert metrics["unnamed_nodes"] == 0
            # Total should not include hidden subtree
            # Visible: Page (root) + Section 1 + Title = 3
            assert metrics["total_nodes"] == 3
        finally:
            os.unlink(tmp)

    def test_no_hidden_nodes(self):
        """When no hidden nodes, hidden_nodes metric should be 0."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Section",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                        "children": [
                            {"id": "2:1", "type": "TEXT", "name": "Title",
                             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 200, "height": 30}},
                        ],
                    },
                ],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("analyze-structure.sh", tmp)
            assert result["metrics"]["hidden_nodes"] == 0
        finally:
            os.unlink(tmp)


# ============================================================
# analyze-structure.sh: off-canvas node filtering (Issue 182)
# ============================================================
class TestAnalyzeStructureOffCanvas:
    def test_off_canvas_nodes_excluded(self):
        """Elements far right (x > page_width * 1.5) should be excluded."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Section 1",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                        "children": [
                            {"id": "2:1", "type": "TEXT", "name": "Title",
                             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 200, "height": 30}},
                        ],
                    },
                    {
                        "id": "1:2", "type": "FRAME", "name": "Frame 1",
                        "absoluteBoundingBox": {"x": 3000, "y": 0, "width": 500, "height": 500},
                        "children": [
                            {"id": "2:2", "type": "TEXT", "name": "Text 1",
                             "absoluteBoundingBox": {"x": 3000, "y": 0, "width": 200, "height": 30}},
                            {"id": "2:3", "type": "RECTANGLE", "name": "Rectangle 1",
                             "absoluteBoundingBox": {"x": 3000, "y": 30, "width": 200, "height": 200}},
                        ],
                    },
                ],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("analyze-structure.sh", tmp)
            metrics = result["metrics"]
            # Off-canvas node (Frame 1 at x=3000) counted as 1 off-canvas
            assert metrics["off_canvas_nodes"] == 1
            # Total should not include off-canvas subtree
            # Visible: Page (root) + Section 1 + Title = 3
            assert metrics["total_nodes"] == 3
        finally:
            os.unlink(tmp)

    def test_element_within_margin_not_excluded(self):
        """Elements within 1.5x page_width are NOT off-canvas."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Section",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                        "children": [],
                    },
                    {
                        "id": "1:2", "type": "FRAME", "name": "Sidebar",
                        "absoluteBoundingBox": {"x": 1500, "y": 0, "width": 300, "height": 500},
                        "children": [],
                    },
                ],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("analyze-structure.sh", tmp)
            metrics = result["metrics"]
            # x=1500 < 1440 * 1.5 = 2160 -> not off-canvas
            assert metrics["off_canvas_nodes"] == 0
            # All nodes counted: Page + Section + Sidebar = 3
            assert metrics["total_nodes"] == 3
        finally:
            os.unlink(tmp)

    def test_element_negative_x_off_canvas(self):
        """Elements completely to the left (x + w < 0) are off-canvas."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Section",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                        "children": [],
                    },
                    {
                        "id": "1:2", "type": "FRAME", "name": "Hidden Left",
                        "absoluteBoundingBox": {"x": -500, "y": 0, "width": 200, "height": 500},
                        "children": [],
                    },
                ],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("analyze-structure.sh", tmp)
            metrics = result["metrics"]
            assert metrics["off_canvas_nodes"] == 1
        finally:
            os.unlink(tmp)


# ============================================================
# detect-grouping-candidates.sh: hidden node filtering (Issue 187)
# ============================================================
class TestGroupingHiddenNodes:
    def test_hidden_children_excluded_from_grouping(self):
        """Hidden children should not appear in grouping candidates."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Section 1",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                        "children": [
                            {"id": "2:1", "type": "TEXT", "name": "Title",
                             "absoluteBoundingBox": {"x": 10, "y": 10, "width": 200, "height": 30}},
                        ],
                    },
                    {
                        "id": "1:2", "type": "FRAME", "name": "Frame 1",
                        "visible": False,
                        "absoluteBoundingBox": {"x": 0, "y": 500, "width": 1440, "height": 500},
                        "children": [
                            {"id": "2:2", "type": "TEXT", "name": "Text 1",
                             "absoluteBoundingBox": {"x": 10, "y": 510, "width": 200, "height": 30}},
                        ],
                    },
                    {
                        "id": "1:3", "type": "FRAME", "name": "Section 2",
                        "absoluteBoundingBox": {"x": 0, "y": 1000, "width": 1440, "height": 500},
                        "children": [
                            {"id": "2:3", "type": "TEXT", "name": "Subtitle",
                             "absoluteBoundingBox": {"x": 10, "y": 1010, "width": 200, "height": 30}},
                        ],
                    },
                ],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("detect-grouping-candidates.sh", tmp)
            candidates = result.get("candidates", [])
            all_node_ids = []
            for c in candidates:
                all_node_ids.extend(c.get("node_ids", []))
            assert "1:2" not in all_node_ids
            assert "2:2" not in all_node_ids
        finally:
            os.unlink(tmp)


# ============================================================
# detect-grouping-candidates.sh: off-canvas node filtering (Issue 182)
# ============================================================
class TestGroupingOffCanvas:
    def test_off_canvas_excluded_from_root_grouping(self):
        """Off-canvas nodes at root level should be excluded from grouping."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Section 1",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                        "children": [
                            {"id": "2:1", "type": "TEXT", "name": "Title",
                             "absoluteBoundingBox": {"x": 10, "y": 10, "width": 200, "height": 30}},
                        ],
                    },
                    {
                        "id": "1:2", "type": "FRAME", "name": "Off Canvas Asset",
                        "absoluteBoundingBox": {"x": 5000, "y": 0, "width": 500, "height": 500},
                        "children": [
                            {"id": "2:2", "type": "TEXT", "name": "Hidden Text",
                             "absoluteBoundingBox": {"x": 5000, "y": 10, "width": 200, "height": 30}},
                        ],
                    },
                    {
                        "id": "1:3", "type": "FRAME", "name": "Section 2",
                        "absoluteBoundingBox": {"x": 0, "y": 500, "width": 1440, "height": 500},
                        "children": [
                            {"id": "2:3", "type": "TEXT", "name": "Subtitle",
                             "absoluteBoundingBox": {"x": 10, "y": 510, "width": 200, "height": 30}},
                        ],
                    },
                ],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("detect-grouping-candidates.sh", tmp)
            candidates = result.get("candidates", [])
            all_node_ids = []
            for c in candidates:
                all_node_ids.extend(c.get("node_ids", []))
            assert "1:2" not in all_node_ids
            assert "2:2" not in all_node_ids
        finally:
            os.unlink(tmp)

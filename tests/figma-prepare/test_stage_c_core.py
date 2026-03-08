"""Tests for Stage C core: nested flat counting (TestCountNestedFlat, TestAnalyzeStructureNestedFlat)."""
import json
import os
import pytest
import tempfile

from helpers import run_script, write_fixture

from figma_utils import (
    compare_grouping_by_section,
    count_nested_flat,
    FLAT_THRESHOLD,
    MAX_STAGE_C_DEPTH,
    STAGE_A_ONLY_DETECTORS,
    STAGE_C_COVERABLE_DETECTORS,
    STAGE_C_COVERAGE_THRESHOLD,
)


class TestCountNestedFlat:
    """Issue 231: count_nested_flat only counts within section root boundaries."""

    def _make_section_root(self, children, name="section-hero", width=1440, height=1000):
        """Helper to create a section root node."""
        return {
            "type": "FRAME", "name": name,
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": width, "height": height},
            "children": children,
        }

    def _make_page(self, children, width=1440, height=5000):
        """Helper to create a page-level node (not a section root itself for traversal)."""
        return {
            "type": "FRAME", "name": "Page",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": width, "height": height},
            "children": children,
        }

    def test_empty_node(self):
        """Node with no children returns 0."""
        node = {"type": "FRAME", "children": []}
        assert count_nested_flat(node) == 0

    def test_section_root_itself_not_counted(self):
        """A section root (width=1440) with >15 children is NOT counted (counted by flat_sections)."""
        children = [{"type": "TEXT", "name": f"t{i}"} for i in range(20)]
        section = self._make_section_root(children)
        # The section root itself is excluded; none of its TEXT children are FRAME/GROUP
        assert count_nested_flat(section) == 0

    def test_flat_frame_inside_section_root_counted(self):
        """A FRAME inside a section root with >15 children IS counted."""
        inner_children = [{"type": "TEXT", "name": f"t{i}"} for i in range(20)]
        inner = {"type": "FRAME", "name": "FlatInner", "children": inner_children}
        section = self._make_section_root([inner])
        assert count_nested_flat(section) == 1

    def test_frame_outside_section_root_not_counted(self):
        """FRAME above section root boundary (no section root ancestor) is NOT counted."""
        # A non-section-root FRAME with many children, no section root in subtree
        children = [{"type": "TEXT", "name": f"t{i}"} for i in range(20)]
        node = {"type": "FRAME", "name": "non-section",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 500, "height": 300},
                "children": children}
        assert count_nested_flat(node) == 0

    def test_page_with_section_root_containing_flat_frame(self):
        """Page > section root > flat FRAME: only the flat FRAME inside is counted."""
        inner_children = [{"type": "TEXT", "name": f"t{i}"} for i in range(20)]
        inner = {"type": "FRAME", "name": "FlatInner", "children": inner_children}
        section = self._make_section_root([inner] + [{"type": "TEXT", "name": f"s{i}"} for i in range(16)])
        page = self._make_page([section])
        # section root has 17 children but is NOT counted (flat_sections handles it)
        # inner has 20 children and IS counted
        assert count_nested_flat(page) == 1

    def test_multiple_section_roots_with_nested_flat(self):
        """Multiple section roots each with flat descendants."""
        inner1_children = [{"type": "TEXT", "name": f"t{i}"} for i in range(20)]
        inner1 = {"type": "FRAME", "name": "FlatInner1", "children": inner1_children}
        section1 = self._make_section_root([inner1], name="section-hero")

        inner2_children = [{"type": "RECTANGLE", "name": f"r{i}"} for i in range(18)]
        inner2 = {"type": "GROUP", "name": "FlatInner2", "children": inner2_children}
        section2 = self._make_section_root([inner2], name="section-about", height=800)
        section2["absoluteBoundingBox"]["y"] = 1000

        page = self._make_page([section1, section2])
        assert count_nested_flat(page) == 2

    def test_hidden_children_excluded(self):
        """Hidden children (visible: false) should not count toward threshold."""
        visible = [{"type": "TEXT", "name": f"t{i}"} for i in range(14)]
        hidden = [{"type": "TEXT", "name": f"h{i}", "visible": False} for i in range(10)]
        inner = {"type": "FRAME", "name": "inner", "children": visible + hidden}
        section = self._make_section_root([inner])
        # inner has only 14 visible children <= 15
        assert count_nested_flat(section) == 0

    def test_group_type_counted_inside_section(self):
        """GROUP nodes inside section roots are counted."""
        children = [{"type": "RECTANGLE", "name": f"r{i}"} for i in range(16)]
        group = {"type": "GROUP", "name": "flat-group", "children": children}
        section = self._make_section_root([group])
        assert count_nested_flat(section) == 1

    def test_non_container_type_ignored(self):
        """TEXT/RECTANGLE nodes with children are not counted."""
        children = [{"type": "TEXT", "name": f"t{i}"} for i in range(20)]
        text_node = {"type": "TEXT", "name": "text-block", "children": children}
        section = self._make_section_root([text_node])
        assert count_nested_flat(section) == 0

    def test_custom_threshold(self):
        """Custom threshold parameter works within section root."""
        children = [{"type": "TEXT", "name": f"t{i}"} for i in range(6)]
        inner = {"type": "FRAME", "name": "inner", "children": children}
        section = self._make_section_root([inner])
        assert count_nested_flat(section, threshold=5) == 1
        assert count_nested_flat(section, threshold=6) == 0

    def test_deeply_nested_flat_inside_section(self):
        """Deeply nested flat frames inside section root are all counted."""
        leaf_children = [{"type": "TEXT", "name": f"t{i}"} for i in range(20)]
        deep = {"type": "FRAME", "name": "deep-flat", "children": leaf_children}
        mid_children = [deep] + [{"type": "TEXT", "name": f"m{i}"} for i in range(16)]
        mid = {"type": "FRAME", "name": "mid-flat", "children": mid_children}
        section = self._make_section_root([mid])
        # mid has 17 children (>15), deep has 20 children (>15)
        assert count_nested_flat(section) == 2


# ============================================================
# analyze-structure.sh: nested_flat_count metric (Issue 228)
# ============================================================
class TestAnalyzeStructureNestedFlat:
    def test_nested_flat_count_reported(self):
        """nested_flat_count appears in metrics output."""
        # Build a section root (width=1440) with a nested flat FRAME
        inner_children = [
            {"id": f"3:{i}", "type": "TEXT", "name": f"Text {i}",
             "absoluteBoundingBox": {"x": 0, "y": i * 30, "width": 100, "height": 20}}
            for i in range(20)
        ]
        data = {
            "node": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "section-hero",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1000},
                        "children": [
                            {
                                "id": "2:1", "type": "FRAME", "name": "FlatInner",
                                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 800, "height": 600},
                                "children": inner_children,
                            }
                        ],
                    }
                ],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("analyze-structure.sh", tmp)
            metrics = result["metrics"]
            # FlatInner has 20 children > 15 threshold
            assert "nested_flat_count" in metrics
            assert metrics["nested_flat_count"] >= 1
        finally:
            os.unlink(tmp)

    def test_nested_flat_does_not_affect_score(self):
        """nested_flat_count is informational only and does not change score."""
        # Two identical structures except one has a nested flat frame
        base_children = [
            {"id": f"3:{i}", "type": "TEXT", "name": f"Item {i}",
             "absoluteBoundingBox": {"x": 0, "y": i * 30, "width": 100, "height": 20}}
            for i in range(20)
        ]
        data_with_flat = {
            "node": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "section-hero",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1000},
                        "children": [
                            {
                                "id": "2:1", "type": "FRAME", "name": "FlatFrame",
                                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 800, "height": 600},
                                "children": base_children,
                            }
                        ],
                    }
                ],
            }
        }
        data_without_flat = {
            "node": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "section-hero",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1000},
                        "children": [
                            {
                                "id": "2:1", "type": "FRAME", "name": "SmallFrame",
                                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 800, "height": 600},
                                "children": base_children[:5],
                            }
                        ],
                    }
                ],
            }
        }
        tmp1 = write_fixture(data_with_flat)
        tmp2 = write_fixture(data_without_flat)
        try:
            r1 = run_script("analyze-structure.sh", tmp1)
            r2 = run_script("analyze-structure.sh", tmp2)
            assert r1["metrics"]["nested_flat_count"] > r2["metrics"]["nested_flat_count"]
            # Score should NOT differ due to nested_flat_count (it's informational only)
            # Note: scores may still differ due to flat_sections/ungrouped differences,
            # but nested_flat_count itself has no weight in the formula
            assert "nested_flat_count" not in str(r1.get("score_breakdown", {}))
        finally:
            os.unlink(tmp1)
            os.unlink(tmp2)

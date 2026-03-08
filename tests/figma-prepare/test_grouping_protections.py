"""Tests for grouping safety and suppression: protected nodes and over-grouping."""
import json
import os
import tempfile
import pytest

from helpers import run_script, write_fixture


# ============================================================
# Issue #221: Protected node (GROUP/COMPONENT/INSTANCE) preservation
# ============================================================
class TestProtectedNodeGrouping:
    """Verify that designer-intentional GROUPs and COMPONENTs are not decomposed."""

    def test_named_group_children_not_regrouped(self):
        """A named GROUP's children should not generate grouping candidates."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 3000},
                "children": [
                    {
                        "id": "1:1", "type": "GROUP", "name": "悩み",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 800},
                        "children": [
                            {"id": "2:1", "type": "TEXT", "name": "Text 1",
                             "absoluteBoundingBox": {"x": 10, "y": 10, "width": 200, "height": 30}},
                            {"id": "2:2", "type": "TEXT", "name": "Text 2",
                             "absoluteBoundingBox": {"x": 10, "y": 50, "width": 200, "height": 30}},
                            {"id": "2:3", "type": "TEXT", "name": "Text 3",
                             "absoluteBoundingBox": {"x": 10, "y": 90, "width": 200, "height": 30}},
                            {"id": "2:4", "type": "TEXT", "name": "Text 4",
                             "absoluteBoundingBox": {"x": 10, "y": 130, "width": 200, "height": 30}},
                        ],
                    },
                    {
                        "id": "1:2", "type": "FRAME", "name": "Section 2",
                        "absoluteBoundingBox": {"x": 0, "y": 1000, "width": 1440, "height": 1000},
                        "children": [
                            {"id": "3:1", "type": "TEXT", "name": "Title",
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
            # No candidates should have parent_id = "1:1" (the named GROUP "悩み")
            named_group_candidates = [c for c in candidates if c.get("parent_name") == "悩み"]
            assert len(named_group_candidates) == 0, \
                f"Named GROUP '悩み' should not have grouping candidates, got: {named_group_candidates}"
        finally:
            os.unlink(tmp)

    def test_unnamed_group_still_processed(self):
        """An auto-named GROUP (e.g. 'Group 1') should still be processed for grouping."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 3000},
                "children": [
                    {
                        "id": "1:1", "type": "GROUP", "name": "Group 1",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 800},
                        "children": [
                            {"id": "2:1", "type": "TEXT", "name": "Text 1",
                             "absoluteBoundingBox": {"x": 10, "y": 10, "width": 100, "height": 30}},
                            {"id": "2:2", "type": "TEXT", "name": "Text 2",
                             "absoluteBoundingBox": {"x": 10, "y": 50, "width": 100, "height": 30}},
                            {"id": "2:3", "type": "TEXT", "name": "Text 3",
                             "absoluteBoundingBox": {"x": 10, "y": 90, "width": 100, "height": 30}},
                            {"id": "2:4", "type": "TEXT", "name": "Text 4",
                             "absoluteBoundingBox": {"x": 10, "y": 130, "width": 100, "height": 30}},
                            {"id": "2:5", "type": "TEXT", "name": "Text 5",
                             "absoluteBoundingBox": {"x": 10, "y": 170, "width": 100, "height": 30}},
                            {"id": "2:6", "type": "TEXT", "name": "Text 6",
                             "absoluteBoundingBox": {"x": 10, "y": 210, "width": 100, "height": 30}},
                            {"id": "2:7", "type": "TEXT", "name": "Text 7",
                             "absoluteBoundingBox": {"x": 10, "y": 250, "width": 100, "height": 30}},
                            {"id": "2:8", "type": "TEXT", "name": "Text 8",
                             "absoluteBoundingBox": {"x": 10, "y": 290, "width": 100, "height": 30}},
                            {"id": "2:9", "type": "TEXT", "name": "Text 9",
                             "absoluteBoundingBox": {"x": 10, "y": 330, "width": 100, "height": 30}},
                            {"id": "2:10", "type": "TEXT", "name": "Text 10",
                             "absoluteBoundingBox": {"x": 10, "y": 370, "width": 100, "height": 30}},
                            {"id": "2:11", "type": "TEXT", "name": "Text 11",
                             "absoluteBoundingBox": {"x": 10, "y": 410, "width": 100, "height": 30}},
                            {"id": "2:12", "type": "TEXT", "name": "Text 12",
                             "absoluteBoundingBox": {"x": 10, "y": 450, "width": 100, "height": 30}},
                            {"id": "2:13", "type": "TEXT", "name": "Text 13",
                             "absoluteBoundingBox": {"x": 10, "y": 490, "width": 100, "height": 30}},
                            {"id": "2:14", "type": "TEXT", "name": "Text 14",
                             "absoluteBoundingBox": {"x": 10, "y": 530, "width": 100, "height": 30}},
                            {"id": "2:15", "type": "TEXT", "name": "Text 15",
                             "absoluteBoundingBox": {"x": 10, "y": 570, "width": 100, "height": 30}},
                            {"id": "2:16", "type": "TEXT", "name": "Text 16",
                             "absoluteBoundingBox": {"x": 10, "y": 610, "width": 100, "height": 30}},
                        ],
                    },
                ],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("detect-grouping-candidates.sh", tmp)
            candidates = result.get("candidates", [])
            # "Group 1" is auto-named, so its children should still be processed
            group1_candidates = [c for c in candidates if c.get("parent_name") == "Group 1"]
            assert len(group1_candidates) > 0, \
                "Auto-named GROUP 'Group 1' should still have grouping candidates"
        finally:
            os.unlink(tmp)

    def test_component_children_not_regrouped(self):
        """COMPONENT children should not generate grouping candidates."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 3000},
                "children": [
                    {
                        "id": "1:1", "type": "COMPONENT", "name": "Button",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 200, "height": 50},
                        "children": [
                            {"id": "2:1", "type": "RECTANGLE", "name": "Rectangle 1",
                             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 200, "height": 50}},
                            {"id": "2:2", "type": "TEXT", "name": "Label",
                             "absoluteBoundingBox": {"x": 10, "y": 10, "width": 180, "height": 30}},
                        ],
                    },
                    {
                        "id": "1:2", "type": "INSTANCE", "name": "Button Instance",
                        "absoluteBoundingBox": {"x": 0, "y": 100, "width": 200, "height": 50},
                        "children": [
                            {"id": "3:1", "type": "RECTANGLE", "name": "Rectangle 1",
                             "absoluteBoundingBox": {"x": 0, "y": 100, "width": 200, "height": 50}},
                            {"id": "3:2", "type": "TEXT", "name": "Label",
                             "absoluteBoundingBox": {"x": 10, "y": 110, "width": 180, "height": 30}},
                        ],
                    },
                ],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("detect-grouping-candidates.sh", tmp)
            candidates = result.get("candidates", [])
            # No candidates should have parent "Button" or "Button Instance"
            comp_candidates = [c for c in candidates
                               if c.get("parent_name") in ("Button", "Button Instance")]
            assert len(comp_candidates) == 0, \
                f"COMPONENT/INSTANCE children should not have grouping candidates, got: {comp_candidates}"
        finally:
            os.unlink(tmp)


# ============================================================
# Issue #222: Over-grouping suppression for non-root levels
# ============================================================
class TestOverGroupingSuppression:
    """Verify that non-root nodes with few children don't get over-grouped."""

    def test_few_children_no_proximity_grouping(self):
        """Non-root FRAME with < FLAT_THRESHOLD children should not get proximity groups."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 3000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Frame 1",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 800},
                        "children": [
                            {"id": "2:1", "type": "TEXT", "name": "Title",
                             "absoluteBoundingBox": {"x": 10, "y": 10, "width": 200, "height": 30}},
                            {"id": "2:2", "type": "RECTANGLE", "name": "Image",
                             "absoluteBoundingBox": {"x": 10, "y": 50, "width": 400, "height": 300}},
                            {"id": "2:3", "type": "TEXT", "name": "Description",
                             "absoluteBoundingBox": {"x": 10, "y": 360, "width": 400, "height": 60}},
                            {"id": "2:4", "type": "FRAME", "name": "Button",
                             "absoluteBoundingBox": {"x": 10, "y": 430, "width": 150, "height": 40},
                             "children": []},
                        ],
                    },
                ],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("detect-grouping-candidates.sh", tmp)
            candidates = result.get("candidates", [])
            # No proximity/pattern/spacing candidates should exist for "Frame 1"
            # because it has only 4 children (< FLAT_THRESHOLD=15)
            overgroup_candidates = [c for c in candidates
                                    if c.get("parent_name") == "Frame 1"
                                    and c.get("method") in ("proximity", "pattern", "spacing")]
            assert len(overgroup_candidates) == 0, \
                f"Non-root FRAME with few children should not have proximity/pattern groups, got: {overgroup_candidates}"
        finally:
            os.unlink(tmp)

"""Integration tests for prepare-sectioning-context.sh."""
import json
import os
import pytest
import tempfile

from helpers import run_script, write_fixture


class TestScriptIntegrationSectioning:
    """Tests that create temp fixtures and invoke prepare-sectioning-context.sh."""

    def test_instance_header_detection(self):
        """Issue 37: INSTANCE at top → header, COMPONENT at bottom → footer."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 5000},
            "children": [
                {"id": "1:1", "name": "Header Instance", "type": "INSTANCE",
                 "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 80},
                 "children": []},
                {"id": "1:2", "name": "Main Content", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 100, "width": 1440, "height": 4700},
                 "children": []},
                {"id": "1:3", "name": "Footer Component", "type": "COMPONENT",
                 "absoluteBoundingBox": {"x": 0, "y": 4850, "width": 1440, "height": 150},
                 "children": []},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("prepare-sectioning-context.sh", tmp)
            assert "1:1" in data["heuristic_hints"]["header_candidates"]
            assert "1:3" in data["heuristic_hints"]["footer_candidates"]
        finally:
            os.unlink(tmp)

    def test_childless_root(self):
        """Issue 59: childless root handled gracefully."""
        fixture = {
            "id": "0:1", "name": "Empty Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 0},
            "children": [],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("prepare-sectioning-context.sh", tmp)
            assert data["total_children"] == 0
            assert data["top_level_children"] == []
            assert data["heuristic_hints"]["header_candidates"] == []
        finally:
            os.unlink(tmp)

"""Tests for CTA detection, side panel detection, and related constants (Issues 185, 192, 193)."""
import json
import os
import pytest

from helpers import run_script, write_fixture

from figma_utils import (
    CTA_SQUARE_RATIO_MAX,
    CTA_SQUARE_RATIO_MIN,
    CTA_Y_THRESHOLD,
    EN_JP_PAIR_MAX_DISTANCE,
    EN_LABEL_MAX_WORDS,
    SIDE_PANEL_HEIGHT_RATIO,
    SIDE_PANEL_MAX_WIDTH,
)


# ============================================================
# Constants: CTA, Side Panel, EN+JP (Issues 185, 192, 193)
# ============================================================
class TestNewConstants185_192_193:
    def test_en_label_max_words(self):
        assert EN_LABEL_MAX_WORDS == 3

    def test_en_jp_pair_max_distance(self):
        assert EN_JP_PAIR_MAX_DISTANCE == 200

    def test_cta_square_ratio_min(self):
        assert CTA_SQUARE_RATIO_MIN == 0.8

    def test_cta_square_ratio_max(self):
        assert CTA_SQUARE_RATIO_MAX == 1.2

    def test_cta_y_threshold(self):
        assert CTA_Y_THRESHOLD == 100

    def test_side_panel_max_width(self):
        assert SIDE_PANEL_MAX_WIDTH == 80

    def test_side_panel_height_ratio(self):
        assert SIDE_PANEL_HEIGHT_RATIO == 3.0


# ============================================================
# generate-rename-map.sh integration: CTA detection (Issue 193)
# ============================================================
class TestGenerateRenameMapCTA:
    def test_cta_square_button(self):
        """Square CTA button at top-right with contact text -> cta-contact."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 5000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Frame 1",
                        "absoluteBoundingBox": {"x": 1250, "y": 10, "width": 156, "height": 156},
                        "children": [
                            {
                                "id": "1:2", "type": "TEXT", "name": "Text 1",
                                "characters": "お問い合わせ",
                                "absoluteBoundingBox": {"x": 1260, "y": 50, "width": 100, "height": 30},
                            }
                        ],
                    }
                ],
            }
        }
        path = write_fixture(data)
        try:
            result = run_script("generate-rename-map.sh", path)
            renames = result.get("renames", {})
            assert "1:1" in renames
            assert renames["1:1"]["new_name"].startswith("cta-")
            assert "contact" in renames["1:1"]["new_name"]
        finally:
            os.unlink(path)

    def test_non_square_not_cta(self):
        """Non-square button at top-right -> not CTA."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 5000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Frame 1",
                        "absoluteBoundingBox": {"x": 1250, "y": 10, "width": 300, "height": 50},
                        "children": [
                            {
                                "id": "1:2", "type": "TEXT", "name": "Text 1",
                                "characters": "お問い合わせ",
                                "absoluteBoundingBox": {"x": 1260, "y": 20, "width": 100, "height": 30},
                            }
                        ],
                    }
                ],
            }
        }
        path = write_fixture(data)
        try:
            result = run_script("generate-rename-map.sh", path)
            renames = result.get("renames", {})
            if "1:1" in renames:
                assert not renames["1:1"]["new_name"].startswith("cta-")
        finally:
            os.unlink(path)


# ============================================================
# generate-rename-map.sh integration: Side panel (Issue 192)
# ============================================================
class TestGenerateRenameMapSidePanel:
    def test_side_panel_right_edge(self):
        """Narrow vertical frame at right edge -> side-panel-*."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 5000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Frame 52",
                        "absoluteBoundingBox": {"x": 1379, "y": 500, "width": 42, "height": 268},
                        "children": [
                            {
                                "id": "1:2", "type": "VECTOR", "name": "Vector 1",
                                "absoluteBoundingBox": {"x": 1385, "y": 510, "width": 20, "height": 20},
                            }
                        ],
                    }
                ],
            }
        }
        path = write_fixture(data)
        try:
            result = run_script("generate-rename-map.sh", path)
            renames = result.get("renames", {})
            assert "1:1" in renames
            assert renames["1:1"]["new_name"].startswith("side-panel-")
        finally:
            os.unlink(path)

    def test_wide_frame_not_side_panel(self):
        """Wide frame at edge -> not side panel."""
        data = {
            "document": {
                "id": "0:1", "type": "FRAME", "name": "Page",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 5000},
                "children": [
                    {
                        "id": "1:1", "type": "FRAME", "name": "Frame 1",
                        "absoluteBoundingBox": {"x": 1300, "y": 500, "width": 120, "height": 268},
                        "children": [
                            {
                                "id": "1:2", "type": "TEXT", "name": "Text 1",
                                "characters": "test",
                                "absoluteBoundingBox": {"x": 1310, "y": 510, "width": 100, "height": 30},
                            }
                        ],
                    }
                ],
            }
        }
        path = write_fixture(data)
        try:
            result = run_script("generate-rename-map.sh", path)
            renames = result.get("renames", {})
            if "1:1" in renames:
                assert not renames["1:1"]["new_name"].startswith("side-panel-")
        finally:
            os.unlink(path)

"""Integration tests for generate-rename-map.sh."""
import json
import os
import pytest
import tempfile

from helpers import run_script, write_fixture


class TestScriptIntegrationRename:
    """Tests that create temp fixtures and invoke generate-rename-map.sh."""

    def test_fills_empty_no_crash(self):
        """Issue 32: fills=[] should not crash generate-rename-map.sh."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1000},
            "children": [{
                "id": "1:1", "name": "Frame 1", "type": "FRAME",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 800, "height": 400},
                "children": [
                    {"id": "1:2", "name": "Rectangle 1", "type": "RECTANGLE",
                     "absoluteBoundingBox": {"x": 0, "y": 0, "width": 800, "height": 200},
                     "fills": [], "children": []},
                    {"id": "1:3", "name": "Text 1", "type": "TEXT",
                     "absoluteBoundingBox": {"x": 0, "y": 200, "width": 800, "height": 50},
                     "children": []},
                    {"id": "1:4", "name": "Frame 2", "type": "FRAME",
                     "absoluteBoundingBox": {"x": 0, "y": 250, "width": 200, "height": 50},
                     "children": [{"id": "1:5", "name": "Button", "type": "TEXT",
                                   "absoluteBoundingBox": {"x": 0, "y": 0, "width": 100, "height": 30},
                                   "children": []}]},
                ],
            }],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("generate-rename-map.sh", tmp)
            assert "error" not in data
        finally:
            os.unlink(tmp)

    def test_characters_field_preference(self):
        """Issue 38: characters field preferred over name for TEXT nodes."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1000},
            "children": [
                {"id": "1:1", "name": "Text 1", "type": "TEXT",
                 "absoluteBoundingBox": {"x": 0, "y": 0, "width": 200, "height": 30},
                 "characters": "お問い合わせ", "children": []},
                {"id": "1:2", "name": "Frame 1", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 100, "width": 400, "height": 200},
                 "children": [
                     {"id": "1:3", "name": "Text 2", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 0, "y": 0, "width": 200, "height": 30},
                      "characters": "募集要項", "children": []},
                     {"id": "1:4", "name": "Text 3", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 0, "y": 40, "width": 200, "height": 30},
                      "characters": "REASON", "children": []},
                 ]},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("generate-rename-map.sh", tmp)
            renames = data.get("renames", {})
            r1 = renames.get("1:1", {})
            # Issue 170: お問い合わせ → contact via JP_KEYWORD_MAP
            assert "contact" in r1.get("new_name", ""), \
                f"Expected 'contact' in {r1.get('new_name', '')}"
            r2 = renames.get("1:2", {})
            name = r2.get("new_name", "")
            # Issue 170: 募集要項 → recruit via JP_KEYWORD_MAP, or REASON → reason
            assert "recruit" in name or "reason" in name or "heading" in name, \
                f"Expected 'recruit'/'reason'/'heading' in {name}"
        finally:
            os.unlink(tmp)

    def test_image_wrapper_card_detection(self):
        """Image wrapped in sub-frame + TEXT caption should be card-*, not heading-*."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1000},
            "children": [
                # Menu item: FRAME containing [FRAME(with rectangles), TEXT]
                # This pattern is common for food/product cards with image + caption
                {"id": "1:1", "name": "Frame 1", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 0, "width": 250, "height": 245},
                 "children": [
                     # Image wrapper frame with rectangles (photo overlays)
                     {"id": "1:2", "name": "Group 1", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 0, "y": 0, "width": 230, "height": 173},
                      "children": [
                          {"id": "1:3", "name": "Rectangle 1", "type": "RECTANGLE",
                           "absoluteBoundingBox": {"x": 0, "y": 0, "width": 230, "height": 173},
                           "children": []},
                          {"id": "1:4", "name": "Rectangle 2", "type": "RECTANGLE",
                           "absoluteBoundingBox": {"x": 10, "y": 10, "width": 210, "height": 153},
                           "children": []},
                      ]},
                     # Caption text
                     {"id": "1:5", "name": "Text 1", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 0, "y": 180, "width": 230, "height": 40},
                      "characters": "finger food",
                      "children": []},
                 ]},
                # Second card item with different text
                {"id": "2:1", "name": "Frame 2", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 260, "y": 0, "width": 250, "height": 245},
                 "children": [
                     {"id": "2:2", "name": "Group 2", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 0, "y": 0, "width": 230, "height": 173},
                      "children": [
                          {"id": "2:3", "name": "Rectangle 3", "type": "RECTANGLE",
                           "absoluteBoundingBox": {"x": 0, "y": 0, "width": 230, "height": 173},
                           "children": []},
                      ]},
                     {"id": "2:4", "name": "Text 2", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 0, "y": 180, "width": 230, "height": 40},
                      "characters": "catering service",
                      "children": []},
                 ]},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("generate-rename-map.sh", tmp)
            renames = data.get("renames", {})
            # Frame 1 (image-wrapper + text) must be card-*, not heading-*
            r1 = renames.get("1:1", {})
            assert r1.get("new_name", "").startswith("card-"), \
                f"Expected card-* for image-wrapper+text, got: {r1.get('new_name', '')}"
            # Frame 2 similarly
            r2 = renames.get("2:1", {})
            assert r2.get("new_name", "").startswith("card-"), \
                f"Expected card-* for image-wrapper+text, got: {r2.get('new_name', '')}"
            # Verify the card slug uses text content
            assert "finger-food" in r1["new_name"], \
                f"Expected slug from text content, got: {r1['new_name']}"
            assert "catering-service" in r2["new_name"], \
                f"Expected slug from text content, got: {r2['new_name']}"
        finally:
            os.unlink(tmp)

    def test_semantic_group_naming_from_child_text(self):
        """Issue 174: group-N / container-N should use semantic slug from child text."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 3000},
            "children": [
                # FRAME with 4 child FRAMEs, each with TEXT children (Japanese)
                # This should get group-{slug} instead of group-0
                {"id": "1:1", "name": "Frame 1", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 100, "y": 100, "width": 600, "height": 800},
                 "children": [
                     {"id": "1:10", "name": "Frame 10", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 100, "y": 100, "width": 500, "height": 180},
                      "children": [
                          {"id": "1:11", "name": "Text 1", "type": "TEXT",
                           "absoluteBoundingBox": {"x": 110, "y": 110, "width": 200, "height": 30},
                           "characters": "サービスについて", "children": []},
                      ]},
                     {"id": "1:20", "name": "Frame 11", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 100, "y": 300, "width": 500, "height": 180},
                      "children": [
                          {"id": "1:21", "name": "Text 2", "type": "TEXT",
                           "absoluteBoundingBox": {"x": 110, "y": 310, "width": 200, "height": 30},
                           "characters": "詳しくはこちら", "children": []},
                      ]},
                     {"id": "1:30", "name": "Frame 12", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 100, "y": 500, "width": 500, "height": 180},
                      "children": [
                          {"id": "1:31", "name": "Text 3", "type": "TEXT",
                           "absoluteBoundingBox": {"x": 110, "y": 510, "width": 200, "height": 30},
                           "characters": "お問い合わせ", "children": []},
                      ]},
                     {"id": "1:40", "name": "Frame 13", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 100, "y": 700, "width": 500, "height": 180},
                      "children": [
                          {"id": "1:41", "name": "Text 4", "type": "TEXT",
                           "absoluteBoundingBox": {"x": 110, "y": 710, "width": 200, "height": 30},
                           "characters": "料金プラン", "children": []},
                      ]},
                 ]},
                # FRAME with 6+ child FRAMEs -> container-{slug}
                {"id": "2:1", "name": "Frame 2", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 100, "y": 1000, "width": 600, "height": 1200},
                 "children": [
                     {"id": f"2:{10+i}", "name": f"Frame {20+i}", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 100, "y": 1000 + i * 180, "width": 500, "height": 160},
                      "children": [
                          {"id": f"2:{50+i}", "name": f"Text {10+i}", "type": "TEXT",
                           "absoluteBoundingBox": {"x": 110, "y": 1010 + i * 180, "width": 200, "height": 30},
                           "characters": "ケータリング" if i == 0 else f"Item {i}",
                           "children": []},
                      ]}
                     for i in range(6)
                 ]},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("generate-rename-map.sh", tmp)
            renames = data.get("renames", {})
            # 1:1 has 4 children, each with JP text -> should be group-{slug}
            r1 = renames.get("1:1", {})
            name1 = r1.get("new_name", "")
            assert name1.startswith("group-"), \
                f"Expected group-* for 4-child frame, got: {name1}"
            # Must NOT end with numeric index -- should have semantic slug
            assert not name1.split("-")[-1].isdigit(), \
                f"Expected semantic slug, not numeric index: {name1}"
            # Should contain 'service' from 'サービスについて' (first text child)
            assert "service" in name1, \
                f"Expected 'service' slug from 'サービスについて', got: {name1}"

            # 2:1 has 6 children -> should be container-{slug}
            r2 = renames.get("2:1", {})
            name2 = r2.get("new_name", "")
            assert name2.startswith("container-"), \
                f"Expected container-* for 6-child frame, got: {name2}"
            # Must have semantic slug, not numeric
            assert not name2.split("-")[-1].isdigit(), \
                f"Expected semantic slug, not numeric index: {name2}"
            # Should contain 'catering' from 'ケータリング' (first grandchild text)
            assert "catering" in name2, \
                f"Expected 'catering' slug from 'ケータリング', got: {name2}"
        finally:
            os.unlink(tmp)

    def test_semantic_group_naming_fallback_to_index(self):
        """Issue 174: group-N fallback when no text content is available."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
            "children": [
                # FRAME with 4 child FRAMEs, none with TEXT → falls back to group-N
                {"id": "1:1", "name": "Frame 1", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 100, "y": 100, "width": 600, "height": 800},
                 "children": [
                     {"id": f"1:{10+i}", "name": f"Frame {10+i}", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 100, "y": 100 + i * 200, "width": 500, "height": 180},
                      "children": [
                          {"id": f"1:{20+i}", "name": f"Rectangle {i}", "type": "RECTANGLE",
                           "absoluteBoundingBox": {"x": 110, "y": 110 + i * 200, "width": 200, "height": 150},
                           "children": []},
                      ]}
                     for i in range(4)
                 ]},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("generate-rename-map.sh", tmp)
            renames = data.get("renames", {})
            r1 = renames.get("1:1", {})
            name1 = r1.get("new_name", "")
            # No text children → should fall back to group-{index}
            assert name1.startswith("group-"), \
                f"Expected group-* fallback, got: {name1}"
            assert name1 == "group-0", \
                f"Expected group-0 (numeric fallback), got: {name1}"
        finally:
            os.unlink(tmp)

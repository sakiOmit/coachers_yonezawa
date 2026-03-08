"""Integration tests for detect-grouping-candidates.sh and enrich-metadata.sh."""
import json
import os
import pytest
import tempfile

from helpers import run_script, write_fixture


class TestScriptIntegrationGrouping:
    """Tests that create temp fixtures and invoke grouping/enrichment scripts."""

    def test_yaml_structure_hash_key(self):
        """Issue 41: YAML output uses structure_hash key, not pattern."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
            "children": [
                {"id": f"1:{i}", "name": f"Frame {i}", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": i * 300, "width": 300, "height": 200},
                 "children": [
                     {"id": f"1:{i}0", "name": f"Text {i}", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 0, "y": 0, "width": 200, "height": 30},
                      "children": []},
                 ]}
                for i in range(1, 4)
            ],
        }
        tmp = write_fixture(fixture)
        yaml_path = tmp + ".yaml"
        try:
            run_script("detect-grouping-candidates.sh", tmp, "--output", yaml_path)
            with open(yaml_path) as f:
                content = f.read()
            assert "structure_hash:" in content
            assert "pattern:" not in content
        finally:
            os.unlink(tmp)
            if os.path.exists(yaml_path):
                os.unlink(yaml_path)

    def test_empty_enrichment(self):
        """Issue 58: empty enrichment handled gracefully."""
        metadata = {
            "id": "0:1", "name": "Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1000},
            "children": [{"id": "1:1", "name": "Child", "type": "FRAME",
                          "absoluteBoundingBox": {"x": 0, "y": 0, "width": 100, "height": 100},
                          "children": []}],
        }
        meta_tmp = write_fixture(metadata)
        enrich_tmp = write_fixture({})
        out_tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
        try:
            data = run_script("enrich-metadata.sh", meta_tmp, enrich_tmp, "--output", out_tmp)
            assert data["enriched_nodes"] == 0
            with open(out_tmp) as f:
                assert json.load(f)["id"] == "0:1"
        finally:
            for p in (meta_tmp, enrich_tmp, out_tmp):
                if os.path.exists(p):
                    os.unlink(p)

    def test_dedup_partial_overlap_preserves_nodes(self):
        """Issue 236: Partial overlap should trim, not delete entire candidate.

        Setup: A section with 3 cards (semantic:card-list) followed by 3 pattern
        elements that share the last card's node ID. After dedup, the non-overlapping
        pattern nodes should still be covered by a trimmed candidate.
        """
        # Create a flat structure with 20+ children to trigger pattern detection:
        # - 3 card-like FRAMEs (img+text) → semantic:card-list {c0, c1, c2}
        # - c2 is also structurally similar to pattern items p0, p1
        # - pattern items p0, p1, c2 share structure → pattern {c2, p0, p1}
        # After dedup, p0 and p1 must NOT be orphaned.
        cards = []
        for i in range(3):
            cards.append({
                "id": f"card:{i}", "name": f"Frame {i}", "type": "FRAME",
                "absoluteBoundingBox": {"x": i * 400, "y": 100, "width": 350, "height": 400},
                "children": [
                    {"id": f"card:{i}:img", "name": f"Rectangle {i}", "type": "RECTANGLE",
                     "absoluteBoundingBox": {"x": i * 400, "y": 100, "width": 350, "height": 200}},
                    {"id": f"card:{i}:txt", "name": f"Text {i}", "type": "TEXT",
                     "absoluteBoundingBox": {"x": i * 400, "y": 310, "width": 350, "height": 40},
                     "characters": f"Card Title {i}"},
                ],
            })
        # Add extra pattern items structurally similar to cards
        extra_patterns = []
        for i in range(3, 6):
            extra_patterns.append({
                "id": f"card:{i}", "name": f"Frame {i}", "type": "FRAME",
                "absoluteBoundingBox": {"x": (i - 3) * 400, "y": 600, "width": 350, "height": 400},
                "children": [
                    {"id": f"card:{i}:img", "name": f"Rectangle {i}", "type": "RECTANGLE",
                     "absoluteBoundingBox": {"x": (i - 3) * 400, "y": 600, "width": 350, "height": 200}},
                    {"id": f"card:{i}:txt", "name": f"Text {i}", "type": "TEXT",
                     "absoluteBoundingBox": {"x": (i - 3) * 400, "y": 810, "width": 350, "height": 40},
                     "characters": f"Item Title {i}"},
                ],
            })
        # Padding elements to reach flat_threshold (15)
        fillers = []
        for i in range(9):
            fillers.append({
                "id": f"fill:{i}", "name": f"Line {i}", "type": "LINE",
                "absoluteBoundingBox": {"x": 0, "y": 1100 + i * 100, "width": 1440, "height": 1},
            })
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 3000},
            "children": cards + extra_patterns + fillers,
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("detect-grouping-candidates.sh", tmp)
            candidates = data.get("candidates", [])
            # Collect all covered node IDs
            all_covered = set()
            for c in candidates:
                all_covered.update(c.get("node_ids", []))
            # All card/pattern frame IDs should be covered (no orphans)
            frame_ids = {f"card:{i}" for i in range(6)}
            orphaned = frame_ids - all_covered
            assert len(orphaned) == 0, (
                f"Issue 236: nodes {orphaned} orphaned after dedup. "
                f"Covered: {all_covered & frame_ids}"
            )
        finally:
            os.unlink(tmp)

    def test_semantic_detection(self):
        """Area 3: Card + nav detection, semantic method, dedup."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
            "children": [
                {"id": "1:1", "name": "Cards Section", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 600},
                 "children": [
                     {"id": f"1:{10+i}", "name": f"Card {i}", "type": "FRAME",
                      "absoluteBoundingBox": {"x": i * 400, "y": 0, "width": 350, "height": 400},
                      "children": [
                          {"id": f"1:{20+i}", "name": f"img {i}", "type": "RECTANGLE",
                           "absoluteBoundingBox": {"x": i * 400, "y": 0, "width": 350, "height": 200}},
                          {"id": f"1:{30+i}", "name": f"text {i}", "type": "TEXT",
                           "absoluteBoundingBox": {"x": i * 400, "y": 210, "width": 350, "height": 40},
                           "characters": f"Card Title {i}"},
                      ]}
                     for i in range(3)
                 ]},
                {"id": "2:1", "name": "Nav Section", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 700, "width": 1440, "height": 60},
                 "children": [
                     {"id": f"2:{10+i}", "name": f"Link {i}", "type": "TEXT",
                      "absoluteBoundingBox": {"x": i * 150, "y": 700, "width": 120, "height": 40},
                      "characters": f"Menu {i}"}
                     for i in range(5)
                 ]},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("detect-grouping-candidates.sh", tmp)
            methods = {c.get("method", "") for c in data.get("candidates", [])}
            cards = [c for c in data["candidates"]
                     if c.get("method") == "semantic" and c.get("semantic_type") == "card-list"]
            navs = [c for c in data["candidates"]
                    if c.get("method") == "semantic" and c.get("semantic_type") == "navigation"]
            assert len(cards) >= 1
            assert len(navs) >= 1
            assert "semantic" in methods
            assert "page-kv" not in methods
            assert data["total"] >= 2
        finally:
            os.unlink(tmp)

    def test_detect_header_footer_groups(self):
        """Issue 85: Header/footer group detection from flat elements."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 5000},
            "children": [
                {"id": "1:1", "name": "Vector", "type": "VECTOR",
                 "absoluteBoundingBox": {"x": 50, "y": 20, "width": 100, "height": 30}},
                *[{"id": f"1:{10+i}", "name": f"Nav {i}", "type": "TEXT",
                   "absoluteBoundingBox": {"x": 300 + i * 150, "y": 25, "width": 120, "height": 20},
                   "characters": f"Menu {i}"} for i in range(6)],
                {"id": "1:20", "name": "Frame 1", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 80},
                 "children": [
                     {"id": "1:21", "name": "Sub 1", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 200, "y": 10, "width": 100, "height": 20}},
                     {"id": "1:22", "name": "Sub 2", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 400, "y": 10, "width": 100, "height": 20}},
                 ]},
                {"id": "2:1", "name": "Main Content", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 400, "width": 1440, "height": 3000},
                 "children": [{"id": "2:2", "name": "Text 1", "type": "TEXT",
                                "absoluteBoundingBox": {"x": 50, "y": 400, "width": 500, "height": 40}}]},
                {"id": "3:1", "name": "Line 1", "type": "LINE",
                 "absoluteBoundingBox": {"x": 0, "y": 4800, "width": 1440, "height": 1}},
                {"id": "3:2", "name": "Footer Text", "type": "TEXT",
                 "absoluteBoundingBox": {"x": 50, "y": 4850, "width": 300, "height": 20},
                 "characters": "Copyright 2024"},
                {"id": "3:3", "name": "Footer Links", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 4900, "width": 1440, "height": 80},
                 "children": [{"id": "3:4", "name": "Link 1", "type": "TEXT",
                                "absoluteBoundingBox": {"x": 50, "y": 4900, "width": 100, "height": 20}}]},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("detect-grouping-candidates.sh", tmp)
            header = [c for c in data["candidates"] if c.get("semantic_type") == "header"]
            footer = [c for c in data["candidates"] if c.get("semantic_type") == "footer"]
            assert len(header) >= 1
            assert "1:1" in header[0]["node_ids"]
            assert len(footer) >= 1
            for c in header + footer:
                assert "2:1" not in c.get("node_ids", [])
        finally:
            os.unlink(tmp)

    def test_already_named_header_footer_excluded(self):
        """Issue 85: Already-named HEADER/FOOTER should not be re-grouped."""
        fixture = {
            "id": "0:1", "name": "Test", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 3000},
            "children": [
                {"id": "1:1", "name": "HEADER", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 80},
                 "children": []},
                {"id": "2:1", "name": "Content", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 80, "width": 1440, "height": 2800},
                 "children": []},
                {"id": "3:1", "name": "FOOTER", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 2880, "width": 1440, "height": 120},
                 "children": []},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("detect-grouping-candidates.sh", tmp)
            hf = [c for c in data["candidates"]
                  if c.get("semantic_type") in ("header", "footer")]
            assert len(hf) == 0
        finally:
            os.unlink(tmp)

    def test_infer_zone_semantic_name(self):
        """Issue 91: Zone names should be semantic, not generic 'section'."""
        fixture = {
            "id": "1:1", "name": "Artboard", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 4500},
            "children": [
                {"id": "2:1", "name": "Rectangle 1", "type": "RECTANGLE",
                 "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 600}},
                {"id": "2:2", "name": "Text 1", "type": "TEXT", "characters": "Welcome",
                 "absoluteBoundingBox": {"x": 100, "y": 200, "width": 400, "height": 60}},
                *[{"id": f"2:{3+i}", "name": f"Frame {2+i}", "type": "FRAME",
                   "absoluteBoundingBox": {"x": 100 + i * 400, "y": 800, "width": 350, "height": 400},
                   "children": [
                       {"id": f"3:{1+i*2}", "type": "RECTANGLE", "name": f"Image {i+1}",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 350, "height": 200}},
                       {"id": f"3:{2+i*2}", "type": "TEXT", "name": f"Title {i+1}",
                        "characters": f"Card {i+1}",
                        "absoluteBoundingBox": {"x": 0, "y": 210, "width": 350, "height": 30}},
                   ]} for i in range(3)],
                *[{"id": f"2:{6+i}", "name": f"Text {2+i}", "type": "TEXT",
                   "characters": name,
                   "absoluteBoundingBox": {"x": 100 + i * 100, "y": 1500, "width": 60, "height": 20}}
                  for i, name in enumerate(["Home", "About", "Service", "Contact", "FAQ"])],
                {"id": "2:11", "name": "Text 7", "type": "TEXT", "characters": "Description",
                 "absoluteBoundingBox": {"x": 100, "y": 2000, "width": 600, "height": 100}},
                {"id": "2:12", "name": "Frame 5", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 100, "y": 2100, "width": 600, "height": 200},
                 "children": [
                     {"id": "3:7", "type": "TEXT", "name": "Sub", "characters": "Sub text",
                      "absoluteBoundingBox": {"x": 0, "y": 0, "width": 300, "height": 30}},
                 ]},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("detect-grouping-candidates.sh", tmp)
            zone_candidates = [c for c in data.get("candidates", []) if c.get("method") == "zone"]
            assert len(zone_candidates) >= 1
            generic = [c for c in zone_candidates if c.get("suggested_name") == "section"]
            assert len(generic) == 0, f"Generic names found: {[c['suggested_name'] for c in zone_candidates]}"
            for c in zone_candidates:
                name = c.get("suggested_name", "")
                assert name.startswith("section-")
                assert len(name) > len("section-")
        finally:
            os.unlink(tmp)

    def test_consecutive_pattern_detection(self):
        """Issue 165: 3 consecutive similar frames grouped at root level."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 5000},
            "children": [
                {"id": "1:1", "name": "HEADER", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 80},
                 "children": []},
                # 3 consecutive similar frames (each has FRAME + TEXT child)
                {"id": "2:1", "name": "section-menu-1", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 200, "width": 1440, "height": 600},
                 "children": [
                     {"id": "2:10", "name": "Frame 1", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 0, "y": 0, "width": 500, "height": 400}},
                     {"id": "2:11", "name": "Text 1", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 0, "y": 400, "width": 500, "height": 40},
                      "characters": "Menu 1"},
                 ]},
                {"id": "2:2", "name": "section-menu-2", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 820, "width": 1440, "height": 600},
                 "children": [
                     {"id": "2:20", "name": "Frame 2", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 0, "y": 0, "width": 500, "height": 400}},
                     {"id": "2:21", "name": "Text 2", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 0, "y": 400, "width": 500, "height": 40},
                      "characters": "Menu 2"},
                 ]},
                {"id": "2:3", "name": "section-menu-3", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 1440, "width": 1440, "height": 600},
                 "children": [
                     {"id": "2:30", "name": "Frame 3", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 0, "y": 0, "width": 500, "height": 400}},
                     {"id": "2:31", "name": "Text 3", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 0, "y": 400, "width": 500, "height": 40},
                      "characters": "Menu 3"},
                 ]},
                {"id": "3:1", "name": "FOOTER", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 4800, "width": 1440, "height": 200},
                 "children": []},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("detect-grouping-candidates.sh", tmp)
            consecutive = [c for c in data["candidates"] if c.get("method") == "consecutive"]
            assert len(consecutive) >= 1, \
                f"No consecutive groups found. Methods: {[c['method'] for c in data['candidates']]}"
            # All 3 menu frames should be in the group
            group_ids = set(consecutive[0]["node_ids"])
            assert "2:1" in group_ids
            assert "2:2" in group_ids
            assert "2:3" in group_ids
            # Suggested name should be list-based
            assert consecutive[0]["suggested_name"].startswith("list-")
        finally:
            os.unlink(tmp)

    def test_heading_content_pair_detection(self):
        """Issue 166: Small heading frame + large content frame paired."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 5000},
            "children": [
                {"id": "1:1", "name": "HEADER", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 80},
                 "children": []},
                # Heading frame (small, text-heavy; TEXT >= ELLIPSE per Issue 175)
                {"id": "2:1", "name": "section-our-concept", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 200, "width": 1440, "height": 215},
                 "children": [
                     {"id": "2:10", "name": "Text 1", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 200, "y": 50, "width": 400, "height": 60},
                      "characters": "OUR CONCEPT"},
                     {"id": "2:13", "name": "Text 2", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 200, "y": 120, "width": 400, "height": 30},
                      "characters": "Our philosophy"},
                     {"id": "2:11", "name": "Ellipse 1", "type": "ELLIPSE",
                      "absoluteBoundingBox": {"x": 300, "y": 160, "width": 10, "height": 10}},
                     {"id": "2:12", "name": "Ellipse 2", "type": "ELLIPSE",
                      "absoluteBoundingBox": {"x": 320, "y": 160, "width": 10, "height": 10}},
                 ]},
                # Content frame (large, complex)
                {"id": "2:2", "name": "section-concept-detail", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 415, "width": 1440, "height": 746},
                 "children": [
                     {"id": "2:20", "name": "Text 2", "type": "TEXT",
                      "absoluteBoundingBox": {"x": 100, "y": 50, "width": 800, "height": 200},
                      "characters": "Detail text"},
                     {"id": "2:21", "name": "Frame 1", "type": "FRAME",
                      "absoluteBoundingBox": {"x": 100, "y": 300, "width": 600, "height": 300},
                      "children": [
                          {"id": "2:22", "name": "Tag 1", "type": "TEXT",
                           "absoluteBoundingBox": {"x": 0, "y": 0, "width": 100, "height": 30},
                           "characters": "Tag"},
                      ]},
                 ]},
                {"id": "3:1", "name": "FOOTER", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 4800, "width": 1440, "height": 200},
                 "children": []},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("detect-grouping-candidates.sh", tmp)
            hc_pairs = [c for c in data["candidates"] if c.get("method") == "heading-content"]
            assert len(hc_pairs) >= 1, \
                f"No heading-content pairs found. Methods: {[c['method'] for c in data['candidates']]}"
            pair_ids = set(hc_pairs[0]["node_ids"])
            assert "2:1" in pair_ids, "Heading not in pair"
            assert "2:2" in pair_ids, "Content not in pair"
            # Suggested name should contain concept slug
            assert "section-" in hc_pairs[0]["suggested_name"]
        finally:
            os.unlink(tmp)

    def test_loose_element_absorption(self):
        """Issue 167: LINE dividers absorbed into nearest group."""
        fixture = {
            "id": "0:1", "name": "Test Page", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 5000},
            "children": [
                # Three consecutive similar frames (will form a consecutive group)
                {"id": "2:1", "name": "section-menu-1", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 600},
                 "children": [
                     {"id": "2:10", "type": "FRAME", "name": "F1",
                      "absoluteBoundingBox": {"x": 0, "y": 0, "width": 400, "height": 400}},
                     {"id": "2:11", "type": "TEXT", "name": "T1",
                      "absoluteBoundingBox": {"x": 0, "y": 400, "width": 400, "height": 40},
                      "characters": "Item 1"},
                 ]},
                # Loose LINE divider between menu-1 and menu-2
                {"id": "9:1", "name": "divider-1", "type": "LINE",
                 "absoluteBoundingBox": {"x": 0, "y": 610, "width": 1440, "height": 1}},
                {"id": "2:2", "name": "section-menu-2", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 620, "width": 1440, "height": 600},
                 "children": [
                     {"id": "2:20", "type": "FRAME", "name": "F2",
                      "absoluteBoundingBox": {"x": 0, "y": 0, "width": 400, "height": 400}},
                     {"id": "2:21", "type": "TEXT", "name": "T2",
                      "absoluteBoundingBox": {"x": 0, "y": 400, "width": 400, "height": 40},
                      "characters": "Item 2"},
                 ]},
                # Another loose divider
                {"id": "9:2", "name": "divider-2", "type": "LINE",
                 "absoluteBoundingBox": {"x": 0, "y": 1230, "width": 1440, "height": 1}},
                {"id": "2:3", "name": "section-menu-3", "type": "FRAME",
                 "absoluteBoundingBox": {"x": 0, "y": 1240, "width": 1440, "height": 600},
                 "children": [
                     {"id": "2:30", "type": "FRAME", "name": "F3",
                      "absoluteBoundingBox": {"x": 0, "y": 0, "width": 400, "height": 400}},
                     {"id": "2:31", "type": "TEXT", "name": "T3",
                      "absoluteBoundingBox": {"x": 0, "y": 400, "width": 400, "height": 40},
                      "characters": "Item 3"},
                 ]},
            ],
        }
        tmp = write_fixture(fixture)
        try:
            data = run_script("detect-grouping-candidates.sh", tmp)
            # Check that dividers were absorbed into a group
            all_grouped_ids = set()
            for c in data["candidates"]:
                all_grouped_ids.update(c.get("node_ids", []))
            # At least one divider should be absorbed
            divider_absorbed = "9:1" in all_grouped_ids or "9:2" in all_grouped_ids
            assert divider_absorbed, \
                f"No dividers absorbed. Grouped IDs: {all_grouped_ids}"
        finally:
            os.unlink(tmp)

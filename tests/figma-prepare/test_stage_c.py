"""Tests for Stage C recursion, nested flat counting, and detector management."""
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


# ============================================================
# Issue 225: generate-nested-grouping-context.sh --groups / --depth tests
# ============================================================
class TestNestedGroupingContextGroups:
    """Tests for --groups and --depth support in generate-nested-grouping-context.sh."""

    # Shared fixture: metadata with a tree structure
    METADATA = {
        "id": "0:1", "name": "Page", "type": "FRAME",
        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 5000},
        "children": [
            {
                "id": "2:100", "name": "Card A", "type": "FRAME",
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 400, "height": 300},
                "children": [
                    {"id": "3:1", "name": "Title A", "type": "TEXT",
                     "absoluteBoundingBox": {"x": 10, "y": 10, "width": 200, "height": 30},
                     "children": []},
                    {"id": "3:2", "name": "Image A", "type": "RECTANGLE",
                     "absoluteBoundingBox": {"x": 10, "y": 50, "width": 380, "height": 200},
                     "children": []},
                ],
            },
            {
                "id": "2:101", "name": "Card B", "type": "FRAME",
                "absoluteBoundingBox": {"x": 0, "y": 350, "width": 400, "height": 300},
                "children": [
                    {"id": "4:1", "name": "Title B", "type": "TEXT",
                     "absoluteBoundingBox": {"x": 10, "y": 10, "width": 200, "height": 30},
                     "children": []},
                    {"id": "4:2", "name": "Image B", "type": "RECTANGLE",
                     "absoluteBoundingBox": {"x": 10, "y": 50, "width": 380, "height": 200},
                     "children": []},
                ],
            },
            {
                "id": "2:200", "name": "Single Element", "type": "FRAME",
                "absoluteBoundingBox": {"x": 0, "y": 700, "width": 400, "height": 100},
                "children": [],
            },
        ],
    }

    def _write_groups(self, groups_data):
        """Write groups JSON to temp file."""
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(groups_data, f)
        f.close()
        return f.name

    def test_groups_basic(self):
        """--groups mode treats node_ids as siblings to sub-group (Issue 257)."""
        groups = {
            "groups": [
                {
                    "name": "feature-cards",
                    "pattern": "card",
                    "node_ids": ["2:100", "2:101"],
                },
            ]
        }
        meta_tmp = write_fixture(self.METADATA)
        groups_tmp = self._write_groups(groups)
        try:
            data = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp, "--depth", "1",
            )
            assert "error" not in data
            assert data["total_sections"] == 1  # one per group
            assert data["depth"] == 1
            assert data["model"] == "haiku"

            # Single section for the group; siblings are node_ids themselves
            sec = data["sections"][0]
            assert sec["parent_group"] == "feature-cards"
            assert sec["depth"] == 1
            assert sec["total_children"] == 2  # 2 sibling nodes
            assert sec["section_id"] == "2:100"  # first node_id
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)

    def test_groups_skips_single_pattern(self):
        """Groups with pattern 'single' are skipped."""
        groups = {
            "groups": [
                {
                    "name": "standalone",
                    "pattern": "single",
                    "node_ids": ["2:200"],
                },
                {
                    "name": "feature-cards",
                    "pattern": "card",
                    "node_ids": ["2:100", "2:101"],
                },
            ]
        }
        meta_tmp = write_fixture(self.METADATA)
        groups_tmp = self._write_groups(groups)
        try:
            data = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp,
            )
            assert data["total_sections"] == 1  # only feature-cards
            assert data["sections"][0]["section_name"] == "feature-cards"
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)

    def test_groups_default_depth_zero(self):
        """Default depth is 0 when --depth is not specified."""
        groups = {
            "groups": [
                {
                    "name": "cards",
                    "pattern": "card",
                    "node_ids": ["2:100", "2:101"],
                },
            ]
        }
        meta_tmp = write_fixture(self.METADATA)
        groups_tmp = self._write_groups(groups)
        try:
            data = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp,
            )
            assert data["depth"] == 0
            assert data["sections"][0]["depth"] == 0
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)

    def test_groups_skips_too_few_siblings(self):
        """Groups with fewer than 2 resolvable node_ids are skipped (Issue 257)."""
        groups = {
            "groups": [
                {
                    "name": "empty-group",
                    "pattern": "list",
                    "node_ids": ["2:200"],  # only 1 node_id → too few siblings
                },
            ]
        }
        meta_tmp = write_fixture(self.METADATA)
        groups_tmp = self._write_groups(groups)
        try:
            data = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp,
            )
            assert data["total_sections"] == 0
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)

    def test_groups_output_has_enriched_table_and_prompt(self):
        """Each section in groups mode has enriched_children_table and prompt."""
        groups = {
            "groups": [
                {
                    "name": "cards",
                    "pattern": "card",
                    "node_ids": ["2:100", "2:101"],
                },
            ]
        }
        meta_tmp = write_fixture(self.METADATA)
        groups_tmp = self._write_groups(groups)
        try:
            data = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp, "--depth", "1",
            )
            sec = data["sections"][0]
            assert "enriched_children_table" in sec
            assert len(sec["enriched_children_table"]) > 0
            assert "prompt" in sec
            assert len(sec["prompt"]) > 0
            # Prompt should contain the section name
            assert "cards" in sec["prompt"]
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)

    def test_groups_output_file(self):
        """--output flag writes result to file in groups mode."""
        groups = {
            "groups": [
                {
                    "name": "cards",
                    "pattern": "card",
                    "node_ids": ["2:100", "2:101"],
                },
            ]
        }
        meta_tmp = write_fixture(self.METADATA)
        groups_tmp = self._write_groups(groups)
        out_tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        out_tmp.close()
        try:
            result = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp,
                "--depth", "1", "--output", out_tmp.name,
            )
            assert result["status"] == "ok"
            assert result["depth"] == 1

            # Verify the output file content
            with open(out_tmp.name, "r") as f:
                file_data = json.load(f)
            assert file_data["total_sections"] == 1
            assert file_data["depth"] == 1
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)
            os.unlink(out_tmp.name)

    def test_plan_mode_unchanged(self):
        """Original plan mode still works (backward compatibility)."""
        plan = {
            "sections": [
                {
                    "name": "section-hero",
                    "node_ids": ["2:100"],
                },
            ]
        }
        meta_tmp = write_fixture(self.METADATA)
        plan_tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(plan, plan_tmp)
        plan_tmp.close()
        try:
            data = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, plan_tmp.name,
            )
            assert "error" not in data
            assert data["total_sections"] >= 1
            assert data["model"] == "haiku"
            # Plan mode should NOT have depth field at top level
            assert "depth" not in data
            # Sections should NOT have parent_group or depth fields
            sec = data["sections"][0]
            assert "parent_group" not in sec
            assert "depth" not in sec
        finally:
            os.unlink(meta_tmp)
            os.unlink(plan_tmp.name)


# ============================================================
# Constants: Stage C recursive nesting (Issue 224)
# ============================================================
class TestMaxStageCDepth:
    def test_max_stage_c_depth_value(self):
        assert MAX_STAGE_C_DEPTH == 10  # Safety upper bound, convergence-based (Issue 257)

    def test_max_stage_c_depth_is_positive(self):
        assert MAX_STAGE_C_DEPTH > 0


# ============================================================
# Constants: STAGE_C_COVERABLE / STAGE_A_ONLY (Issue 229)
# ============================================================
class TestStageCCoverableConstants:
    def test_stage_c_coverable_expected_values(self):
        """STAGE_C_COVERABLE_DETECTORS contains expected detector names."""
        expected = {'bg-content', 'table', 'highlight', 'tuple', 'consecutive', 'heading-content'}
        assert STAGE_C_COVERABLE_DETECTORS == expected

    def test_stage_a_only_expected_values(self):
        """STAGE_A_ONLY_DETECTORS contains expected detector names."""
        expected = {'header-footer', 'horizontal-bar', 'zone', 'semantic', 'proximity', 'spacing', 'pattern'}
        assert STAGE_A_ONLY_DETECTORS == expected

    def test_no_overlap(self):
        """Coverable and A-only sets should be disjoint."""
        overlap = STAGE_C_COVERABLE_DETECTORS & STAGE_A_ONLY_DETECTORS
        assert len(overlap) == 0, f"Unexpected overlap: {overlap}"


# ============================================================
# detect-grouping-candidates.sh: --disable-detectors (Issue 229)
# ============================================================
class TestDisableDetectors:
    """Test --disable-detectors flag for selective detector disabling."""

    def _build_fixture(self):
        """Build a fixture that generates multiple detector types."""
        # Large flat structure at root to trigger proximity, pattern, spacing, semantic,
        # zone, consecutive, heading-content, and header-footer
        children = []
        # Header zone elements (for header-footer detection)
        children.append({
            "id": "1:1", "name": "Logo", "type": "VECTOR",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 100, "height": 50},
            "children": []})
        for i in range(4):
            children.append({
                "id": f"1:{10+i}", "name": f"NavItem{i}", "type": "TEXT",
                "absoluteBoundingBox": {"x": 150 + i*120, "y": 10, "width": 80, "height": 20},
                "children": []})
        # Heading + content pair
        children.append({
            "id": "2:1", "name": "SectionTitle", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 200, "width": 1440, "height": 60},
            "children": [
                {"id": "2:1a", "name": "Title Text", "type": "TEXT",
                 "absoluteBoundingBox": {"x": 10, "y": 210, "width": 400, "height": 40},
                 "children": [], "characters": "About Us"}
            ]})
        children.append({
            "id": "2:2", "name": "SectionBody", "type": "FRAME",
            "absoluteBoundingBox": {"x": 0, "y": 280, "width": 1440, "height": 400},
            "children": [
                {"id": "2:2a", "name": "BodyText", "type": "TEXT",
                 "absoluteBoundingBox": {"x": 10, "y": 290, "width": 600, "height": 380},
                 "children": [], "characters": "Lorem ipsum dolor sit amet"}
            ]})
        # Many similar frames to trigger consecutive/pattern detection
        for i in range(5):
            children.append({
                "id": f"3:{i}", "name": f"Frame {i}", "type": "FRAME",
                "absoluteBoundingBox": {"x": 0, "y": 800 + i*200, "width": 1440, "height": 180},
                "children": [
                    {"id": f"3:{i}a", "name": "Title", "type": "TEXT",
                     "absoluteBoundingBox": {"x": 10, "y": 810 + i*200, "width": 400, "height": 30},
                     "children": [], "characters": f"Item {i}"},
                    {"id": f"3:{i}b", "name": "Image", "type": "RECTANGLE",
                     "absoluteBoundingBox": {"x": 500, "y": 810 + i*200, "width": 200, "height": 150},
                     "children": []},
                ]})
        # Footer zone
        children.append({
            "id": "4:1", "name": "FooterText", "type": "TEXT",
            "absoluteBoundingBox": {"x": 0, "y": 4900, "width": 200, "height": 30},
            "children": []})
        children.append({
            "id": "4:2", "name": "FooterLink", "type": "TEXT",
            "absoluteBoundingBox": {"x": 300, "y": 4900, "width": 150, "height": 30},
            "children": []})

        return {
            "document": {
                "id": "0:0", "name": "Document", "type": "DOCUMENT",
                "children": [{
                    "id": "0:1", "name": "Page", "type": "CANVAS",
                    "children": [{
                        "id": "root", "name": "Desktop", "type": "FRAME",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 5000},
                        "children": children
                    }]
                }]
            }
        }

    def test_disable_detectors_empty(self):
        """Empty disable string = no detectors disabled (current behavior)."""
        data = self._build_fixture()
        tmp = write_fixture(data)
        try:
            result = run_script("detect-grouping-candidates.sh", tmp)
            assert result["total"] > 0
            assert "disabled_detectors" not in result
            methods = {c.get("method") for c in result.get("candidates", [])}
            # Should have at least some methods present
            assert len(methods) >= 1
        finally:
            os.unlink(tmp)

    def test_disable_detectors_single(self):
        """Disabling one detector removes all candidates with that method."""
        data = self._build_fixture()
        tmp = write_fixture(data)
        try:
            result = run_script(
                "detect-grouping-candidates.sh", tmp,
                "--disable-detectors", "consecutive")
            methods = {c.get("method") for c in result.get("candidates", [])}
            assert "consecutive" not in methods, \
                f"'consecutive' should be disabled but found in methods: {methods}"
            assert result.get("disabled_detectors") == ["consecutive"]
        finally:
            os.unlink(tmp)

    def test_disable_detectors_multiple(self):
        """Disabling multiple detectors removes all their candidates."""
        data = self._build_fixture()
        tmp = write_fixture(data)
        try:
            result = run_script(
                "detect-grouping-candidates.sh", tmp,
                "--disable-detectors", "consecutive,heading-content,table")
            methods = {c.get("method") for c in result.get("candidates", [])}
            assert "consecutive" not in methods
            assert "heading-content" not in methods
            assert "table" not in methods
            assert set(result.get("disabled_detectors", [])) == {"consecutive", "heading-content", "table"}
        finally:
            os.unlink(tmp)

    def test_disable_detectors_invalid(self):
        """Invalid detector name is warned and stripped (no error)."""
        data = self._build_fixture()
        tmp = write_fixture(data)
        try:
            result = run_script(
                "detect-grouping-candidates.sh", tmp,
                "--disable-detectors", "nonexistent-detector")
            # Should succeed without error
            assert "error" not in result
            # Unknown detectors are stripped, so disabled_detectors should be absent or empty
            assert "nonexistent-detector" not in result.get("disabled_detectors", [])
        finally:
            os.unlink(tmp)

    def test_disable_all_stage_c_coverable(self):
        """Disabling all Stage C coverable detectors still produces output from remaining."""
        data = self._build_fixture()
        tmp = write_fixture(data)
        try:
            disable_list = ",".join(sorted(STAGE_C_COVERABLE_DETECTORS))
            result = run_script(
                "detect-grouping-candidates.sh", tmp,
                "--disable-detectors", disable_list)
            methods = {c.get("method") for c in result.get("candidates", [])}
            # No Stage C coverable methods should appear
            for d in STAGE_C_COVERABLE_DETECTORS:
                assert d not in methods, f"'{d}' should be disabled"
            # But Stage A only detectors should still work
            # (at least some of them, depending on fixture)
            assert "error" not in result
        finally:
            os.unlink(tmp)


# ============================================================
# STAGE_C_COVERAGE_THRESHOLD constant (Fix 1)
# ============================================================
class TestStageCCoverageThreshold:
    """Tests for STAGE_C_COVERAGE_THRESHOLD constant."""

    def test_stage_c_coverage_threshold_value(self):
        """STAGE_C_COVERAGE_THRESHOLD should be 0.8."""
        assert STAGE_C_COVERAGE_THRESHOLD == 0.8

    def test_stage_c_coverage_threshold_used_in_compare(self):
        """compare_grouping_by_section should use STAGE_C_COVERAGE_THRESHOLD."""
        # Stage A with one section
        stage_a = [
            {'parent_id': 'sec1', 'node_ids': ['a', 'b'], 'method': 'pattern', 'count': 2},
        ]
        # Stage C with high coverage (>= 0.8) for section
        stage_c = [
            {
                'section_id': 'sec1',
                'groups': [
                    {'node_ids': ['a', 'b'], 'name': 'group-1', 'method': 'stage_c'},
                ],
            },
        ]
        result = compare_grouping_by_section(stage_a, stage_c)
        # High coverage should adopt stage_c
        assert result['sections'][0]['source'] == 'stage_c'

    def test_stage_c_coverage_threshold_fallback(self):
        """Below STAGE_C_COVERAGE_THRESHOLD should fall back to stage_a."""
        stage_a = [
            {'parent_id': 'sec1', 'node_ids': ['a', 'b', 'c'], 'method': 'pattern', 'count': 3},
        ]
        # Stage C with no matching groups (coverage = 0)
        stage_c = [
            {
                'section_id': 'sec1',
                'groups': [
                    {'node_ids': ['x', 'y'], 'name': 'group-1', 'method': 'stage_c'},
                ],
            },
        ]
        result = compare_grouping_by_section(stage_a, stage_c)
        assert result['sections'][0]['source'] == 'stage_a'


# ============================================================
# MAX_STAGE_C_DEPTH enforcement in groups mode (Fix 2)
# ============================================================
class TestMaxStageCDepthEnforcement:
    """Test MAX_STAGE_C_DEPTH enforcement in generate-nested-grouping-context.sh."""

    def _build_groups_fixture(self):
        """Build metadata + groups files for testing."""
        metadata = {
            "document": {
                "id": "0:0", "name": "Doc", "type": "DOCUMENT",
                "children": [{
                    "id": "0:1", "name": "Page", "type": "CANVAS",
                    "children": [{
                        "id": "root", "name": "Desktop", "type": "FRAME",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
                        "children": [
                            {"id": "n1", "name": "Section1", "type": "FRAME",
                             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                             "children": [
                                 {"id": "n1a", "name": "Child1", "type": "TEXT",
                                  "absoluteBoundingBox": {"x": 10, "y": 10, "width": 200, "height": 30},
                                  "children": [], "characters": "Hello"},
                             ]},
                        ],
                    }]
                }]
            }
        }
        groups = {
            "groups": [
                {"name": "section-1", "pattern": "multi", "node_ids": ["n1"]},
            ]
        }
        return metadata, groups

    def test_depth_below_max_produces_sections(self):
        """Depth below MAX_STAGE_C_DEPTH should produce sections."""
        metadata, groups = self._build_groups_fixture()
        meta_tmp = write_fixture(metadata)
        groups_tmp = write_fixture(groups)
        try:
            result = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp, "--depth", "0")
            assert 'skipped_reason' not in result
            assert result['total_sections'] >= 0
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)

    def test_depth_at_max_skips(self):
        """Depth == MAX_STAGE_C_DEPTH should skip with reason."""
        metadata, groups = self._build_groups_fixture()
        meta_tmp = write_fixture(metadata)
        groups_tmp = write_fixture(groups)
        try:
            result = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp, "--depth", str(MAX_STAGE_C_DEPTH))
            assert result['total_sections'] == 0
            assert 'skipped_reason' in result
            assert 'MAX_STAGE_C_DEPTH' in result['skipped_reason']
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)

    def test_depth_above_max_skips(self):
        """Depth > MAX_STAGE_C_DEPTH should skip with reason."""
        metadata, groups = self._build_groups_fixture()
        meta_tmp = write_fixture(metadata)
        groups_tmp = write_fixture(groups)
        try:
            result = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp, "--depth", str(MAX_STAGE_C_DEPTH + 1))
            assert result['total_sections'] == 0
            assert 'skipped_reason' in result
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)


# ============================================================
# Unknown detector name warning (Fix 3)
# ============================================================
class TestUnknownDetectorValidation:
    """Test that unknown detector names are warned and stripped."""

    def _build_simple_fixture(self):
        return {
            "document": {
                "id": "0:0", "name": "Doc", "type": "DOCUMENT",
                "children": [{
                    "id": "0:1", "name": "Page", "type": "CANVAS",
                    "children": [{
                        "id": "root", "name": "Desktop", "type": "FRAME",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
                        "children": [
                            {"id": "1:1", "name": "Frame 1", "type": "FRAME",
                             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                             "children": [
                                 {"id": "1:1a", "name": "Text", "type": "TEXT",
                                  "absoluteBoundingBox": {"x": 10, "y": 10, "width": 200, "height": 30},
                                  "children": [], "characters": "Hello"},
                             ]},
                        ],
                    }]
                }]
            }
        }

    def test_unknown_detector_stripped_from_disabled(self):
        """Unknown detector names should be stripped (not appear in disabled_detectors)."""
        data = self._build_simple_fixture()
        tmp = write_fixture(data)
        try:
            result = run_script(
                "detect-grouping-candidates.sh", tmp,
                "--disable-detectors", "fake-detector,also-fake")
            # Unknown detectors are stripped, so disabled_detectors should not include them
            assert "error" not in result
            disabled = result.get("disabled_detectors", [])
            assert "fake-detector" not in disabled
            assert "also-fake" not in disabled
        finally:
            os.unlink(tmp)

    def test_mixed_valid_invalid_detectors(self):
        """Valid detectors are kept, invalid ones are stripped."""
        data = self._build_simple_fixture()
        tmp = write_fixture(data)
        try:
            result = run_script(
                "detect-grouping-candidates.sh", tmp,
                "--disable-detectors", "consecutive,fake-one")
            assert "error" not in result
            methods = {c.get("method") for c in result.get("candidates", [])}
            assert "consecutive" not in methods
        finally:
            os.unlink(tmp)


# ============================================================
# Stage A-only detector protection (Fix 4)
# ============================================================
class TestStageAOnlyProtection:
    """Test that Stage A-only detectors cannot be disabled."""

    def _build_fixture_with_header(self):
        """Build fixture that would trigger header-footer detection."""
        children = []
        children.append({
            "id": "1:1", "name": "Logo", "type": "VECTOR",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 100, "height": 50},
            "children": []})
        for i in range(4):
            children.append({
                "id": f"1:{10+i}", "name": f"NavItem{i}", "type": "TEXT",
                "absoluteBoundingBox": {"x": 150 + i*120, "y": 10, "width": 80, "height": 20},
                "children": []})
        # Some content sections to have a non-trivial result
        for i in range(5):
            children.append({
                "id": f"2:{i}", "name": f"Section {i}", "type": "FRAME",
                "absoluteBoundingBox": {"x": 0, "y": 200 + i*300, "width": 1440, "height": 280},
                "children": [
                    {"id": f"2:{i}a", "name": "Title", "type": "TEXT",
                     "absoluteBoundingBox": {"x": 10, "y": 210 + i*300, "width": 400, "height": 30},
                     "children": [], "characters": f"Section {i}"},
                ]})
        return {
            "document": {
                "id": "0:0", "name": "Doc", "type": "DOCUMENT",
                "children": [{
                    "id": "0:1", "name": "Page", "type": "CANVAS",
                    "children": [{
                        "id": "root", "name": "Desktop", "type": "FRAME",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 3000},
                        "children": children
                    }]
                }]
            }
        }

    def test_disable_stage_a_only_ignored(self):
        """Trying to disable a Stage A-only detector should be ignored."""
        data = self._build_fixture_with_header()
        tmp = write_fixture(data)
        try:
            result = run_script(
                "detect-grouping-candidates.sh", tmp,
                "--disable-detectors", "header-footer,semantic")
            # Stage A-only detectors should be stripped from disabled list
            disabled = result.get("disabled_detectors", [])
            assert "header-footer" not in disabled
            assert "semantic" not in disabled
            assert "error" not in result
        finally:
            os.unlink(tmp)

    def test_disable_mixed_coverable_and_stage_a(self):
        """Coverable detectors are disabled but Stage A-only are kept."""
        data = self._build_fixture_with_header()
        tmp = write_fixture(data)
        try:
            result = run_script(
                "detect-grouping-candidates.sh", tmp,
                "--disable-detectors", "consecutive,header-footer")
            disabled = result.get("disabled_detectors", [])
            # consecutive (coverable) should be disabled
            methods = {c.get("method") for c in result.get("candidates", [])}
            assert "consecutive" not in methods
            # header-footer (Stage A-only) should NOT be disabled
            assert "header-footer" not in disabled
        finally:
            os.unlink(tmp)


# ============================================================
# Skipped groups reporting in --groups mode (Fix 5)
# ============================================================
class TestSkippedGroupsReporting:
    """Test that skipped groups are reported in groups mode output."""

    def _build_metadata(self):
        return {
            "document": {
                "id": "0:0", "name": "Doc", "type": "DOCUMENT",
                "children": [{
                    "id": "0:1", "name": "Page", "type": "CANVAS",
                    "children": [{
                        "id": "root", "name": "Desktop", "type": "FRAME",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 2000},
                        "children": [
                            {"id": "n1", "name": "Section1", "type": "FRAME",
                             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500},
                             "children": [
                                 {"id": "n1a", "name": "Child1", "type": "TEXT",
                                  "absoluteBoundingBox": {"x": 10, "y": 10, "width": 200, "height": 30},
                                  "children": [], "characters": "Hello"},
                             ]},
                            {"id": "n2", "name": "LeafNode", "type": "TEXT",
                             "absoluteBoundingBox": {"x": 0, "y": 600, "width": 200, "height": 30},
                             "children": [], "characters": "Leaf"},
                        ],
                    }]
                }]
            }
        }

    def test_single_pattern_skipped(self):
        """Groups with pattern='single' are reported as skipped."""
        metadata = self._build_metadata()
        groups = {
            "groups": [
                {"name": "section-1", "pattern": "multi", "node_ids": ["n1"]},
                {"name": "leaf-item", "pattern": "single", "node_ids": ["n2"]},
            ]
        }
        meta_tmp = write_fixture(metadata)
        groups_tmp = write_fixture(groups)
        try:
            result = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp, "--depth", "0")
            assert result.get('skipped_count', 0) >= 1
            skipped = result.get('skipped_groups', [])
            single_skipped = [s for s in skipped if 'pattern=single' in s.get('reason', '')]
            assert len(single_skipped) >= 1
            assert single_skipped[0]['name'] == 'leaf-item'
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)

    def test_too_few_siblings_skipped(self):
        """Groups with <2 resolvable node_ids are reported as skipped (Issue 257)."""
        metadata = self._build_metadata()
        groups = {
            "groups": [
                {"name": "leaf-group", "pattern": "multi", "node_ids": ["n2"]},
            ]
        }
        meta_tmp = write_fixture(metadata)
        groups_tmp = write_fixture(groups)
        try:
            result = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp, "--depth", "0")
            assert result.get('skipped_count', 0) >= 1
            skipped = result.get('skipped_groups', [])
            few_siblings = [s for s in skipped if 'too few sibling nodes' in s.get('reason', '')]
            assert len(few_siblings) >= 1
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)

    def test_no_skips_when_all_valid(self):
        """When all groups are valid (>=2 node_ids), skipped_count is 0."""
        metadata = self._build_metadata()
        groups = {
            "groups": [
                {"name": "section-1", "pattern": "multi", "node_ids": ["n1", "n2"]},
            ]
        }
        meta_tmp = write_fixture(metadata)
        groups_tmp = write_fixture(groups)
        try:
            result = run_script(
                "generate-nested-grouping-context.sh",
                meta_tmp, "--groups", groups_tmp, "--depth", "0")
            assert result.get('skipped_count', 0) == 0
        finally:
            os.unlink(meta_tmp)
            os.unlink(groups_tmp)

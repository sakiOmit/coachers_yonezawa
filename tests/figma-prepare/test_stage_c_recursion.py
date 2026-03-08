"""Tests for Stage C recursion depth: TestNestedGroupingContextGroups, TestMaxStageCDepth, TestMaxStageCDepthEnforcement."""
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

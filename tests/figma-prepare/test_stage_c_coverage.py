"""Tests for Stage C coverage & detector management: constants, disable-detectors, coverage threshold, validation, protection, skipped groups."""
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

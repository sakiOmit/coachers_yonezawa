"""Tests for deduplication, decoration pattern skip, and infer-autolayout hidden children."""
import json
import os
import pytest

from helpers import run_script, write_fixture

from figma_utils import (
    deduplicate_candidates,
    METHOD_PRIORITY,
)


class TestDecorationPatternSkip:
    """Decoration dot grid internals should not produce redundant candidates."""

    def test_decoration_children_not_recursed(self):
        """A decoration pattern's children should NOT be detected by pattern/proximity/spacing."""
        # Build a root with one section containing a decoration dot grid
        data = {
            "document": {
                "id": "0:0", "name": "Document", "type": "DOCUMENT",
                "children": [{
                    "id": "0:1", "name": "Page", "type": "CANVAS",
                    "children": [{
                        "id": "1:0", "name": "Artboard", "type": "FRAME",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 3000},
                        "children": [
                            # A non-decoration section (should be recursed)
                            {"id": "2:0", "name": "section-normal", "type": "FRAME",
                             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1500},
                             "children": [
                                 # Decoration dot grid: 150x150 frame with 9 ellipses
                                 {"id": "3:0", "name": "Frame 1", "type": "FRAME",
                                  "absoluteBoundingBox": {"x": 100, "y": 100, "width": 150, "height": 150},
                                  "children": [
                                      {"id": f"4:{i}", "name": f"Ellipse {i+1}", "type": "ELLIPSE",
                                       "absoluteBoundingBox": {
                                           "x": 100 + (i % 3) * 50,
                                           "y": 100 + (i // 3) * 50,
                                           "width": 10, "height": 10},
                                       "children": []}
                                      for i in range(9)
                                  ]},
                             ]},
                            # Another section to ensure root detection works
                            {"id": "2:1", "name": "section-other", "type": "FRAME",
                             "absoluteBoundingBox": {"x": 0, "y": 1500, "width": 1440, "height": 1500},
                             "children": []},
                        ],
                    }],
                }],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("detect-grouping-candidates.sh", tmp)
            candidates = result.get("candidates", [])
            # No candidate should have parent_id "3:0" (the decoration frame)
            # or parent_name "Frame 1" (the decoration frame's auto name)
            decoration_children_candidates = [
                c for c in candidates
                if c.get("parent_id") == "3:0" or c.get("parent_name") == "Frame 1"
            ]
            assert len(decoration_children_candidates) == 0, \
                f"Decoration internals should not produce candidates, got: {decoration_children_candidates}"
        finally:
            os.unlink(tmp)

    def test_non_decoration_children_still_recursed(self):
        """A non-decoration FRAME's children should still be detected normally."""
        # Build a root with a non-decoration frame containing pattern-detectable children
        data = {
            "document": {
                "id": "0:0", "name": "Document", "type": "DOCUMENT",
                "children": [{
                    "id": "0:1", "name": "Page", "type": "CANVAS",
                    "children": [{
                        "id": "1:0", "name": "Artboard", "type": "FRAME",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 3000},
                        "children": [
                            # A large non-decoration frame (> 200px, so NOT decoration)
                            {"id": "2:0", "name": "Frame 1", "type": "FRAME",
                             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1500},
                             "children": [
                                 # 20 similar TEXT children → should trigger pattern detection
                                 *[{"id": f"3:{i}", "name": f"Text {i+1}", "type": "TEXT",
                                    "absoluteBoundingBox": {
                                        "x": 100, "y": i * 50,
                                        "width": 200, "height": 30},
                                    "characters": f"Item {i+1}",
                                    "children": []}
                                   for i in range(20)],
                             ]},
                            {"id": "2:1", "name": "section-other", "type": "FRAME",
                             "absoluteBoundingBox": {"x": 0, "y": 1500, "width": 1440, "height": 1500},
                             "children": []},
                        ],
                    }],
                }],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("detect-grouping-candidates.sh", tmp)
            candidates = result.get("candidates", [])
            # There should be candidates with parent_id "2:0" (the non-decoration frame)
            non_decoration_candidates = [
                c for c in candidates
                if c.get("parent_id") == "2:0"
            ]
            assert len(non_decoration_candidates) > 0, \
                f"Non-decoration frame children should still produce candidates. All candidates: {candidates}"
        finally:
            os.unlink(tmp)


# ============================================================
# infer-autolayout.sh: hidden children filtering (Audit Issue #18)
# ============================================================

class TestInferAutolayoutHiddenChildren:
    """Hidden children (visible: false) should be excluded from auto layout inference."""

    def test_hidden_child_excluded_from_inference(self):
        """A frame with 3 visible children at regular positions + 1 hidden child
        at a distant position. The hidden child should not affect gap/direction."""
        data = {
            "document": {
                "id": "0:0", "name": "Document", "type": "DOCUMENT",
                "children": [{
                    "id": "0:1", "name": "Page", "type": "CANVAS",
                    "children": [{
                        "id": "1:0", "name": "container", "type": "FRAME",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 400, "height": 200},
                        "children": [
                            # 3 visible children evenly spaced vertically
                            {"id": "1:1", "name": "child-1", "type": "FRAME",
                             "absoluteBoundingBox": {"x": 10, "y": 10, "width": 380, "height": 40},
                             "children": []},
                            {"id": "1:2", "name": "child-2", "type": "FRAME",
                             "absoluteBoundingBox": {"x": 10, "y": 70, "width": 380, "height": 40},
                             "children": []},
                            {"id": "1:3", "name": "child-3", "type": "FRAME",
                             "absoluteBoundingBox": {"x": 10, "y": 130, "width": 380, "height": 40},
                             "children": []},
                            # 1 hidden child at a very distant position
                            {"id": "1:4", "name": "hidden-child", "type": "FRAME",
                             "visible": False,
                             "absoluteBoundingBox": {"x": 5000, "y": 5000, "width": 100, "height": 100},
                             "children": []},
                        ],
                    }],
                }],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("infer-autolayout.sh", tmp)
            frames = result.get("frames", [])
            # The container frame should be inferred
            container_frames = [f for f in frames if f["node_id"] == "1:0"]
            assert len(container_frames) == 1, f"Expected 1 container frame, got {len(container_frames)}"
            layout = container_frames[0]["layout"]
            # Direction should be VERTICAL (children stacked vertically)
            assert layout["direction"] == "VERTICAL", \
                f"Expected VERTICAL direction, got {layout['direction']}"
            # Gap should be ~20px (snapped), not skewed by distant hidden child
            assert layout["gap"] <= 24, \
                f"Expected gap <= 24 (from visible children), got {layout['gap']} — hidden child may have skewed it"
            # Child count should be 3 (excluding hidden)
            assert container_frames[0]["child_count"] == 3, \
                f"Expected child_count=3 (hidden excluded), got {container_frames[0]['child_count']}"
        finally:
            os.unlink(tmp)

    def test_all_visible_children_hidden_leaves_insufficient(self):
        """If hiding children leaves fewer than 2 visible, no layout should be inferred."""
        data = {
            "document": {
                "id": "0:0", "name": "Document", "type": "DOCUMENT",
                "children": [{
                    "id": "0:1", "name": "Page", "type": "CANVAS",
                    "children": [{
                        "id": "1:0", "name": "container", "type": "FRAME",
                        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 400, "height": 200},
                        "children": [
                            {"id": "1:1", "name": "visible-child", "type": "FRAME",
                             "absoluteBoundingBox": {"x": 10, "y": 10, "width": 380, "height": 40},
                             "children": []},
                            {"id": "1:2", "name": "hidden-1", "type": "FRAME",
                             "visible": False,
                             "absoluteBoundingBox": {"x": 10, "y": 70, "width": 380, "height": 40},
                             "children": []},
                            {"id": "1:3", "name": "hidden-2", "type": "FRAME",
                             "visible": False,
                             "absoluteBoundingBox": {"x": 10, "y": 130, "width": 380, "height": 40},
                             "children": []},
                        ],
                    }],
                }],
            }
        }
        tmp = write_fixture(data)
        try:
            result = run_script("infer-autolayout.sh", tmp)
            frames = result.get("frames", [])
            # Container should NOT appear since only 1 visible child
            container_frames = [f for f in frames if f["node_id"] == "1:0"]
            assert len(container_frames) == 0, \
                f"Container with only 1 visible child should not be inferred, got: {container_frames}"
        finally:
            os.unlink(tmp)


# ============================================================
# deduplicate_candidates (Issue 236)
# ============================================================

class TestDeduplicateCandidates:
    """Direct unit tests for deduplicate_candidates (Issue 236)."""

    def _make_candidate(self, method, node_ids, node_names=None, parent_id='root', parent_name='Frame 1'):
        """Helper to create a candidate dict."""
        if node_names is None:
            node_names = [f'node-{nid}' for nid in node_ids]
        return {
            'method': method,
            'node_ids': list(node_ids),
            'node_names': list(node_names),
            'count': len(node_ids),
            'suggested_name': f'{method}-group',
            'parent_id': parent_id,
            'parent_name': parent_name,
        }

    def test_no_overlap_keeps_all(self):
        """No overlap: both candidates should be kept intact."""
        c1 = self._make_candidate('semantic', ['1', '2', '3'])
        c2 = self._make_candidate('pattern', ['4', '5', '6'])
        result = deduplicate_candidates([c1, c2])
        assert len(result) == 2
        assert set(result[0]['node_ids']) == {'1', '2', '3'}
        assert set(result[1]['node_ids']) == {'4', '5', '6'}

    def test_partial_overlap_trims_lower_priority(self):
        """Issue 236: Partial overlap should trim, not delete entire candidate."""
        c1 = self._make_candidate('semantic', ['10', '11', '12'])  # priority 4
        c2 = self._make_candidate('pattern', ['12', '13', '14'])   # priority 2
        result = deduplicate_candidates([c1, c2])
        assert len(result) == 2, f"Expected 2 candidates, got {len(result)}"
        # Semantic keeps all nodes
        assert set(result[0]['node_ids']) == {'10', '11', '12'}
        # Pattern is trimmed: node 12 removed, nodes 13+14 preserved
        assert set(result[1]['node_ids']) == {'13', '14'}
        assert result[1]['count'] == 2

    def test_partial_overlap_node_names_trimmed_in_parallel(self):
        """node_names should be trimmed in parallel with node_ids."""
        c1 = self._make_candidate('semantic', ['A', 'B'], ['Alpha', 'Beta'])
        c2 = self._make_candidate('pattern', ['B', 'C', 'D'], ['Beta', 'Charlie', 'Delta'])
        result = deduplicate_candidates([c1, c2])
        trimmed = result[1]
        assert trimmed['node_ids'] == ['C', 'D']
        assert trimmed['node_names'] == ['Charlie', 'Delta']

    def test_full_subset_removed(self):
        """If all nodes of lower-priority candidate overlap, remove it entirely."""
        c1 = self._make_candidate('semantic', ['1', '2', '3'])  # priority 4
        c2 = self._make_candidate('proximity', ['2', '3'])       # priority 0, subset
        result = deduplicate_candidates([c1, c2])
        assert len(result) == 1
        assert result[0]['method'] == 'semantic'

    def test_same_priority_no_trim(self):
        """Same-priority candidates should not trim each other."""
        c1 = self._make_candidate('pattern', ['1', '2', '3'])
        c2 = self._make_candidate('pattern', ['3', '4', '5'])
        result = deduplicate_candidates([c1, c2])
        assert len(result) == 2
        assert set(result[0]['node_ids']) == {'1', '2', '3'}
        assert set(result[1]['node_ids']) == {'3', '4', '5'}

    def test_rule2_proximity_named_parent_removed(self):
        """Rule 2: proximity candidate with named parent (non-root) should be removed."""
        c1 = self._make_candidate('proximity', ['1', '2'],
                                  parent_id='child', parent_name='About Section')
        result = deduplicate_candidates([c1], root_id='root')
        assert len(result) == 0

    def test_rule2_root_parent_exempt(self):
        """Rule 2: root-level proximity candidates are exempt."""
        c1 = self._make_candidate('proximity', ['1', '2'],
                                  parent_id='root', parent_name='About Section')
        result = deduplicate_candidates([c1], root_id='root')
        assert len(result) == 1

    def test_rule2_unnamed_parent_kept(self):
        """Rule 2: proximity candidate with unnamed parent should be kept."""
        c1 = self._make_candidate('proximity', ['1', '2'],
                                  parent_id='child', parent_name='Frame 1')
        result = deduplicate_candidates([c1], root_id='root')
        assert len(result) == 1

    def test_empty_candidates(self):
        """Edge case: empty input."""
        result = deduplicate_candidates([])
        assert result == []

    def test_single_candidate(self):
        """Edge case: single candidate, no dedup needed."""
        c1 = self._make_candidate('semantic', ['1', '2'])
        result = deduplicate_candidates([c1])
        assert len(result) == 1

    def test_triple_overlap_cascade(self):
        """Three candidates with cascading overlaps: highest priority wins overlap nodes."""
        c1 = self._make_candidate('semantic', ['1', '2', '3'])       # priority 4
        c2 = self._make_candidate('consecutive', ['3', '4', '5'])    # priority 2.5
        c3 = self._make_candidate('proximity', ['5', '6', '7'])      # priority 0
        result = deduplicate_candidates([c1, c2, c3])
        assert len(result) == 3
        assert set(result[0]['node_ids']) == {'1', '2', '3'}
        # consecutive: node 3 trimmed by semantic
        assert set(result[1]['node_ids']) == {'4', '5'}
        # proximity: node 5 trimmed by consecutive (which has higher priority)
        assert set(result[2]['node_ids']) == {'6', '7'}

    def test_does_not_mutate_original(self):
        """Trimming should not mutate the original candidate dicts."""
        c1 = self._make_candidate('semantic', ['A', 'B'])
        c2 = self._make_candidate('pattern', ['B', 'C'])
        original_ids = list(c2['node_ids'])
        deduplicate_candidates([c1, c2])
        assert c2['node_ids'] == original_ids, "Original candidate was mutated"

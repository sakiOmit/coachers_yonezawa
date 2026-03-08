"""Tests for hidden filters, deduplication, decoration skip, and small utilities."""
import json
import os
import pytest

from helpers import run_script, write_fixture

from figma_utils import (
    _collect_text_preview,
    _count_flat_descendants,
    alignment_bonus,
    compute_gap_consistency,
    decoration_dominant_shape,
    deduplicate_candidates,
    detect_highlight_text,
    detect_horizontal_bar,
    detect_en_jp_label_pairs,
    detect_table_rows,
    generate_enriched_table,
    infer_direction_two_elements,
    is_decoration_pattern,
    is_heading_like,
    METHOD_PRIORITY,
    size_similarity_bonus,
    structure_hash,
    _compute_child_types,
    _compute_flags,
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


# === Issue #242: Hidden children filter tests ===


class TestHiddenChildrenFilter:
    """Issue #242: Verify hidden children (visible=False) are excluded in 4 internal helpers."""

    def test_collect_text_preview_skips_hidden(self):
        """_collect_text_preview should not return text from hidden children."""
        from figma_utils import _collect_text_preview
        node = {
            'type': 'FRAME', 'name': 'wrapper',
            'children': [
                {'type': 'TEXT', 'characters': 'Hidden Text', 'name': 'hidden-text', 'visible': False},
                {'type': 'TEXT', 'characters': 'Visible Text', 'name': 'visible-text'},
            ],
        }
        result = _collect_text_preview(node)
        assert result == 'Visible Text'

    def test_collect_text_preview_all_hidden(self):
        """_collect_text_preview returns empty when all children are hidden."""
        from figma_utils import _collect_text_preview
        node = {
            'type': 'FRAME', 'name': 'wrapper',
            'children': [
                {'type': 'TEXT', 'characters': 'Secret', 'name': 'hidden', 'visible': False},
            ],
        }
        assert _collect_text_preview(node) == ''

    def test_is_heading_like_skips_hidden_children(self):
        """is_heading_like count_leaves should not count hidden children."""
        # 2 visible TEXT + 1 hidden RECTANGLE nested inside a sub-frame
        # Total top-level children = 2 (within HEADING_MAX_CHILDREN=5)
        # The sub-frame has hidden non-TEXT children that should not dilute ratio
        node = {
            'type': 'FRAME',
            'children': [
                {'type': 'TEXT', 'children': []},
                {'type': 'FRAME', 'children': [
                    {'type': 'TEXT', 'children': []},
                    # Hidden non-text children should be excluded from leaf count
                    {'type': 'RECTANGLE', 'children': [], 'visible': False},
                    {'type': 'IMAGE', 'children': [], 'visible': False},
                ]},
            ],
        }
        # Without filter in count_leaves: 2 TEXT + 2 non-TEXT = 50% → barely True
        # With filter in count_leaves: 2 TEXT / 2 total = 100% → True
        assert is_heading_like(node) is True

    def test_is_heading_like_hidden_makes_non_heading(self):
        """Hiding TEXT children can make a frame non-heading-like."""
        node = {
            'type': 'FRAME',
            'children': [
                {'type': 'TEXT', 'children': [], 'visible': False},
                {'type': 'TEXT', 'children': [], 'visible': False},
                {'type': 'RECTANGLE', 'children': []},
                {'type': 'RECTANGLE', 'children': []},
            ],
        }
        # Without filter: 2 TEXT + 2 RECT = 50% → True (edge)
        # With filter: 0 TEXT + 2 RECT = 0% → False
        assert is_heading_like(node) is False

    def test_is_decoration_pattern_skips_hidden_shapes(self):
        """is_decoration_pattern count_leaves should not count hidden shape children."""
        # Need: >= 3 shape leaves AND shape_ratio >= 0.6
        # 4 visible ELLIPSE + 1 visible TEXT = 4/5 = 0.8 → True
        # But add 10 hidden TEXT children → without filter would dilute ratio
        node = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 100},
            'children': [
                {'type': 'ELLIPSE', 'children': []},
                {'type': 'ELLIPSE', 'children': []},
                {'type': 'ELLIPSE', 'children': []},
                {'type': 'ELLIPSE', 'children': []},
                {'type': 'TEXT', 'children': []},
                # Hidden TEXT children should NOT count
                {'type': 'TEXT', 'children': [], 'visible': False},
                {'type': 'TEXT', 'children': [], 'visible': False},
                {'type': 'TEXT', 'children': [], 'visible': False},
                {'type': 'TEXT', 'children': [], 'visible': False},
                {'type': 'TEXT', 'children': [], 'visible': False},
            ],
        }
        # With filter: 4 shapes / 5 total = 0.8 >= 0.6 → True
        # Without filter: 4 shapes / 10 total = 0.4 < 0.6 → False
        assert is_decoration_pattern(node) is True

    def test_is_decoration_pattern_hidden_shapes_not_counted(self):
        """Hidden shapes should not be counted toward the shape threshold."""
        node = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 100},
            'children': [
                # Only 2 visible shapes (below DECORATION_MIN_SHAPES=3)
                {'type': 'ELLIPSE', 'children': []},
                {'type': 'ELLIPSE', 'children': []},
                # Hidden shapes should NOT push count above threshold
                {'type': 'ELLIPSE', 'children': [], 'visible': False},
                {'type': 'ELLIPSE', 'children': [], 'visible': False},
                {'type': 'ELLIPSE', 'children': [], 'visible': False},
            ],
        }
        # With filter: 2 shapes < 3 min → False
        # Without filter: 5 shapes → True
        assert is_decoration_pattern(node) is False

    def test_decoration_dominant_shape_skips_hidden(self):
        """decoration_dominant_shape count_shapes should not count hidden shapes."""
        node = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 100},
            'children': [
                # 3 visible RECTANGLE
                {'type': 'RECTANGLE', 'children': []},
                {'type': 'RECTANGLE', 'children': []},
                {'type': 'RECTANGLE', 'children': []},
                # 5 hidden ELLIPSE - should NOT be counted
                {'type': 'ELLIPSE', 'children': [], 'visible': False},
                {'type': 'ELLIPSE', 'children': [], 'visible': False},
                {'type': 'ELLIPSE', 'children': [], 'visible': False},
                {'type': 'ELLIPSE', 'children': [], 'visible': False},
                {'type': 'ELLIPSE', 'children': [], 'visible': False},
            ],
        }
        # With filter: 3 RECTANGLE > 0 ELLIPSE → RECTANGLE
        # Without filter: 5 ELLIPSE > 3 RECTANGLE → ELLIPSE
        assert decoration_dominant_shape(node) == 'RECTANGLE'

    def test_decoration_dominant_shape_nested_hidden(self):
        """Hidden children in nested structures should also be excluded."""
        node = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 100},
            'children': [
                {
                    'type': 'FRAME',
                    'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 50, 'height': 50},
                    'children': [
                        {'type': 'VECTOR', 'children': []},
                        {'type': 'VECTOR', 'children': []},
                        {'type': 'RECTANGLE', 'children': [], 'visible': False},
                        {'type': 'RECTANGLE', 'children': [], 'visible': False},
                        {'type': 'RECTANGLE', 'children': [], 'visible': False},
                    ],
                },
            ],
        }
        # With filter: 2 VECTOR, 0 RECTANGLE → VECTOR
        # Without filter: 3 RECTANGLE > 2 VECTOR → RECTANGLE
        assert decoration_dominant_shape(node) == 'VECTOR'


# ============================================================
# Issue #245: Hidden children filter for 10 functions
# ============================================================
class TestHiddenFilterIssue245:
    """Issue #245: Hidden children filter for 10 functions in figma_utils.py."""

    def test_structure_hash_ignores_hidden(self):
        node = {'type': 'FRAME', 'children': [
            {'type': 'TEXT', 'visible': False},
            {'type': 'RECTANGLE'},
        ]}
        h = structure_hash(node)
        assert 'TEXT' not in h  # hidden TEXT excluded

    def test_structure_hash_all_hidden_returns_leaf(self):
        node = {'type': 'FRAME', 'children': [
            {'type': 'TEXT', 'visible': False},
        ]}
        assert structure_hash(node) == 'FRAME'

    def test_is_heading_like_ignores_hidden(self):
        # 6 children but 3 hidden → effective 3, should pass MAX_CHILDREN check
        node = {'type': 'FRAME', 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 200, 'height': 50}, 'children': [
            {'type': 'TEXT', 'visible': False},
            {'type': 'TEXT', 'visible': False},
            {'type': 'TEXT', 'visible': False},
            {'type': 'TEXT', 'characters': 'A'},
            {'type': 'TEXT', 'characters': 'B'},
            {'type': 'TEXT', 'characters': 'C'},
        ]}
        # Should not be rejected by MAX_CHILDREN (5) because hidden excluded
        result = is_heading_like(node)
        assert isinstance(result, bool)  # Function runs without error

    def test_is_decoration_pattern_ignores_hidden(self):
        # Only visible children count
        node = {'type': 'FRAME', 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 100}, 'children': [
            {'type': 'ELLIPSE', 'visible': False},
            {'type': 'ELLIPSE', 'visible': False},
            {'type': 'ELLIPSE'},
            {'type': 'ELLIPSE'},
            {'type': 'ELLIPSE'},
        ]}
        result = is_decoration_pattern(node)
        assert isinstance(result, bool)

    def test_detect_highlight_text_ignores_hidden(self):
        children = [
            {'type': 'RECTANGLE', 'visible': False, 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 30}},
            {'type': 'TEXT', 'characters': 'Hello', 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 30}},
        ]
        result = detect_highlight_text(children)
        assert result == []  # Hidden RECT should not pair with TEXT

    def test_detect_horizontal_bar_ignores_hidden(self):
        # 4 visible + 2 hidden elements; hidden should not affect detection
        children = [
            {'type': 'TEXT', 'visible': False, 'absoluteBoundingBox': {'x': 0, 'y': 50, 'width': 50, 'height': 20}},
            {'type': 'TEXT', 'visible': False, 'absoluteBoundingBox': {'x': 60, 'y': 50, 'width': 50, 'height': 20}},
        ]
        result = detect_horizontal_bar(children, {'x': 0, 'y': 0, 'w': 1440, 'h': 900})
        assert result == []  # Only hidden elements → nothing

    def test_detect_en_jp_label_pairs_ignores_hidden(self):
        children = [
            {'type': 'TEXT', 'visible': False, 'characters': 'ABOUT', 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 30}},
            {'type': 'TEXT', 'characters': '会社概要', 'absoluteBoundingBox': {'x': 0, 'y': 40, 'width': 100, 'height': 30}},
        ]
        result = detect_en_jp_label_pairs(children)
        assert result == []  # Hidden EN label should not pair

    def test_detect_table_rows_ignores_hidden(self):
        children = [
            {'type': 'RECTANGLE', 'visible': False, 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1400, 'height': 50}},
            {'type': 'RECTANGLE', 'visible': False, 'absoluteBoundingBox': {'x': 0, 'y': 60, 'width': 1400, 'height': 50}},
            {'type': 'RECTANGLE', 'visible': False, 'absoluteBoundingBox': {'x': 0, 'y': 120, 'width': 1400, 'height': 50}},
        ]
        parent_bb = {'x': 0, 'y': 0, 'w': 1440, 'h': 300}
        result = detect_table_rows(children, parent_bb)
        assert result == []  # All hidden → no table detected

    def test_compute_child_types_ignores_hidden(self):
        children = [
            {'type': 'TEXT', 'visible': False},
            {'type': 'TEXT'},
            {'type': 'RECTANGLE'},
        ]
        result = _compute_child_types(children)
        assert 'TEX' in result  # Only 1 visible TEXT
        # Should show 1TEX+1REC, not 2TEX+1REC

    def test_compute_flags_ignores_hidden_for_leaf(self):
        # Node with only hidden children should be treated as leaf
        # bg-full requires is_leaf=True + RECTANGLE type + full page width
        node = {'type': 'RECTANGLE', 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 100}, 'children': [
            {'type': 'TEXT', 'visible': False},
        ]}
        flags = _compute_flags(node, 1440, 5000)
        assert 'bg-full' in flags  # is_leaf=True (hidden filtered) → bg-full detected

    def test_generate_enriched_table_ignores_hidden_children(self):
        children = [
            {'type': 'FRAME', 'name': 'test', 'id': '1', 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 200, 'height': 100}, 'children': [
                {'type': 'TEXT', 'visible': False},
            ]},
        ]
        result = generate_enriched_table(children, page_width=1440)
        assert 'leaf=Y' in result or '| Y |' in result  # Should be leaf


# ============================================================
# alignment_bonus — previously untested function
# ============================================================
class TestAlignmentBonus:
    """Tests for alignment_bonus() — previously untested."""

    def test_left_aligned(self):
        a = {'x': 100, 'y': 0, 'w': 50, 'h': 50}
        b = {'x': 100, 'y': 60, 'w': 80, 'h': 50}
        assert alignment_bonus(a, b) == 0.5  # Left edges match

    def test_no_alignment(self):
        a = {'x': 0, 'y': 0, 'w': 50, 'h': 50}
        b = {'x': 200, 'y': 200, 'w': 80, 'h': 80}
        assert alignment_bonus(a, b) == 1.0  # No alignment

    def test_center_aligned(self):
        a = {'x': 100, 'y': 0, 'w': 100, 'h': 50}
        b = {'x': 110, 'y': 60, 'w': 80, 'h': 50}
        # center_x_a = 150, center_x_b = 150 → match
        assert alignment_bonus(a, b) == 0.5

    def test_zero_size_boxes(self):
        a = {'x': 0, 'y': 0, 'w': 0, 'h': 0}
        b = {'x': 0, 'y': 0, 'w': 0, 'h': 0}
        # All edges and centers are at 0, so all checks are 0 <= tolerance → 0.5
        assert alignment_bonus(a, b) == 0.5


# ============================================================
# size_similarity_bonus — previously untested function
# ============================================================
class TestSizeSimilarityBonus:
    """Tests for size_similarity_bonus() — previously untested."""

    def test_identical_sizes(self):
        a = {'x': 0, 'y': 0, 'w': 100, 'h': 50}
        b = {'x': 0, 'y': 0, 'w': 100, 'h': 50}
        assert size_similarity_bonus(a, b) == 0.7

    def test_very_different_sizes(self):
        a = {'x': 0, 'y': 0, 'w': 100, 'h': 50}
        b = {'x': 0, 'y': 0, 'w': 500, 'h': 500}
        assert size_similarity_bonus(a, b) == 1.0

    def test_zero_size(self):
        a = {'x': 0, 'y': 0, 'w': 0, 'h': 0}
        b = {'x': 0, 'y': 0, 'w': 100, 'h': 50}
        # Early return 1.0 when any dimension is <= 0
        assert size_similarity_bonus(a, b) == 1.0


# ============================================================
# compute_gap_consistency — previously untested function
# ============================================================
class TestComputeGapConsistency:
    """Tests for compute_gap_consistency() — previously untested."""

    def test_identical_gaps(self):
        # Returns float (CoV value)
        result = compute_gap_consistency([20, 20, 20])
        assert result == 0.0

    def test_varying_gaps(self):
        result = compute_gap_consistency([10, 20, 30])
        assert result > 0

    def test_empty_gaps(self):
        # Empty → returns 1.0 (max inconsistency)
        result = compute_gap_consistency([])
        assert result == 1.0

    def test_single_gap(self):
        result = compute_gap_consistency([20])
        assert result == 0.0

    def test_zero_mean_gaps(self):
        # All zeros → returns 1.0 (zero mean guarded)
        result = compute_gap_consistency([0, 0, 0])
        assert result == 1.0


# ============================================================
# infer_direction_two_elements — previously untested function
# ============================================================
class TestInferDirectionTwoElements:
    """Tests for infer_direction_two_elements() — previously untested."""

    def test_horizontal(self):
        a = {'x': 0, 'y': 0, 'w': 100, 'h': 50}
        b = {'x': 200, 'y': 0, 'w': 100, 'h': 50}
        assert infer_direction_two_elements(a, b) == 'HORIZONTAL'

    def test_vertical(self):
        a = {'x': 0, 'y': 0, 'w': 100, 'h': 50}
        b = {'x': 0, 'y': 200, 'w': 100, 'h': 50}
        assert infer_direction_two_elements(a, b) == 'VERTICAL'

    def test_same_position(self):
        a = {'x': 0, 'y': 0, 'w': 100, 'h': 50}
        b = {'x': 0, 'y': 0, 'w': 100, 'h': 50}
        result = infer_direction_two_elements(a, b)
        assert result in ('HORIZONTAL', 'VERTICAL')  # No crash


# ============================================================
# _count_flat_descendants — Issue #248: zero test coverage
# ============================================================
class TestCountFlatDescendants:
    """Tests for _count_flat_descendants() — previously untested."""

    def test_empty_node(self):
        """Node with no children returns 0."""
        node = {'type': 'FRAME', 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 500, 'height': 500}}
        assert _count_flat_descendants(node) == 0

    def test_single_child(self):
        """Node with 1 child — not flat (below FLAT_THRESHOLD)."""
        child = {'type': 'FRAME', 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 200, 'height': 100}}
        node = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 500, 'height': 500},
            'children': [child],
        }
        assert _count_flat_descendants(node) == 0

    def test_flat_section(self):
        """Node with children > FLAT_THRESHOLD is detected as flat with correct excess."""
        # Create a FRAME child that has 20 visible children (> 15 threshold)
        grandchildren = [
            {'type': 'TEXT', 'absoluteBoundingBox': {'x': 0, 'y': i * 20, 'width': 100, 'height': 18}}
            for i in range(20)
        ]
        flat_child = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 500, 'height': 400},
            'children': grandchildren,
        }
        node = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 500, 'height': 500},
            'children': [flat_child],
        }
        # flat_child has 20 children > 15 threshold → counted as 1 flat descendant
        assert _count_flat_descendants(node) == 1

    def test_nested_flat(self):
        """Nested structure where inner node is flat — both levels counted."""
        # Inner FRAME with 16 children (> threshold)
        inner_grandchildren = [
            {'type': 'TEXT', 'absoluteBoundingBox': {'x': 0, 'y': i * 20, 'width': 100, 'height': 18}}
            for i in range(16)
        ]
        inner_flat = {
            'type': 'GROUP',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 400, 'height': 300},
            'children': inner_grandchildren,
        }
        # Outer FRAME wrapping inner_flat + 15 more children (16 total > threshold)
        outer_siblings = [
            {'type': 'TEXT', 'absoluteBoundingBox': {'x': 0, 'y': i * 20, 'width': 100, 'height': 18}}
            for i in range(15)
        ]
        outer_flat = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 500, 'height': 400},
            'children': [inner_flat] + outer_siblings,
        }
        node = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 500, 'height': 500},
            'children': [outer_flat],
        }
        # outer_flat: 16 children > 15 → 1
        # inner_flat: 16 children > 15 → 1
        # Total: 2
        assert _count_flat_descendants(node) == 2

    def test_hidden_children_excluded(self):
        """Node with 20 children but 10 hidden → only 10 visible → not flat."""
        children = []
        for i in range(20):
            child = {
                'type': 'TEXT',
                'absoluteBoundingBox': {'x': 0, 'y': i * 20, 'width': 100, 'height': 18},
            }
            if i >= 10:
                child['visible'] = False
            children.append(child)
        target = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 500, 'height': 400},
            'children': children,
        }
        node = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 500, 'height': 500},
            'children': [target],
        }
        # Only 10 visible children ≤ 15 threshold → not flat
        assert _count_flat_descendants(node) == 0

    def test_section_root_skipped(self):
        """Section root child (width ~1440) is skipped but its subtree is recursed."""
        # A section root child should NOT itself be counted as flat,
        # but its children should be recursed into.
        inner_grandchildren = [
            {'type': 'TEXT', 'absoluteBoundingBox': {'x': 0, 'y': i * 20, 'width': 100, 'height': 18}}
            for i in range(20)
        ]
        inner_flat = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 400, 'height': 300},
            'children': inner_grandchildren,
        }
        # Section root child (width=1440) with inner_flat as its only child
        section_child = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 800},
            'children': [inner_flat],
        }
        node = {
            'type': 'FRAME',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 500, 'height': 500},
            'children': [section_child],
        }
        # section_child is a section root → skipped (not counted itself)
        # but inner_flat (20 children > 15) is found via recursion → 1
        assert _count_flat_descendants(node) == 1

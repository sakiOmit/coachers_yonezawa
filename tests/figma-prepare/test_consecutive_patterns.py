"""Tests for consecutive pattern detection and absorbable elements."""
import pytest

from figma_utils import (
    CONSECUTIVE_PATTERN_MIN,
    detect_consecutive_similar,
    find_absorbable_elements,
    LOOSE_ABSORPTION_DISTANCE,
    LOOSE_ELEMENT_MAX_HEIGHT,
)


class TestDetectConsecutiveSimilar:
    def _make_frame(self, name, child_types):
        """Helper to create a frame with typed children."""
        return {
            "type": "FRAME", "name": name,
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 100, "height": 100},
            "children": [{"type": t, "name": f"{t} {i}"}
                         for i, t in enumerate(child_types)],
        }

    def test_three_consecutive_similar(self):
        """3 consecutive frames with FRAME:[FRAME,TEXT] → should group."""
        children = [
            self._make_frame("menu-1", ["FRAME", "TEXT"]),
            self._make_frame("menu-2", ["FRAME", "TEXT"]),
            self._make_frame("menu-3", ["FRAME", "TEXT"]),
        ]
        groups = detect_consecutive_similar(children)
        assert len(groups) == 1
        assert groups[0]['indices'] == [0, 1, 2]
        assert len(groups[0]['children']) == 3

    def test_non_consecutive_not_grouped(self):
        """Similar frames separated by a different frame → no group."""
        children = [
            self._make_frame("menu-1", ["FRAME", "TEXT"]),
            self._make_frame("different", ["IMAGE", "RECTANGLE"]),
            self._make_frame("menu-2", ["FRAME", "TEXT"]),
            self._make_frame("menu-3", ["FRAME", "TEXT"]),
        ]
        groups = detect_consecutive_similar(children)
        assert len(groups) == 0  # only 2 consecutive, not 3

    def test_too_few(self):
        """Only 2 similar frames → below min_count threshold."""
        children = [
            self._make_frame("a", ["TEXT"]),
            self._make_frame("b", ["TEXT"]),
        ]
        groups = detect_consecutive_similar(children)
        assert len(groups) == 0

    def test_custom_min_count(self):
        """Custom min_count=2 → group of 2."""
        children = [
            self._make_frame("a", ["TEXT"]),
            self._make_frame("b", ["TEXT"]),
        ]
        groups = detect_consecutive_similar(children, min_count=2)
        assert len(groups) == 1

    def test_mixed_but_similar(self):
        """Fuzzy match: FRAME:[FRAME,TEXT] vs FRAME:[TEXT,FRAME] → same hash (sorted)."""
        children = [
            self._make_frame("a", ["FRAME", "TEXT"]),
            self._make_frame("b", ["TEXT", "FRAME"]),
            self._make_frame("c", ["FRAME", "TEXT"]),
        ]
        groups = detect_consecutive_similar(children)
        assert len(groups) == 1

    def test_empty_children(self):
        """Empty input → no groups."""
        assert detect_consecutive_similar([]) == []

    def test_two_separate_runs(self):
        """Two separate consecutive runs with a break."""
        children = [
            self._make_frame("a1", ["TEXT"]),
            self._make_frame("a2", ["TEXT"]),
            self._make_frame("a3", ["TEXT"]),
            self._make_frame("break", ["IMAGE", "RECTANGLE", "VECTOR"]),
            self._make_frame("b1", ["TEXT"]),
            self._make_frame("b2", ["TEXT"]),
            self._make_frame("b3", ["TEXT"]),
        ]
        groups = detect_consecutive_similar(children)
        assert len(groups) == 2
        assert groups[0]['indices'] == [0, 1, 2]
        assert groups[1]['indices'] == [4, 5, 6]


# ============================================================
# find_absorbable_elements (Issue 167)
# ============================================================
class TestFindAbsorbableElements:
    def test_line_absorbed(self):
        """LINE element between two grouped frames → absorbed."""
        children = [
            {"type": "FRAME", "name": "section-a",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500}},
            {"type": "LINE", "name": "divider",
             "absoluteBoundingBox": {"x": 0, "y": 510, "width": 1440, "height": 1}},
            {"type": "FRAME", "name": "section-b",
             "absoluteBoundingBox": {"x": 0, "y": 530, "width": 1440, "height": 600}},
        ]
        group_indices = {0, 2}
        absorptions = find_absorbable_elements(children, group_indices)
        assert len(absorptions) == 1
        assert absorptions[0]['element_idx'] == 1
        assert absorptions[0]['target_group_idx'] in (0, 2)
        assert 'LINE' in absorptions[0]['reason']

    def test_small_rect_absorbed(self):
        """Small RECTANGLE (h=5) → absorbed as divider."""
        children = [
            {"type": "FRAME", "name": "section",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500}},
            {"type": "RECTANGLE", "name": "Rectangle 1",
             "absoluteBoundingBox": {"x": 0, "y": 510, "width": 1440, "height": 5}},
        ]
        group_indices = {0}
        absorptions = find_absorbable_elements(children, group_indices)
        assert len(absorptions) == 1
        assert absorptions[0]['element_idx'] == 1

    def test_large_frame_not_absorbed(self):
        """Large FRAME (h=500) → not absorbed."""
        children = [
            {"type": "FRAME", "name": "section",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500}},
            {"type": "FRAME", "name": "Frame 2",
             "absoluteBoundingBox": {"x": 0, "y": 510, "width": 1440, "height": 500},
             "children": [{"type": "TEXT"}]},
        ]
        group_indices = {0}
        absorptions = find_absorbable_elements(children, group_indices)
        assert len(absorptions) == 0

    def test_too_far_not_absorbed(self):
        """LINE element > LOOSE_ABSORPTION_DISTANCE away → not absorbed."""
        children = [
            {"type": "FRAME", "name": "section",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500}},
            {"type": "LINE", "name": "far-divider",
             "absoluteBoundingBox": {"x": 0, "y": 800, "width": 1440, "height": 1}},
        ]
        group_indices = {0}
        absorptions = find_absorbable_elements(children, group_indices)
        assert len(absorptions) == 0  # distance = 300 > 200

    def test_already_grouped_skipped(self):
        """Elements already in groups → skipped."""
        children = [
            {"type": "LINE", "name": "divider",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 1}},
        ]
        group_indices = {0}
        absorptions = find_absorbable_elements(children, group_indices)
        assert len(absorptions) == 0

    def test_empty_inputs(self):
        """Empty children → no absorptions."""
        assert find_absorbable_elements([], set()) == []

    def test_nearest_group_chosen(self):
        """LINE closer to group B than group A → absorbed into B."""
        children = [
            {"type": "FRAME", "name": "A",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 200}},
            {"type": "LINE", "name": "divider",
             "absoluteBoundingBox": {"x": 0, "y": 410, "width": 1440, "height": 1}},
            {"type": "FRAME", "name": "B",
             "absoluteBoundingBox": {"x": 0, "y": 420, "width": 1440, "height": 300}},
        ]
        group_indices = {0, 2}
        absorptions = find_absorbable_elements(children, group_indices)
        assert len(absorptions) == 1
        # B is at y=420, divider bottom is at y=411, distance = 9
        # A bottom is at y=200, divider top is at y=410, distance = 210 (> LOOSE_ABSORPTION_DISTANCE)
        # But both are checked; B is closer
        assert absorptions[0]['target_group_idx'] == 2

    def test_zone_bbox_absorbs_divider_within_span(self):
        """LINE inside a zone's vertical span -> absorbed via zone bbox even if
        individual members are far away (root-level divider fix)."""
        # Zone has two members: y=4269..4500 and y=4800..5015
        # LINE at y=4706 is between them but inside the zone's bounding box.
        children = [
            {"id": "m1", "type": "FRAME", "name": "zone-member-1",
             "absoluteBoundingBox": {"x": 0, "y": 4269, "width": 1440, "height": 231}},
            {"id": "d1", "type": "LINE", "name": "divider-28",
             "absoluteBoundingBox": {"x": 100, "y": 4706, "width": 1240, "height": 1}},
            {"id": "m2", "type": "FRAME", "name": "zone-member-2",
             "absoluteBoundingBox": {"x": 0, "y": 4800, "width": 1440, "height": 215}},
        ]
        group_indices = {0, 2}
        # Without candidate_groups: m1 bottom=4500, divider top=4706 => dist=206 > 200
        #   m2 top=4800, divider bottom=4707 => dist=93 < 200, so absorbed by member-level.
        absorptions_no_zone = find_absorbable_elements(children, group_indices)
        assert len(absorptions_no_zone) == 1

        # With candidate_groups: zone bbox y=4269..5015, divider center=4706.5 inside
        candidate_groups = [{"node_ids": ["m1", "m2"]}]
        absorptions_zone = find_absorbable_elements(children, group_indices, candidate_groups=candidate_groups)
        assert len(absorptions_zone) == 1
        assert absorptions_zone[0]['distance'] == 0.0

    def test_zone_bbox_absorbs_distant_divider(self):
        """LINE far from individual members but inside zone span -> absorbed."""
        # Zone members at y=100..300 and y=900..1100, divider at y=600
        # Member distances: 600-300=300 > 200, and 900-601=299 > 200
        # But zone spans 100..1100, so divider center y=600.5 is inside.
        children = [
            {"id": "a", "type": "FRAME", "name": "top-member",
             "absoluteBoundingBox": {"x": 0, "y": 100, "width": 1440, "height": 200}},
            {"id": "div", "type": "LINE", "name": "divider",
             "absoluteBoundingBox": {"x": 0, "y": 600, "width": 1440, "height": 1}},
            {"id": "b", "type": "FRAME", "name": "bottom-member",
             "absoluteBoundingBox": {"x": 0, "y": 900, "width": 1440, "height": 200}},
        ]
        group_indices = {0, 2}
        # Without zone: both distances > 200 -> not absorbed
        absorptions_no_zone = find_absorbable_elements(children, group_indices)
        assert len(absorptions_no_zone) == 0

        # With zone: center y=600.5 is within [100, 1100] -> absorbed
        candidate_groups = [{"node_ids": ["a", "b"]}]
        absorptions_zone = find_absorbable_elements(children, group_indices, candidate_groups=candidate_groups)
        assert len(absorptions_zone) == 1
        assert absorptions_zone[0]['distance'] == 0.0
        assert absorptions_zone[0]['element_idx'] == 1

    def test_zone_bbox_outside_not_absorbed(self):
        """LINE outside all zone bounding boxes and far from members -> not absorbed."""
        children = [
            {"id": "m1", "type": "FRAME", "name": "member",
             "absoluteBoundingBox": {"x": 0, "y": 100, "width": 1440, "height": 200}},
            {"id": "div", "type": "LINE", "name": "far-divider",
             "absoluteBoundingBox": {"x": 0, "y": 800, "width": 1440, "height": 1}},
        ]
        group_indices = {0}
        # Zone spans y=100..300, divider at y=800 is outside and 500px away
        candidate_groups = [{"node_ids": ["m1"]}]
        absorptions = find_absorbable_elements(children, group_indices, candidate_groups=candidate_groups)
        assert len(absorptions) == 0

    def test_zone_bbox_two_dividers_same_zone(self):
        """Two LINE elements within same zone span -> both absorbed."""
        children = [
            {"id": "m1", "type": "FRAME", "name": "section-top",
             "absoluteBoundingBox": {"x": 0, "y": 4000, "width": 1440, "height": 300}},
            {"id": "d1", "type": "LINE", "name": "divider-1",
             "absoluteBoundingBox": {"x": 100, "y": 4500, "width": 1240, "height": 1}},
            {"id": "d2", "type": "LINE", "name": "divider-2",
             "absoluteBoundingBox": {"x": 100, "y": 4700, "width": 1240, "height": 1}},
            {"id": "m2", "type": "FRAME", "name": "section-bottom",
             "absoluteBoundingBox": {"x": 0, "y": 4800, "width": 1440, "height": 300}},
        ]
        group_indices = {0, 3}
        candidate_groups = [{"node_ids": ["m1", "m2"]}]
        absorptions = find_absorbable_elements(children, group_indices, candidate_groups=candidate_groups)
        assert len(absorptions) == 2
        absorbed_indices = {a['element_idx'] for a in absorptions}
        assert absorbed_indices == {1, 2}

    def test_candidate_groups_none_backward_compat(self):
        """candidate_groups=None -> backward compatible member-level only."""
        children = [
            {"id": "s", "type": "FRAME", "name": "section",
             "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1440, "height": 500}},
            {"id": "d", "type": "LINE", "name": "divider",
             "absoluteBoundingBox": {"x": 0, "y": 510, "width": 1440, "height": 1}},
        ]
        group_indices = {0}
        absorptions = find_absorbable_elements(children, group_indices, candidate_groups=None)
        assert len(absorptions) == 1
        assert absorptions[0]['element_idx'] == 1

"""Tests for Stage C divider absorption and column validation."""
import pytest

from figma_utils import (
    absorb_stage_c_dividers,
    DIVIDER_MAX_HEIGHT,
    validate_column_consistency,
)


class TestAbsorbStageCDividers:
    """Issue #253: Absorb single-element divider groups into adjacent list-item groups."""

    def _make_node(self, nid, ntype, y, h=50, w=100):
        return {
            'id': nid,
            'type': ntype,
            'absoluteBoundingBox': {'x': 0, 'y': y, 'width': w, 'height': h},
        }

    def test_dividers_absorbed_into_preceding_list_items(self):
        """Dividers between list items should be absorbed into the preceding item."""
        node_lookup = {
            'item1-a': self._make_node('item1-a', 'FRAME', 0),
            'item1-b': self._make_node('item1-b', 'TEXT', 0),
            'div1': self._make_node('div1', 'VECTOR', 60, h=0),
            'item2-a': self._make_node('item2-a', 'FRAME', 80),
            'item2-b': self._make_node('item2-b', 'TEXT', 80),
            'div2': self._make_node('div2', 'VECTOR', 140, h=0),
            'item3-a': self._make_node('item3-a', 'FRAME', 160),
        }
        groups = [
            {'name': 'list-item-1', 'pattern': 'list', 'node_ids': ['item1-a', 'item1-b']},
            {'name': 'divider-1', 'pattern': 'single', 'node_ids': ['div1']},
            {'name': 'list-item-2', 'pattern': 'list', 'node_ids': ['item2-a', 'item2-b']},
            {'name': 'divider-2', 'pattern': 'single', 'node_ids': ['div2']},
            {'name': 'list-item-3', 'pattern': 'list', 'node_ids': ['item3-a']},
        ]
        result = absorb_stage_c_dividers(groups, node_lookup)
        assert len(result) == 3
        names = [g['name'] for g in result]
        assert 'divider-1' not in names
        assert 'divider-2' not in names
        assert 'div1' in result[0]['node_ids']
        assert 'div2' in result[1]['node_ids']

    def test_no_dividers_unchanged(self):
        """Groups without dividers should pass through unchanged."""
        node_lookup = {
            'a': self._make_node('a', 'FRAME', 0),
            'b': self._make_node('b', 'FRAME', 100),
        }
        groups = [
            {'name': 'group-1', 'pattern': 'list', 'node_ids': ['a']},
            {'name': 'group-2', 'pattern': 'list', 'node_ids': ['b']},
        ]
        result = absorb_stage_c_dividers(groups, node_lookup)
        assert len(result) == 2

    def test_rectangle_divider_absorbed(self):
        """Thin RECTANGLE (height <= DIVIDER_MAX_HEIGHT) should also be absorbed."""
        node_lookup = {
            'item': self._make_node('item', 'FRAME', 0),
            'rect_div': self._make_node('rect_div', 'RECTANGLE', 55, h=2),
            'item2': self._make_node('item2', 'FRAME', 100),
        }
        groups = [
            {'name': 'list-item-1', 'pattern': 'list', 'node_ids': ['item']},
            {'name': 'divider', 'pattern': 'single', 'node_ids': ['rect_div']},
            {'name': 'list-item-2', 'pattern': 'list', 'node_ids': ['item2']},
        ]
        result = absorb_stage_c_dividers(groups, node_lookup)
        assert len(result) == 2
        # rect_div (y=55) is closer to item (y=0, center=25) than item2 (y=100, center=125)
        assert 'rect_div' in result[0]['node_ids']

    def test_tall_rectangle_not_absorbed(self):
        """Tall RECTANGLE (height > LOOSE_ELEMENT_MAX_HEIGHT) should NOT be absorbed."""
        node_lookup = {
            'item': self._make_node('item', 'FRAME', 0),
            'big_rect': self._make_node('big_rect', 'RECTANGLE', 55, h=100),
            'item2': self._make_node('item2', 'FRAME', 200),
        }
        groups = [
            {'name': 'list-item-1', 'pattern': 'list', 'node_ids': ['item']},
            {'name': 'bg-rect', 'pattern': 'single', 'node_ids': ['big_rect']},
            {'name': 'list-item-2', 'pattern': 'list', 'node_ids': ['item2']},
        ]
        result = absorb_stage_c_dividers(groups, node_lookup)
        assert len(result) == 3

    def test_empty_groups(self):
        """Empty or single group should return unchanged."""
        assert absorb_stage_c_dividers([], {}) == []
        single = [{'name': 'g', 'pattern': 'list', 'node_ids': ['a']}]
        assert absorb_stage_c_dividers(single, {}) == single

    def test_line_type_absorbed(self):
        """LINE type divider should be absorbed."""
        node_lookup = {
            'item': self._make_node('item', 'FRAME', 0),
            'line': self._make_node('line', 'LINE', 55, h=1),
            'item2': self._make_node('item2', 'FRAME', 80),
        }
        groups = [
            {'name': 'list-item-1', 'pattern': 'list', 'node_ids': ['item']},
            {'name': 'divider', 'pattern': 'single', 'node_ids': ['line']},
            {'name': 'list-item-2', 'pattern': 'list', 'node_ids': ['item2']},
        ]
        result = absorb_stage_c_dividers(groups, node_lookup)
        assert len(result) == 2
        assert 'line' in result[0]['node_ids']

    def test_all_dividers(self):
        """All groups are dividers -> no absorption possible, return as-is."""
        node_lookup = {
            'div1': self._make_node('div1', 'VECTOR', 0, h=1),
            'div2': self._make_node('div2', 'LINE', 50, h=1),
            'div3': self._make_node('div3', 'VECTOR', 100, h=0),
        }
        groups = [
            {'name': 'divider-1', 'pattern': 'single', 'node_ids': ['div1']},
            {'name': 'divider-2', 'pattern': 'single', 'node_ids': ['div2']},
            {'name': 'divider-3', 'pattern': 'single', 'node_ids': ['div3']},
        ]
        result = absorb_stage_c_dividers(groups, node_lookup)
        # No non-divider groups to absorb into, so all remain
        assert len(result) == 3
        assert [g['name'] for g in result] == ['divider-1', 'divider-2', 'divider-3']

    def test_multiple_consecutive_dividers(self):
        """Two consecutive divider groups -> both absorbed into nearest non-divider."""
        node_lookup = {
            'item1': self._make_node('item1', 'FRAME', 0),
            'div1': self._make_node('div1', 'LINE', 55, h=1),
            'div2': self._make_node('div2', 'VECTOR', 60, h=0),
            'item2': self._make_node('item2', 'FRAME', 100),
        }
        groups = [
            {'name': 'list-item-1', 'pattern': 'list', 'node_ids': ['item1']},
            {'name': 'divider-1', 'pattern': 'single', 'node_ids': ['div1']},
            {'name': 'divider-2', 'pattern': 'single', 'node_ids': ['div2']},
            {'name': 'list-item-2', 'pattern': 'list', 'node_ids': ['item2']},
        ]
        result = absorb_stage_c_dividers(groups, node_lookup)
        assert len(result) == 2
        names = [g['name'] for g in result]
        assert 'divider-1' not in names
        assert 'divider-2' not in names

    def test_malformed_node_ids(self):
        """Group with missing node_ids key -> should not crash."""
        node_lookup = {
            'item': self._make_node('item', 'FRAME', 0),
        }
        groups = [
            {'name': 'list-item-1', 'pattern': 'list', 'node_ids': ['item']},
            {'name': 'divider-bad', 'pattern': 'single'},  # missing node_ids
        ]
        # Should not raise an exception
        result = absorb_stage_c_dividers(groups, node_lookup)
        assert isinstance(result, list)


# ============================================================
# validate_column_consistency
# ============================================================
class TestValidateColumnConsistency:
    """Tests for validate_column_consistency (Issue 256)."""

    @staticmethod
    def _make_node(node_id, x, y=0, w=100, h=50):
        """Create a minimal node with absoluteBoundingBox."""
        return {
            'id': node_id,
            'absoluteBoundingBox': {'x': x, 'y': y, 'width': w, 'height': h},
        }

    def test_no_split_needed(self):
        """All nodes on same side — no split needed."""
        node_lookup = {
            'a': self._make_node('a', x=0, w=100),
            'b': self._make_node('b', x=50, w=100),
            'c': self._make_node('c', x=10, w=80),
            # Need right-side nodes to establish two-column layout
            'd': self._make_node('d', x=800, w=100),
        }
        groups = [
            {'name': 'group-left', 'pattern': 'list', 'node_ids': ['a', 'b', 'c']},
            {'name': 'group-right', 'pattern': 'list', 'node_ids': ['d']},
        ]
        result = validate_column_consistency(groups, node_lookup)
        # group-left has all nodes on left side — no split
        # group-right has single node — no split
        assert len(result) == 2
        assert result[0]['name'] == 'group-left'
        assert result[1]['name'] == 'group-right'

    def test_splits_cross_column(self):
        """Group with nodes on both L and R sides should split into -left/-right."""
        node_lookup = {
            'l1': self._make_node('l1', x=0, w=100),
            'l2': self._make_node('l2', x=50, w=100),
            'r1': self._make_node('r1', x=800, w=100),
            'r2': self._make_node('r2', x=850, w=100),
        }
        groups = [
            {'name': 'content', 'pattern': 'zone', 'node_ids': ['l1', 'l2', 'r1', 'r2']},
        ]
        result = validate_column_consistency(groups, node_lookup)
        assert len(result) == 2
        left_group = result[0]
        right_group = result[1]
        assert left_group['name'] == 'content-left'
        assert right_group['name'] == 'content-right'
        assert 'l1' in left_group['node_ids']
        assert 'l2' in left_group['node_ids']
        assert 'r1' in right_group['node_ids']
        assert 'r2' in right_group['node_ids']

    def test_full_width_assigned_to_left(self):
        """Full-width elements (>80% span) go to left group."""
        # Span: 0 to 1000 => x_span=1000, 80% = 800
        node_lookup = {
            'l1': self._make_node('l1', x=0, w=100),
            'r1': self._make_node('r1', x=900, w=100),
            'fw': self._make_node('fw', x=0, w=900),  # 900 >= 1000*0.8 = full-width
        }
        groups = [
            {'name': 'section', 'pattern': 'zone', 'node_ids': ['l1', 'r1', 'fw']},
        ]
        result = validate_column_consistency(groups, node_lookup)
        assert len(result) == 2
        left_group = result[0]
        right_group = result[1]
        assert left_group['name'] == 'section-left'
        assert 'fw' in left_group['node_ids']
        assert 'l1' in left_group['node_ids']
        assert right_group['name'] == 'section-right'
        assert 'r1' in right_group['node_ids']

    def test_empty_groups(self):
        """Empty input returns empty (or unchanged)."""
        assert validate_column_consistency([], {}) == []
        assert validate_column_consistency([], {'a': {}}) == []

    def test_no_node_lookup(self):
        """None node_lookup returns groups unchanged."""
        groups = [
            {'name': 'g', 'pattern': 'list', 'node_ids': ['a', 'b']},
        ]
        result = validate_column_consistency(groups, None)
        assert result == groups

    def test_single_column_layout(self):
        """All nodes clustered on one side — no two-column detected."""
        # All nodes in a narrow X range — not a two-column layout
        node_lookup = {
            'a': self._make_node('a', x=100, w=200),
            'b': self._make_node('b', x=120, w=180),
            'c': self._make_node('c', x=110, w=190),
        }
        groups = [
            {'name': 'content', 'pattern': 'zone', 'node_ids': ['a', 'b', 'c']},
        ]
        result = validate_column_consistency(groups, node_lookup)
        # No two-column layout detected, groups returned unchanged
        assert len(result) == 1
        assert result[0]['name'] == 'content'
        assert result[0]['node_ids'] == ['a', 'b', 'c']

    def test_missing_col_field(self):
        """Nodes without 'Col' in enriched data -> should not crash."""
        # Nodes exist in lookup but have no 'Col' metadata
        node_lookup = {
            'a': {'id': 'a', 'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 50}},
            'b': {'id': 'b', 'absoluteBoundingBox': {'x': 800, 'y': 0, 'width': 100, 'height': 50}},
        }
        groups = [
            {'name': 'mixed', 'pattern': 'zone', 'node_ids': ['a', 'b']},
        ]
        # Should not raise KeyError or similar
        result = validate_column_consistency(groups, node_lookup)
        assert isinstance(result, list)

    def test_single_group_consistent_cols(self):
        """Single group with all nodes on one side -> no violations."""
        node_lookup = {
            'a': self._make_node('a', x=10, w=100),
            'b': self._make_node('b', x=20, w=80),
            'c': self._make_node('c', x=15, w=90),
        }
        groups = [
            {'name': 'left-content', 'pattern': 'list', 'node_ids': ['a', 'b', 'c']},
        ]
        result = validate_column_consistency(groups, node_lookup)
        assert len(result) == 1
        assert result[0]['name'] == 'left-content'
        assert result[0]['node_ids'] == ['a', 'b', 'c']

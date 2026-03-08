"""Tests for adaptive proximity gap (Adaptive Proximity Gap feature)."""
import pytest
from figma_utils.grouping_proximity import compute_adaptive_gap, detect_proximity_groups
from figma_utils.constants import PROXIMITY_GAP


def _node(node_id, x, y, w=100, h=50):
    return {
        'id': node_id, 'type': 'FRAME', 'name': f'Frame {node_id}', 'visible': True,
        'absoluteBoundingBox': {'x': x, 'y': y, 'width': w, 'height': h},
        'children': [],
    }


class TestComputeAdaptiveGap:
    def test_returns_default_for_few_children(self):
        """< 3 children -> use default gap"""
        children = [_node('1', 0, 0), _node('2', 0, 100)]
        assert compute_adaptive_gap(children) == PROXIMITY_GAP

    def test_tight_spacing(self):
        """Elements 12px apart -> gap ~8-12px"""
        children = [
            _node('1', 0, 0, 100, 50),
            _node('2', 0, 62, 100, 50),   # gap=12
            _node('3', 0, 124, 100, 50),  # gap=12
            _node('4', 0, 186, 100, 50),  # gap=12
        ]
        gap = compute_adaptive_gap(children)
        assert 8 <= gap <= 12

    def test_wide_spacing(self):
        """Elements 64px apart -> gap ~48-52px"""
        children = [
            _node('1', 0, 0, 100, 50),
            _node('2', 0, 114, 100, 50),  # gap=64
            _node('3', 0, 228, 100, 50),  # gap=64
            _node('4', 0, 342, 100, 50),  # gap=64
        ]
        gap = compute_adaptive_gap(children)
        assert 40 <= gap <= 56

    def test_default_spacing_near_24(self):
        """Elements ~30px apart -> gap near default 24"""
        children = [
            _node('1', 0, 0, 100, 50),
            _node('2', 0, 80, 100, 50),   # gap=30
            _node('3', 0, 160, 100, 50),  # gap=30
            _node('4', 0, 240, 100, 50),  # gap=30
        ]
        gap = compute_adaptive_gap(children)
        assert 20 <= gap <= 28

    def test_minimum_gap_floor(self):
        """Gap never goes below 8px"""
        children = [
            _node('1', 0, 0, 100, 50),
            _node('2', 0, 52, 100, 50),   # gap=2
            _node('3', 0, 104, 100, 50),  # gap=2
            _node('4', 0, 156, 100, 50),  # gap=2
        ]
        gap = compute_adaptive_gap(children)
        assert gap >= 8

    def test_maximum_gap_ceiling(self):
        """Gap never exceeds 200px"""
        children = [
            _node('1', 0, 0, 100, 50),
            _node('2', 0, 550, 100, 50),  # gap=500
            _node('3', 0, 1100, 100, 50), # gap=500
            _node('4', 0, 1650, 100, 50), # gap=500
        ]
        gap = compute_adaptive_gap(children)
        assert gap <= 200

    def test_custom_default_gap(self):
        """Custom default_gap used when < 3 children"""
        children = [_node('1', 0, 0)]
        assert compute_adaptive_gap(children, default_gap=48) == 48

    def test_empty_children(self):
        assert compute_adaptive_gap([]) == PROXIMITY_GAP

    def test_horizontal_layout(self):
        """Horizontal spacing also detected"""
        children = [
            _node('1', 0, 0, 80, 50),
            _node('2', 100, 0, 80, 50),   # h_gap=20
            _node('3', 200, 0, 80, 50),   # h_gap=20
            _node('4', 300, 0, 80, 50),   # h_gap=20
        ]
        gap = compute_adaptive_gap(children)
        assert 12 <= gap <= 20

    def test_grid_snap(self):
        """Result is snapped to GRID_SNAP (4px)"""
        children = [
            _node('1', 0, 0, 100, 50),
            _node('2', 0, 67, 100, 50),   # gap=17
            _node('3', 0, 134, 100, 50),  # gap=17
            _node('4', 0, 201, 100, 50),  # gap=17
        ]
        gap = compute_adaptive_gap(children)
        assert gap % 4 == 0  # snapped to 4px grid


class TestDetectProximityGroupsWithGap:
    def test_explicit_gap_overrides_adaptive(self):
        """When gap is explicitly passed, uses that instead of adaptive"""
        children = [
            _node('1', 0, 0, 100, 50),
            _node('2', 0, 80, 100, 50),   # gap=30
            _node('3', 0, 200, 100, 50),  # gap=70 (far away)
        ]
        # With tight gap=20: nodes 1,2 might group, 3 isolated
        # With wide gap=100: all three grouped
        result_tight = detect_proximity_groups(children, gap=20)
        result_wide = detect_proximity_groups(children, gap=100)

        tight_ids = set()
        for cand in result_tight:
            tight_ids.update(cand.get('node_ids', []))

        wide_ids = set()
        for cand in result_wide:
            wide_ids.update(cand.get('node_ids', []))

        # Wide gap should group more nodes
        assert len(wide_ids) >= len(tight_ids)

    def test_none_gap_uses_adaptive(self):
        """gap=None triggers adaptive computation"""
        children = [
            _node('1', 0, 0, 100, 50),
            _node('2', 0, 60, 100, 50),   # gap=10
            _node('3', 0, 120, 100, 50),  # gap=10
        ]
        # Should not crash, should use adaptive gap
        result = detect_proximity_groups(children, gap=None)
        assert isinstance(result, list)

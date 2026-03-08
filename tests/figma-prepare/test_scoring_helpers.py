"""Tests for scoring/helper functions: alignment, size similarity, gap consistency, direction, flat descendants."""
import json
import os
import pytest

from helpers import run_script, write_fixture

from figma_utils import (
    _count_flat_descendants,
    alignment_bonus,
    compute_gap_consistency,
    infer_direction_two_elements,
    size_similarity_bonus,
)


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

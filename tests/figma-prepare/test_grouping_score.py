"""Tests for grouping score, structure similarity, and layout detection."""
import pytest

from figma_utils import (
    alignment_bonus,
    compute_gap_consistency,
    compute_grouping_score,
    detect_regular_spacing,
    detect_space_between,
    detect_wrap,
    infer_direction_two_elements,
    size_similarity_bonus,
    snap,
    structure_hash,
    structure_similarity,
)


class TestComputeGroupingScore:
    A = {"x": 0, "y": 0, "w": 100, "h": 50}

    def test_identical(self):
        assert compute_grouping_score(self.A, self.A) == 1.0

    def test_close(self):
        b = {"x": 110, "y": 0, "w": 100, "h": 50}
        assert compute_grouping_score(self.A, b, gap=24) >= 0.5

    def test_far(self):
        far = {"x": 500, "y": 0, "w": 100, "h": 50}
        assert compute_grouping_score(self.A, far) < 0.1

    def test_aligned_beats_unaligned(self):
        aligned = {"x": 0, "y": 70, "w": 100, "h": 50}
        unaligned = {"x": 30, "y": 70, "w": 60, "h": 50}
        assert compute_grouping_score(self.A, aligned) >= compute_grouping_score(self.A, unaligned)

    def test_same_size_beats_diff(self):
        same = {"x": 130, "y": 0, "w": 100, "h": 50}
        diff = {"x": 130, "y": 0, "w": 200, "h": 100}
        assert compute_grouping_score(self.A, same) >= compute_grouping_score(self.A, diff)

    def test_alignment_bonus(self):
        aligned = {"x": 0, "y": 70, "w": 100, "h": 50}
        assert alignment_bonus(self.A, aligned) == 0.5

    def test_size_similarity_bonus(self):
        same = {"x": 130, "y": 0, "w": 100, "h": 50}
        diff = {"x": 130, "y": 0, "w": 200, "h": 100}
        assert size_similarity_bonus(self.A, same) == 0.7
        assert size_similarity_bonus(self.A, diff) == 1.0

    def test_zero_size(self):
        zero = {"x": 0, "y": 0, "w": 0, "h": 0}
        assert size_similarity_bonus(self.A, zero) == 1.0

    def test_zero_gap(self):
        """Issue 136: gap=0 returns 0.0 for non-overlapping boxes."""
        b = {"x": 200, "y": 0, "w": 100, "h": 50}
        assert compute_grouping_score(self.A, b, gap=0) == 0.0


# ============================================================
# structure_similarity / detect_regular_spacing (Area 2)
# ============================================================
class TestStructureSimilarity:
    def test_identical(self):
        assert structure_similarity("FRAME:[TEXT,TEXT]", "FRAME:[TEXT,TEXT]") == 1.0

    def test_different(self):
        assert structure_similarity("FRAME:[TEXT]", "FRAME:[IMAGE]") == 0.0

    def test_partial(self):
        s = structure_similarity("FRAME:[IMAGE,TEXT,TEXT]", "FRAME:[IMAGE,TEXT,RECTANGLE]")
        assert 0.3 < s < 0.9

    def test_leaf_same(self):
        assert structure_similarity("TEXT", "TEXT") == 1.0

    def test_leaf_diff(self):
        assert structure_similarity("TEXT", "IMAGE") == 0.0

    def test_card_variants(self):
        s = structure_similarity("FRAME:[IMAGE,TEXT,TEXT,FRAME]", "FRAME:[RECTANGLE,TEXT,TEXT,FRAME]")
        assert s >= 0.5

    def test_empty_children(self):
        assert structure_similarity("FRAME:[]", "FRAME:[]") == 1.0


class TestDetectRegularSpacing:
    def test_even(self):
        boxes = [{"x": i * 120, "y": 0, "w": 100, "h": 50} for i in range(5)]
        assert detect_regular_spacing(boxes) is True

    def test_too_few(self):
        boxes = [{"x": i * 120, "y": 0, "w": 100, "h": 50} for i in range(2)]
        assert detect_regular_spacing(boxes) is False

    def test_irregular(self):
        boxes = [
            {"x": 0, "y": 0, "w": 100, "h": 50},
            {"x": 110, "y": 0, "w": 100, "h": 50},
            {"x": 500, "y": 0, "w": 100, "h": 50},
        ]
        assert detect_regular_spacing(boxes) is False

    def test_vertical(self):
        boxes = [{"x": 0, "y": i * 80, "w": 100, "h": 60} for i in range(4)]
        assert detect_regular_spacing(boxes) is True

    def test_all_zero_gaps(self):
        """Edge-to-edge elements (gap=0) should be perfectly regular."""
        boxes = [
            {"x": 0, "y": 0, "w": 100, "h": 50},
            {"x": 100, "y": 0, "w": 100, "h": 50},
            {"x": 200, "y": 0, "w": 100, "h": 50},
        ]
        assert detect_regular_spacing(boxes) is True

    def test_mixed_zero_positive_gaps(self):
        """Mix of zero and positive gaps should be irregular."""
        boxes = [
            {"x": 0, "y": 0, "w": 100, "h": 50},
            {"x": 100, "y": 0, "w": 100, "h": 50},   # gap=0
            {"x": 250, "y": 0, "w": 100, "h": 50},   # gap=50
            {"x": 350, "y": 0, "w": 100, "h": 50},   # gap=0
        ]
        assert detect_regular_spacing(boxes) is False


# ============================================================
# structure_hash (Issue 144)
# ============================================================
class TestStructureHash:
    def test_leaf(self):
        assert structure_hash({"type": "TEXT"}) == "TEXT"

    def test_empty_children(self):
        assert structure_hash({"type": "IMAGE", "children": []}) == "IMAGE"

    def test_missing_type(self):
        assert structure_hash({}) == "UNKNOWN"

    def test_sorted_children(self):
        node = {"type": "FRAME", "children": [
            {"type": "TEXT"}, {"type": "IMAGE"}, {"type": "TEXT"},
        ]}
        assert structure_hash(node) == "FRAME:[IMAGE,TEXT,TEXT]"

    def test_single_child(self):
        node = {"type": "FRAME", "children": [{"type": "RECTANGLE"}]}
        assert structure_hash(node) == "FRAME:[RECTANGLE]"

    def test_instance(self):
        node = {"type": "INSTANCE", "children": [{"type": "FRAME"}, {"type": "TEXT"}]}
        assert structure_hash(node) == "INSTANCE:[FRAME,TEXT]"

    def test_children_but_no_type(self):
        """Node with children but missing type field produces 'UNKNOWN:[CHILD_TYPES]' hash."""
        node = {"children": [{"type": "TEXT"}, {"type": "TEXT"}]}
        result = structure_hash(node)
        assert result == "UNKNOWN:[TEXT,TEXT]"


# ============================================================
# infer_direction_two / wrap / space_between (Area 4)
# ============================================================
class TestInferDirectionTwo:
    def test_horizontal(self):
        a = {"x": 0, "y": 0, "w": 100, "h": 50}
        b = {"x": 120, "y": 0, "w": 100, "h": 50}
        assert infer_direction_two_elements(a, b) == "HORIZONTAL"

    def test_vertical(self):
        a = {"x": 0, "y": 0, "w": 100, "h": 50}
        b = {"x": 0, "y": 70, "w": 100, "h": 50}
        assert infer_direction_two_elements(a, b) == "VERTICAL"

    def test_diagonal_horizontal(self):
        a = {"x": 0, "y": 0, "w": 50, "h": 50}
        b = {"x": 200, "y": 30, "w": 50, "h": 50}
        assert infer_direction_two_elements(a, b) == "HORIZONTAL"

    def test_diagonal_vertical(self):
        a = {"x": 0, "y": 0, "w": 50, "h": 50}
        b = {"x": 30, "y": 200, "w": 50, "h": 50}
        assert infer_direction_two_elements(a, b) == "VERTICAL"

    def test_same_position(self):
        s = {"x": 0, "y": 0, "w": 50, "h": 50}
        assert infer_direction_two_elements(s, s) == "VERTICAL"


class TestDetectWrap:
    BOXES = [
        {"x": 0, "y": 0, "w": 100, "h": 50},
        {"x": 120, "y": 0, "w": 100, "h": 50},
        {"x": 0, "y": 70, "w": 100, "h": 50},
        {"x": 120, "y": 70, "w": 100, "h": 50},
    ]

    def test_wrap_detected(self):
        assert detect_wrap(self.BOXES, "HORIZONTAL") is True

    def test_too_few(self):
        assert detect_wrap(self.BOXES[:3], "HORIZONTAL") is False

    def test_single_row(self):
        row = [{"x": i * 120, "y": 0, "w": 100, "h": 50} for i in range(5)]
        assert detect_wrap(row, "HORIZONTAL") is False

    def test_vertical_always_false(self):
        assert detect_wrap(self.BOXES, "VERTICAL") is False

    def test_row_tolerance_zero_uses_default(self):
        """Issue #244: row_tolerance=0 should not raise ZeroDivisionError."""
        assert detect_wrap(self.BOXES, "HORIZONTAL", row_tolerance=0) is True

    def test_rounding_boundary_no_false_wrap(self):
        """Issue #251: Elements near rounding boundary should not create false rows.
        Y values 100, 119, 120, 139 with tolerance=20 are all within 39px spread
        — a single row, not multiple rows."""
        boxes = [
            {"x": 0, "y": 100, "w": 100, "h": 50},
            {"x": 120, "y": 119, "w": 100, "h": 50},
            {"x": 240, "y": 120, "w": 100, "h": 50},
            {"x": 360, "y": 139, "w": 100, "h": 50},
        ]
        assert detect_wrap(boxes, "HORIZONTAL", row_tolerance=20) is False

    def test_real_wrap_still_detected(self):
        """Issue #251: Real wrap (large Y gap) should still be detected."""
        boxes = [
            {"x": 0, "y": 0, "w": 100, "h": 50},
            {"x": 120, "y": 0, "w": 100, "h": 50},
            {"x": 0, "y": 100, "w": 100, "h": 50},
            {"x": 120, "y": 100, "w": 100, "h": 50},
        ]
        assert detect_wrap(boxes, "HORIZONTAL", row_tolerance=20) is True


class TestDetectSpaceBetween:
    def test_touching_edges(self):
        frame = {"x": 0, "y": 0, "w": 400, "h": 50}
        boxes = [
            {"x": 0, "y": 0, "w": 100, "h": 50},
            {"x": 150, "y": 0, "w": 100, "h": 50},
            {"x": 300, "y": 0, "w": 100, "h": 50},
        ]
        assert detect_space_between(boxes, "HORIZONTAL", frame) is True

    def test_not_touching(self):
        frame = {"x": 0, "y": 0, "w": 500, "h": 50}
        boxes = [
            {"x": 0, "y": 0, "w": 100, "h": 50},
            {"x": 150, "y": 0, "w": 100, "h": 50},
            {"x": 300, "y": 0, "w": 100, "h": 50},
        ]
        assert detect_space_between(boxes, "HORIZONTAL", frame) is False

    def test_vertical(self):
        frame = {"x": 0, "y": 0, "w": 100, "h": 300}
        boxes = [
            {"x": 0, "y": 0, "w": 100, "h": 80},
            {"x": 0, "y": 110, "w": 100, "h": 80},
            {"x": 0, "y": 220, "w": 100, "h": 80},
        ]
        assert detect_space_between(boxes, "VERTICAL", frame) is True


class TestGapConsistency:
    def test_uniform(self):
        assert compute_gap_consistency([20, 20, 20]) < 0.01

    def test_varied(self):
        assert compute_gap_consistency([10, 50, 20]) > 0.3

    def test_single(self):
        assert compute_gap_consistency([20]) == 0.0

    def test_empty(self):
        assert compute_gap_consistency([]) == 1.0

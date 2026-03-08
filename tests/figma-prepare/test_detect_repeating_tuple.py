"""Tests for detect_repeating_tuple (Issue 186)."""
import pytest

from figma_utils import (
    TUPLE_MAX_SIZE,
    TUPLE_PATTERN_MIN,
    detect_repeating_tuple,
)


class TestDetectRepeatingTuple:
    def _make_node(self, node_type, name, node_id=None):
        """Helper to create a minimal Figma node dict."""
        return {
            "type": node_type,
            "name": name,
            "id": node_id or f"{node_type}-{name}",
        }

    def test_standard_3tuple_x3(self):
        """Standard blog card pattern: 3-tuple (RECTANGLE+FRAME+INSTANCE) x 3 reps."""
        children = []
        for i in range(3):
            children.append(self._make_node("RECTANGLE", f"img-{i}"))
            children.append(self._make_node("FRAME", f"text-{i}"))
            children.append(self._make_node("INSTANCE", f"arrow-{i}"))
        result = detect_repeating_tuple(children)
        assert len(result) == 1
        assert result[0]['tuple_size'] == 3
        assert result[0]['count'] == 3
        assert result[0]['start_idx'] == 0
        assert result[0]['children_indices'] == list(range(9))

    def test_2tuple_x4(self):
        """2-tuple (TEXT+RECTANGLE) x 4 repetitions."""
        children = []
        for i in range(4):
            children.append(self._make_node("TEXT", f"label-{i}"))
            children.append(self._make_node("RECTANGLE", f"box-{i}"))
        result = detect_repeating_tuple(children)
        assert len(result) == 1
        assert result[0]['tuple_size'] == 2
        assert result[0]['count'] == 4
        assert result[0]['children_indices'] == list(range(8))

    def test_not_enough_repetitions(self):
        """Only 2 repetitions (below TUPLE_PATTERN_MIN=3) -> no detection."""
        children = []
        for i in range(2):
            children.append(self._make_node("RECTANGLE", f"img-{i}"))
            children.append(self._make_node("FRAME", f"text-{i}"))
            children.append(self._make_node("INSTANCE", f"arrow-{i}"))
        result = detect_repeating_tuple(children)
        assert len(result) == 0

    def test_mixed_types_no_tuple(self):
        """Types that don't form any repeating tuple pattern."""
        children = [
            self._make_node("RECTANGLE", "a"),
            self._make_node("FRAME", "b"),
            self._make_node("TEXT", "c"),
            self._make_node("VECTOR", "d"),
            self._make_node("ELLIPSE", "e"),
            self._make_node("LINE", "f"),
        ]
        result = detect_repeating_tuple(children)
        assert len(result) == 0

    def test_tuple_at_start_with_trailing(self):
        """Tuple pattern at start with non-tuple trailing elements."""
        children = []
        for i in range(3):
            children.append(self._make_node("RECTANGLE", f"img-{i}"))
            children.append(self._make_node("FRAME", f"text-{i}"))
        # Add trailing non-pattern elements
        children.append(self._make_node("VECTOR", "decoration"))
        children.append(self._make_node("TEXT", "footer-text"))
        result = detect_repeating_tuple(children)
        assert len(result) == 1
        assert result[0]['tuple_size'] == 2
        assert result[0]['count'] == 3
        assert result[0]['start_idx'] == 0
        assert result[0]['children_indices'] == list(range(6))

    def test_tuple_in_middle(self):
        """Tuple pattern in the middle with surrounding non-tuple elements."""
        children = [
            self._make_node("TEXT", "heading"),
            self._make_node("VECTOR", "divider"),
        ]
        for i in range(3):
            children.append(self._make_node("RECTANGLE", f"img-{i}"))
            children.append(self._make_node("INSTANCE", f"btn-{i}"))
        children.append(self._make_node("TEXT", "footer"))
        result = detect_repeating_tuple(children)
        assert len(result) == 1
        assert result[0]['tuple_size'] == 2
        assert result[0]['count'] == 3
        assert result[0]['start_idx'] == 2
        assert result[0]['children_indices'] == [2, 3, 4, 5, 6, 7]

    def test_empty_input(self):
        """Empty children list -> no results."""
        result = detect_repeating_tuple([])
        assert result == []

    def test_single_element(self):
        """Single element -> no results."""
        children = [self._make_node("FRAME", "only-one")]
        result = detect_repeating_tuple(children)
        assert result == []

    def test_tuple_size_exceeds_max(self):
        """Tuple of size 6 (> TUPLE_MAX_SIZE=5) -> not detected as a single tuple."""
        children = []
        for i in range(3):
            children.append(self._make_node("RECTANGLE", f"a-{i}"))
            children.append(self._make_node("FRAME", f"b-{i}"))
            children.append(self._make_node("INSTANCE", f"c-{i}"))
            children.append(self._make_node("TEXT", f"d-{i}"))
            children.append(self._make_node("VECTOR", f"e-{i}"))
            children.append(self._make_node("ELLIPSE", f"f-{i}"))
        result = detect_repeating_tuple(children)
        # Should NOT find a tuple of size 6 (exceeds TUPLE_MAX_SIZE=5)
        for r in result:
            assert r['tuple_size'] <= TUPLE_MAX_SIZE

    def test_constants_values(self):
        """Verify constant values match spec."""
        assert TUPLE_PATTERN_MIN == 3
        assert TUPLE_MAX_SIZE == 5

    def test_5tuple_x3(self):
        """5-tuple (max size) x 3 repetitions."""
        children = []
        for i in range(3):
            children.append(self._make_node("RECTANGLE", f"a-{i}"))
            children.append(self._make_node("FRAME", f"b-{i}"))
            children.append(self._make_node("INSTANCE", f"c-{i}"))
            children.append(self._make_node("TEXT", f"d-{i}"))
            children.append(self._make_node("VECTOR", f"e-{i}"))
        result = detect_repeating_tuple(children)
        assert len(result) == 1
        assert result[0]['tuple_size'] == 5
        assert result[0]['count'] == 3
        assert result[0]['children_indices'] == list(range(15))

    def test_two_different_tuples(self):
        """Two non-overlapping tuple patterns of different sizes."""
        children = []
        # First pattern: 2-tuple x 3
        for i in range(3):
            children.append(self._make_node("TEXT", f"label-{i}"))
            children.append(self._make_node("RECTANGLE", f"box-{i}"))
        # Separator
        children.append(self._make_node("VECTOR", "divider"))
        # Second pattern: 3-tuple x 3
        for i in range(3):
            children.append(self._make_node("FRAME", f"card-{i}"))
            children.append(self._make_node("INSTANCE", f"icon-{i}"))
            children.append(self._make_node("ELLIPSE", f"dot-{i}"))
        result = detect_repeating_tuple(children)
        assert len(result) == 2
        # First group
        first = [r for r in result if r['start_idx'] == 0][0]
        assert first['tuple_size'] == 2
        assert first['count'] == 3
        # Second group
        second = [r for r in result if r['start_idx'] == 7][0]
        assert second['tuple_size'] == 3
        assert second['count'] == 3

    def test_all_same_type_not_tuple(self):
        """All elements of same type -> no tuple (tuple_size=1 is below min size of 2)."""
        children = [self._make_node("TEXT", f"t-{i}") for i in range(6)]
        result = detect_repeating_tuple(children)
        assert len(result) == 0

    def test_hidden_children_filtered(self):
        """Hidden children should be excluded from tuple detection (Issue #264)."""
        children = []
        for i in range(3):
            children.append(self._make_node("RECTANGLE", f"img-{i}"))
            children.append(self._make_node("FRAME", f"text-{i}"))
            children.append(self._make_node("INSTANCE", f"arrow-{i}"))
        # Insert hidden elements that would break the pattern if not filtered
        children.insert(3, {"type": "VECTOR", "name": "hidden-el", "id": "hidden-1", "visible": False})
        children.insert(7, {"type": "TEXT", "name": "hidden-el-2", "id": "hidden-2", "visible": False})
        result = detect_repeating_tuple(children)
        # Hidden elements should be filtered out; pattern should still be detected
        assert len(result) == 1
        assert result[0]['tuple_size'] == 3
        assert result[0]['count'] == 3

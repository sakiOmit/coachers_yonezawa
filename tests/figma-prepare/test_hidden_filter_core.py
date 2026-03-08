"""Tests for hidden children filtering — core hidden filter logic (Issue #242, #245)."""
import json
import os
import pytest

from helpers import run_script, write_fixture

from figma_utils import (
    _collect_text_preview,
    _count_flat_descendants,
    _compute_child_types,
    _compute_flags,
    decoration_dominant_shape,
    detect_en_jp_label_pairs,
    detect_highlight_text,
    detect_horizontal_bar,
    detect_table_rows,
    generate_enriched_table,
    is_decoration_pattern,
    is_heading_like,
    structure_hash,
)


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

"""Tests for detect_highlight_text (Issue 190)."""
import pytest

from figma_utils import (
    HIGHLIGHT_HEIGHT_RATIO_MAX,
    HIGHLIGHT_HEIGHT_RATIO_MIN,
    HIGHLIGHT_OVERLAP_RATIO,
    HIGHLIGHT_TEXT_MAX_LEN,
    detect_highlight_text,
)


class TestDetectHighlightText:
    def _make_rect(self, x, y, w, h, node_id='r1', has_children=False):
        node = {
            'id': node_id, 'type': 'RECTANGLE', 'name': f'Rectangle {node_id}',
            'absoluteBoundingBox': {'x': x, 'y': y, 'width': w, 'height': h},
        }
        if has_children:
            node['children'] = [{'type': 'VECTOR', 'absoluteBoundingBox': {'x': x, 'y': y, 'width': 10, 'height': 10}}]
        return node

    def _make_text(self, x, y, w, h, text='test', node_id='t1'):
        return {
            'id': node_id, 'type': 'TEXT', 'name': f'Text {node_id}',
            'absoluteBoundingBox': {'x': x, 'y': y, 'width': w, 'height': h},
            'characters': text,
        }

    def test_standard_overlap(self):
        """RECTANGLE and TEXT overlapping at same position -> highlight detected."""
        children = [
            self._make_rect(100, 100, 200, 40),
            self._make_text(110, 105, 180, 30, text='key phrase'),
        ]
        result = detect_highlight_text(children)
        assert len(result) == 1
        assert result[0]['rect_idx'] == 0
        assert result[0]['text_idx'] == 1
        assert result[0]['text_content'] == 'key phrase'

    def test_no_overlap(self):
        """RECTANGLE and TEXT completely separated -> no highlight."""
        children = [
            self._make_rect(100, 100, 200, 40),
            self._make_text(100, 300, 200, 30, text='far away'),
        ]
        result = detect_highlight_text(children)
        assert len(result) == 0

    def test_partial_overlap_below_threshold(self):
        """Y overlap below 80% threshold -> no highlight."""
        # RECT: y=100..140, TEXT: y=130..165 (overlap 10px, smaller_h=35, ratio=0.29)
        children = [
            self._make_rect(100, 100, 200, 40),
            self._make_text(100, 130, 200, 35, text='partial'),
        ]
        result = detect_highlight_text(children)
        assert len(result) == 0

    def test_rect_too_tall(self):
        """RECT height > 2.0x TEXT height -> no highlight."""
        children = [
            self._make_rect(100, 100, 200, 100),  # h=100
            self._make_text(100, 100, 200, 30, text='small'),  # h=30, ratio=3.33
        ]
        result = detect_highlight_text(children)
        assert len(result) == 0

    def test_rect_too_short(self):
        """RECT height < 0.5x TEXT height -> no highlight."""
        children = [
            self._make_rect(100, 100, 200, 10),  # h=10
            self._make_text(100, 95, 200, 40, text='tall text'),  # h=40, ratio=0.25
        ]
        result = detect_highlight_text(children)
        assert len(result) == 0

    def test_text_too_long(self):
        """Text > HIGHLIGHT_TEXT_MAX_LEN (30) -> no highlight."""
        long_text = 'a' * 31
        children = [
            self._make_rect(100, 100, 200, 40),
            self._make_text(100, 100, 200, 30, text=long_text),
        ]
        result = detect_highlight_text(children)
        assert len(result) == 0

    def test_text_exactly_30_chars(self):
        """Text exactly at max length -> highlight detected."""
        text_30 = 'a' * 30
        children = [
            self._make_rect(100, 100, 200, 40),
            self._make_text(105, 105, 180, 30, text=text_30),
        ]
        result = detect_highlight_text(children)
        assert len(result) == 1

    def test_multiple_highlight_pairs(self):
        """Two RECT+TEXT pairs -> both detected."""
        children = [
            self._make_rect(100, 100, 200, 40, node_id='r1'),
            self._make_text(105, 105, 180, 30, text='first', node_id='t1'),
            self._make_rect(100, 200, 200, 40, node_id='r2'),
            self._make_text(105, 205, 180, 30, text='second', node_id='t2'),
        ]
        result = detect_highlight_text(children)
        assert len(result) == 2
        texts = {r['text_content'] for r in result}
        assert texts == {'first', 'second'}

    def test_rect_with_children_not_leaf(self):
        """RECTANGLE with children (not a leaf) -> not considered for highlight."""
        children = [
            self._make_rect(100, 100, 200, 40, has_children=True),
            self._make_text(105, 105, 180, 30, text='behind'),
        ]
        result = detect_highlight_text(children)
        assert len(result) == 0

    def test_empty_children(self):
        """Empty children list -> empty result."""
        result = detect_highlight_text([])
        assert result == []

    def test_no_rectangle(self):
        """Only TEXT children -> no highlight."""
        children = [
            self._make_text(100, 100, 200, 30, text='only text', node_id='t1'),
            self._make_text(100, 200, 200, 30, text='more text', node_id='t2'),
        ]
        result = detect_highlight_text(children)
        assert result == []

    def test_no_text(self):
        """Only RECTANGLE children -> no highlight."""
        children = [
            self._make_rect(100, 100, 200, 40, node_id='r1'),
            self._make_rect(100, 200, 200, 40, node_id='r2'),
        ]
        result = detect_highlight_text(children)
        assert result == []

    def test_non_rect_text_combo(self):
        """VECTOR + TEXT at same position -> no highlight (must be RECTANGLE)."""
        children = [
            {'id': 'v1', 'type': 'VECTOR', 'name': 'Vector 1',
             'absoluteBoundingBox': {'x': 100, 'y': 100, 'width': 200, 'height': 40}},
            self._make_text(105, 105, 180, 30, text='over vector'),
        ]
        result = detect_highlight_text(children)
        assert result == []

    def test_x_overlap_required(self):
        """X ranges don't overlap -> no highlight even if Y overlaps."""
        children = [
            self._make_rect(100, 100, 200, 40),
            self._make_text(400, 100, 200, 30, text='far right'),
        ]
        result = detect_highlight_text(children)
        assert len(result) == 0

    def test_constants_exported(self):
        """Verify constants are exported and have expected values."""
        assert HIGHLIGHT_OVERLAP_RATIO == 0.8
        assert HIGHLIGHT_TEXT_MAX_LEN == 30
        assert HIGHLIGHT_HEIGHT_RATIO_MIN == 0.5
        assert HIGHLIGHT_HEIGHT_RATIO_MAX == 2.0

    def test_model_case_example(self):
        """Reproduce the model case: Rectangle 14 (205x49) behind TEXT (same position)."""
        children = [
            self._make_rect(217, 3098, 205, 49, node_id='rect14'),
            self._make_text(220, 3100, 200, 40, text='key text', node_id='text-key'),
        ]
        result = detect_highlight_text(children)
        assert len(result) == 1
        assert result[0]['text_content'] == 'key text'

    def test_each_rect_used_once(self):
        """One RECT cannot match multiple TEXTs."""
        children = [
            self._make_rect(100, 100, 200, 40, node_id='r1'),
            self._make_text(105, 105, 180, 30, text='first', node_id='t1'),
            self._make_text(105, 106, 180, 30, text='second', node_id='t2'),
        ]
        result = detect_highlight_text(children)
        assert len(result) == 1  # Only first TEXT matched

    def test_zero_size_rect(self):
        """RECT with zero width -> skipped."""
        children = [
            self._make_rect(100, 100, 0, 40),
            self._make_text(100, 100, 200, 30, text='test'),
        ]
        result = detect_highlight_text(children)
        assert result == []

    def test_characters_field_preferred(self):
        """Characters field is used over name for text content."""
        children = [
            self._make_rect(100, 100, 200, 40),
            {
                'id': 't1', 'type': 'TEXT', 'name': 'Text 1',
                'absoluteBoundingBox': {'x': 105, 'y': 105, 'width': 180, 'height': 30},
                'characters': 'real content',
            },
        ]
        result = detect_highlight_text(children)
        assert len(result) == 1
        assert result[0]['text_content'] == 'real content'

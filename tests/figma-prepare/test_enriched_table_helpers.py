"""Tests for enriched table helpers: TestComputeChildTypes, TestComputeFlags, TestCollectTextPreview, TestGenerateEnrichedTableOverflowY."""
import pytest

from figma_utils import (
    _collect_text_preview,
    _compute_child_types,
    _compute_flags,
    _compute_zone_bboxes,
    detect_bg_content_layers,
    detect_horizontal_bar,
    detect_repeating_tuple,
    generate_enriched_table,
    HORIZONTAL_BAR_MAX_HEIGHT,
    HORIZONTAL_BAR_MIN_ELEMENTS,
    HORIZONTAL_BAR_VARIANCE_RATIO,
    TUPLE_PATTERN_MIN,
    resolve_absolute_coords,
)


class TestComputeChildTypes:
    """Tests for _compute_child_types helper."""

    def test_empty(self):
        from figma_utils import _compute_child_types
        assert _compute_child_types([]) == '-'

    def test_single_type(self):
        from figma_utils import _compute_child_types
        children = [{'type': 'TEXT'}, {'type': 'TEXT'}, {'type': 'TEXT'}]
        assert _compute_child_types(children) == '3TEX'

    def test_mixed_types(self):
        from figma_utils import _compute_child_types
        children = [{'type': 'FRAME'}, {'type': 'TEXT'}, {'type': 'TEXT'}, {'type': 'RECTANGLE'}]
        result = _compute_child_types(children)
        assert '1FRA' in result
        assert '2TEX' in result
        assert '1REC' in result

    def test_unknown_type(self):
        from figma_utils import _compute_child_types
        children = [{'type': 'UNKNOWN_TYPE'}]
        assert _compute_child_types(children) == '1OTH'


class TestComputeFlags:
    """Tests for _compute_flags helper."""

    def test_no_flags(self):
        from figma_utils import _compute_flags
        node = {
            'type': 'FRAME', 'children': [{'type': 'TEXT'}],
            'absoluteBoundingBox': {'x': 100, 'y': 100, 'width': 300, 'height': 200},
        }
        flags = _compute_flags(node, 1440, 5000)
        assert flags == []

    def test_hidden_flag(self):
        from figma_utils import _compute_flags
        node = {
            'type': 'FRAME', 'visible': False, 'children': [],
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 200, 'height': 200},
        }
        flags = _compute_flags(node, 1440, 5000)
        assert 'hidden' in flags

    def test_bg_full_for_vector(self):
        """VECTOR type also gets bg-full flag when full-width leaf."""
        from figma_utils import _compute_flags
        node = {
            'type': 'VECTOR', 'children': [],
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 720},
        }
        flags = _compute_flags(node, 1440, 5000)
        assert 'bg-full' in flags

    def test_no_bg_for_frame(self):
        """FRAME type does NOT get bg-full flag even when full-width."""
        from figma_utils import _compute_flags
        node = {
            'type': 'FRAME', 'children': [],
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 720},
        }
        flags = _compute_flags(node, 1440, 5000)
        assert 'bg-full' not in flags

    def test_overflow_y_flag(self):
        """Element extending below page gets overflow-y flag."""
        from figma_utils import _compute_flags
        node = {
            'type': 'RECTANGLE', 'children': [],
            'absoluteBoundingBox': {'x': 0, 'y': 5000, 'width': 1440, 'height': 1000},
        }
        flags = _compute_flags(node, 1440, 5273)
        assert 'overflow-y' in flags


class TestCollectTextPreview:
    """Tests for _collect_text_preview helper."""

    def test_direct_text(self):
        from figma_utils import _collect_text_preview
        node = {'type': 'TEXT', 'characters': 'Hello World', 'name': 'Text 1'}
        assert _collect_text_preview(node) == 'Hello World'

    def test_nested_text(self):
        from figma_utils import _collect_text_preview
        node = {
            'type': 'FRAME', 'name': 'section',
            'children': [
                {'type': 'FRAME', 'name': 'inner', 'children': [
                    {'type': 'TEXT', 'characters': '深いテキスト', 'name': 'Text 1', 'children': []},
                ]},
            ],
        }
        assert _collect_text_preview(node) == '深いテキスト'

    def test_max_depth_respected(self):
        from figma_utils import _collect_text_preview
        # Text is at depth 4 but max_depth=3
        node = {
            'type': 'FRAME', 'name': 'a',
            'children': [{
                'type': 'FRAME', 'name': 'b',
                'children': [{
                    'type': 'FRAME', 'name': 'c',
                    'children': [{
                        'type': 'TEXT', 'characters': 'deep', 'name': 'd', 'children': [],
                    }],
                }],
            }],
        }
        assert _collect_text_preview(node, max_depth=2) == ''

    def test_unnamed_text_skipped(self):
        from figma_utils import _collect_text_preview
        node = {'type': 'TEXT', 'name': 'Text 1', 'children': []}  # no characters, unnamed
        assert _collect_text_preview(node) == ''

    def test_truncation(self):
        from figma_utils import _collect_text_preview
        node = {'type': 'TEXT', 'characters': 'A' * 100, 'name': 'long'}
        assert len(_collect_text_preview(node, max_len=30)) == 30


# ============================================================
# generate_enriched_table: page_height overflow-y (Issue 202)
# ============================================================
class TestGenerateEnrichedTableOverflowY:
    """Tests for generate_enriched_table overflow-y detection."""

    def _make_node(self, nid, ntype, name, x, y, w, h, children=None):
        return {
            'id': nid, 'type': ntype, 'name': name,
            'absoluteBoundingBox': {'x': x, 'y': y, 'width': w, 'height': h},
            'children': children or [],
        }

    def test_overflow_y_with_page_height(self):
        """Element extending below page_height -> overflow-y flag."""
        children = [
            self._make_node('1:1', 'RECTANGLE', 'bg', 0, 4800, 1440, 500),
        ]
        result = generate_enriched_table(children, page_width=1440, page_height=5000)
        assert 'overflow-y' in result

    def test_no_overflow_y_within_page(self):
        """Element within page_height -> no overflow-y flag."""
        children = [
            self._make_node('1:1', 'RECTANGLE', 'bg', 0, 4800, 1440, 100),
        ]
        result = generate_enriched_table(children, page_width=1440, page_height=5000)
        assert 'overflow-y' not in result

    def test_zero_page_height_no_overflow_y(self):
        """page_height=0 (default) -> never overflow-y."""
        children = [
            self._make_node('1:1', 'RECTANGLE', 'bg', 0, 99999, 1440, 500),
        ]
        result = generate_enriched_table(children, page_width=1440, page_height=0)
        assert 'overflow-y' not in result

    def test_overflow_y_with_root_y_offset_no_false_positive(self):
        """Artboard at non-zero Y: element within page should NOT get overflow-y.

        Bug (Issue #11): overflow-y used absolute Y coordinates without
        subtracting root_y, causing false positives when the artboard is
        positioned below Y=0 in the Figma canvas.
        """
        # Artboard starts at Y=3000, page_height=5000
        # Element at absolute Y=7800 -> relative Y=4800, bottom=4800+100=4900 < 5000*1.02
        children = [
            self._make_node('1:1', 'RECTANGLE', 'bg', 0, 7800, 1440, 100),
        ]
        result = generate_enriched_table(
            children, page_width=1440, page_height=5000, root_x=0, root_y=3000
        )
        assert 'overflow-y' not in result

    def test_overflow_y_with_root_y_offset_true_positive(self):
        """Artboard at non-zero Y: element truly overflowing SHOULD get overflow-y."""
        # Artboard starts at Y=3000, page_height=5000
        # Element at absolute Y=7800 -> relative Y=4800, bottom=4800+500=5300 > 5000*1.02=5100
        children = [
            self._make_node('1:1', 'RECTANGLE', 'bg', 0, 7800, 1440, 500),
        ]
        result = generate_enriched_table(
            children, page_width=1440, page_height=5000, root_x=0, root_y=3000
        )
        assert 'overflow-y' in result

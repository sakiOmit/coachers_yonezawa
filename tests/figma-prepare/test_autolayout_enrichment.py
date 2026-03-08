"""Tests for autolayout enrichment extraction.

Covers:
  - layout_from_enrichment
"""

from figma_utils.autolayout import layout_from_enrichment


# ===========================================================================
# layout_from_enrichment
# ===========================================================================

class TestLayoutFromEnrichment:
    """Tests for extracting Auto Layout from enriched metadata."""

    def test_horizontal_layout(self):
        frame = {
            'layoutMode': 'HORIZONTAL',
            'itemSpacing': 16,
            'paddingTop': 20,
            'paddingRight': 24,
            'paddingBottom': 20,
            'paddingLeft': 24,
            'primaryAxisAlignItems': 'MIN',
            'counterAxisAlignItems': 'CENTER',
        }
        result = layout_from_enrichment(frame)
        assert result is not None
        assert result['direction'] == 'HORIZONTAL'
        assert result['gap'] == 16
        assert result['padding'] == {'top': 20, 'right': 24, 'bottom': 20, 'left': 24}
        assert result['primary_axis_align'] == 'MIN'
        assert result['counter_axis_align'] == 'CENTER'
        assert result['confidence'] == 'exact'

    def test_vertical_layout(self):
        frame = {'layoutMode': 'VERTICAL', 'itemSpacing': 8}
        result = layout_from_enrichment(frame)
        assert result is not None
        assert result['direction'] == 'VERTICAL'
        assert result['gap'] == 8

    def test_wrap_layout(self):
        """layoutWrap == 'WRAP' converts direction to WRAP."""
        frame = {'layoutMode': 'HORIZONTAL', 'layoutWrap': 'WRAP', 'itemSpacing': 12}
        result = layout_from_enrichment(frame)
        assert result is not None
        assert result['direction'] == 'WRAP'

    def test_no_layout_mode_returns_none(self):
        frame = {'name': 'no-layout', 'type': 'FRAME'}
        assert layout_from_enrichment(frame) is None

    def test_empty_layout_mode_returns_none(self):
        frame = {'layoutMode': ''}
        assert layout_from_enrichment(frame) is None

    def test_defaults_when_fields_missing(self):
        frame = {'layoutMode': 'HORIZONTAL'}
        result = layout_from_enrichment(frame)
        assert result['gap'] == 0
        assert result['padding'] == {'top': 0, 'right': 0, 'bottom': 0, 'left': 0}
        assert result['primary_axis_align'] == 'MIN'
        assert result['counter_axis_align'] == 'MIN'

    def test_values_not_snapped(self):
        """Enriched values should NOT be snapped to grid (preserves Figma intent)."""
        frame = {'layoutMode': 'HORIZONTAL', 'itemSpacing': 13, 'paddingTop': 7}
        result = layout_from_enrichment(frame)
        assert result['gap'] == 13  # not snapped to 12
        assert result['padding']['top'] == 7  # not snapped to 8

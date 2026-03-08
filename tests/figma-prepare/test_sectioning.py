"""Tests for sectioning module — detect_heuristic_hints, classify_section_type, _compute_gap_analysis.

Covers:
  - detect_heuristic_hints: header/footer/bg detection, gap analysis, patterns
  - classify_section_type: keyword and hint-based classification
  - _compute_gap_analysis: gap statistics computation
  - _detect_header_footer_bg: position-based candidate detection
  - _detect_consecutive_patterns: structure hash pattern runs
  - _detect_heading_and_loose: heading/loose element detection
  - _detect_header_cluster: nav-like header cluster detection
  - count_children / get_child_types_summary / has_text_children
"""
import pytest

from figma_utils.sectioning import (
    classify_section_type,
    count_children,
    detect_heuristic_hints,
    get_child_types_summary,
    has_text_children,
    _compute_gap_analysis,
    _detect_consecutive_patterns,
    _detect_header_cluster,
    _detect_header_footer_bg,
    _detect_heading_and_loose,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _frame(id, x=0, y=0, w=100, h=100, name='Frame 1', children=None, **kw):
    node = {
        'id': id, 'name': name, 'type': 'FRAME',
        'absoluteBoundingBox': {'x': x, 'y': y, 'width': w, 'height': h},
    }
    if children is not None:
        node['children'] = children
    node.update(kw)
    return node


def _rect(id, x=0, y=0, w=100, h=100, name='Rectangle 1', **kw):
    node = {
        'id': id, 'name': name, 'type': 'RECTANGLE',
        'absoluteBoundingBox': {'x': x, 'y': y, 'width': w, 'height': h},
    }
    node.update(kw)
    return node


def _text(id, x=0, y=0, w=100, h=20, name='Text 1', characters='Hello', **kw):
    node = {
        'id': id, 'name': name, 'type': 'TEXT',
        'absoluteBoundingBox': {'x': x, 'y': y, 'width': w, 'height': h},
        'characters': characters,
    }
    node.update(kw)
    return node


def _line(id, x=0, y=0, w=200, h=2, name='Line 1', **kw):
    node = {
        'id': id, 'name': name, 'type': 'LINE',
        'absoluteBoundingBox': {'x': x, 'y': y, 'width': w, 'height': h},
    }
    node.update(kw)
    return node


# ---------------------------------------------------------------------------
# classify_section_type
# ---------------------------------------------------------------------------

class TestClassifySectionType:
    """Section classification from hints and name keywords."""

    def test_header_from_name(self):
        assert classify_section_type({}, 'header') == 'header'

    def test_footer_from_name(self):
        assert classify_section_type({}, 'section-footer') == 'footer'

    def test_hero_from_name(self):
        assert classify_section_type({}, 'hero-banner') == 'hero'

    def test_header_from_hints(self):
        assert classify_section_type({'is_header': True}) == 'header'

    def test_footer_from_hints(self):
        assert classify_section_type({'footer_candidates': ['id1']}) == 'footer'

    def test_hero_from_hints(self):
        assert classify_section_type({'has_hero_bg': True}) == 'hero'

    def test_content_from_background(self):
        assert classify_section_type({'background_candidates': ['id1']}) == 'content'

    def test_content_from_heading(self):
        assert classify_section_type({'heading_candidates': [{'id': 'h1'}]}) == 'content'

    def test_unknown_no_hints(self):
        assert classify_section_type({}) == 'unknown'

    def test_none_hints(self):
        assert classify_section_type(None) == 'unknown'

    def test_empty_name(self):
        assert classify_section_type({}, '') == 'unknown'

    def test_header_precedence_over_footer(self):
        """header_candidates takes priority when both present."""
        hints = {'header_candidates': ['id1'], 'footer_candidates': ['id2']}
        assert classify_section_type(hints) == 'header'

    def test_name_case_insensitive(self):
        assert classify_section_type({}, 'HEADER-main') == 'header'


# ---------------------------------------------------------------------------
# _compute_gap_analysis
# ---------------------------------------------------------------------------

class TestComputeGapAnalysis:
    """Gap statistics computation for sibling nodes."""

    def test_normal_uniform_gaps(self):
        """Uniform gaps -> high consistency."""
        children = [
            _frame('1', y=0, h=50),
            _frame('2', y=100, h=50),
            _frame('3', y=200, h=50),
            _frame('4', y=300, h=50),
        ]
        result = _compute_gap_analysis(children)
        assert result is not None
        assert result['median'] == 50
        assert result['mean'] == 50
        assert result['consistency'] == 'high'

    def test_varied_gaps(self):
        """Highly varied gaps -> low consistency."""
        children = [
            _frame('1', y=0, h=10),
            _frame('2', y=20, h=10),    # gap 10
            _frame('3', y=200, h=10),   # gap 170
            _frame('4', y=220, h=10),   # gap 10
        ]
        result = _compute_gap_analysis(children)
        assert result is not None
        assert result['consistency'] == 'low'

    def test_less_than_3_children_returns_none(self):
        children = [_frame('1'), _frame('2')]
        assert _compute_gap_analysis(children) is None

    def test_empty_children(self):
        assert _compute_gap_analysis([]) is None

    def test_single_child(self):
        assert _compute_gap_analysis([_frame('1')]) is None

    def test_hidden_children_filtered(self):
        """Hidden children are excluded; if < 3 visible, returns None."""
        children = [
            _frame('1', y=0, h=50),
            _frame('2', y=100, h=50, visible=False),
            _frame('3', y=200, h=50, visible=False),
            _frame('4', y=300, h=50),
        ]
        result = _compute_gap_analysis(children)
        assert result is None  # only 2 visible

    def test_hidden_mixed_still_enough(self):
        """3 visible children with 1 hidden -> computes gaps."""
        children = [
            _frame('1', y=0, h=50),
            _frame('2', y=100, h=50, visible=False),
            _frame('3', y=200, h=50),
            _frame('4', y=350, h=50),
        ]
        result = _compute_gap_analysis(children)
        assert result is not None

    def test_overlapping_children_no_positive_gaps(self):
        """All children overlap -> fewer than 2 positive gaps -> None."""
        children = [
            _frame('1', y=0, h=200),
            _frame('2', y=50, h=200),
            _frame('3', y=100, h=200),
        ]
        result = _compute_gap_analysis(children)
        assert result is None

    def test_zero_mean_gap(self):
        """Edge-to-edge touching -> gap=0 -> excluded from positive gaps."""
        children = [
            _frame('1', y=0, h=100),
            _frame('2', y=100, h=100),  # gap 0
            _frame('3', y=200, h=100),  # gap 0
            _frame('4', y=310, h=100),  # gap 10
        ]
        result = _compute_gap_analysis(children)
        # Only 1 positive gap (10) -> fewer than 2 -> None
        assert result is None


# ---------------------------------------------------------------------------
# _detect_header_footer_bg
# ---------------------------------------------------------------------------

class TestDetectHeaderFooterBg:
    """Position-based header/footer/background candidate detection."""

    def test_header_detected_at_top(self):
        """Wide FRAME at top -> header candidate."""
        children = [
            _frame('hdr', x=0, y=0, w=1440, h=80, name='Header'),
            _frame('body', x=0, y=100, w=1440, h=5000),
        ]
        hdr, ftr, bg = _detect_header_footer_bg(children, page_y=0, page_h=6000, page_w=1440)
        assert 'hdr' in hdr

    def test_footer_detected_at_bottom(self):
        """Wide FRAME at bottom -> footer candidate."""
        children = [
            _frame('body', x=0, y=0, w=1440, h=5000),
            _frame('ftr', x=0, y=5000, w=1440, h=200),
        ]
        hdr, ftr, bg = _detect_header_footer_bg(children, page_y=0, page_h=5200, page_w=1440)
        assert 'ftr' in ftr

    def test_bg_rectangle_detected(self):
        """Tall RECTANGLE -> background candidate."""
        children = [
            _rect('bg', x=0, y=0, w=1440, h=500),
        ]
        hdr, ftr, bg = _detect_header_footer_bg(children, page_y=0, page_h=5000, page_w=1440)
        assert 'bg' in bg

    def test_small_rect_not_bg(self):
        """Small RECTANGLE (< HINT_BG_MIN_HEIGHT) -> not bg."""
        children = [
            _rect('small', x=0, y=0, w=1440, h=20),
        ]
        hdr, ftr, bg = _detect_header_footer_bg(children, page_y=0, page_h=5000, page_w=1440)
        assert 'small' not in bg

    def test_narrow_frame_not_header(self):
        """Narrow FRAME at top -> not header (width check fails)."""
        children = [
            _frame('narrow', x=0, y=0, w=200, h=80),
        ]
        hdr, ftr, bg = _detect_header_footer_bg(children, page_y=0, page_h=5000, page_w=1440)
        assert 'narrow' not in hdr

    def test_empty_children(self):
        hdr, ftr, bg = _detect_header_footer_bg([], page_y=0, page_h=5000, page_w=1440)
        assert hdr == []
        assert ftr == []
        assert bg == []

    def test_instance_type_as_header(self):
        """INSTANCE type at top should also be detected as header."""
        children = [
            {'id': 'inst', 'name': 'Header Instance', 'type': 'INSTANCE',
             'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 80}},
        ]
        hdr, ftr, bg = _detect_header_footer_bg(children, page_y=0, page_h=5000, page_w=1440)
        assert 'inst' in hdr


# ---------------------------------------------------------------------------
# _detect_consecutive_patterns
# ---------------------------------------------------------------------------

class TestDetectConsecutivePatterns:
    """Consecutive pattern run detection via structure hashes."""

    def test_three_similar_frames(self):
        """3 frames with same structure -> pattern detected."""
        children = [
            _frame('1', children=[_text('t1')]),
            _frame('2', children=[_text('t2')]),
            _frame('3', children=[_text('t3')]),
        ]
        patterns = _detect_consecutive_patterns(children)
        assert len(patterns) >= 1
        assert len(patterns[0]['ids']) == 3

    def test_no_pattern_with_different_structures(self):
        """Children with different structures -> no pattern."""
        children = [
            _frame('1', children=[_text('t1')]),
            _rect('2'),
            _text('3'),
        ]
        patterns = _detect_consecutive_patterns(children)
        assert len(patterns) == 0

    def test_empty_children(self):
        assert _detect_consecutive_patterns([]) == []

    def test_single_child(self):
        assert _detect_consecutive_patterns([_frame('1')]) == []

    def test_two_similar_not_enough(self):
        """2 similar frames < CONSECUTIVE_PATTERN_MIN (3) -> no pattern."""
        children = [
            _frame('1', children=[_text('t1')]),
            _frame('2', children=[_text('t2')]),
        ]
        patterns = _detect_consecutive_patterns(children)
        assert len(patterns) == 0


# ---------------------------------------------------------------------------
# _detect_heading_and_loose
# ---------------------------------------------------------------------------

class TestDetectHeadingAndLoose:
    """Heading candidate and loose element detection."""

    def test_line_is_loose(self):
        """LINE type -> loose element."""
        children = [_line('l1', y=100, h=2)]
        headings, loose = _detect_heading_and_loose(children)
        assert len(loose) == 1
        assert loose[0]['type'] == 'LINE'

    def test_small_leaf_is_loose(self):
        """Small leaf node (h<=20, no children) -> loose."""
        children = [_rect('r1', y=100, h=10)]
        headings, loose = _detect_heading_and_loose(children)
        assert len(loose) == 1

    def test_tall_frame_not_loose(self):
        """Tall frame is not loose."""
        children = [_frame('f1', y=100, h=300)]
        headings, loose = _detect_heading_and_loose(children)
        assert len(loose) == 0

    def test_empty_children(self):
        headings, loose = _detect_heading_and_loose([])
        assert headings == []
        assert loose == []

    def test_heading_like_detected(self):
        """Frame with TEXT children that looks heading-like."""
        heading_frame = _frame('h1', y=0, h=60, children=[
            _text('t1', characters='About Us'),
        ])
        children = [heading_frame, _frame('body', y=200, h=500)]
        headings, loose = _detect_heading_and_loose(children)
        assert len(headings) >= 1

    def test_too_tall_not_heading(self):
        """Frame taller than heading_max_h -> not heading candidate."""
        tall = _frame('tall', y=0, h=500, children=[_text('t1')])
        headings, loose = _detect_heading_and_loose([tall])
        assert len(headings) == 0


# ---------------------------------------------------------------------------
# _detect_header_cluster
# ---------------------------------------------------------------------------

class TestDetectHeaderCluster:
    """Header cluster detection for flat structures."""

    def test_nav_texts_in_header_zone(self):
        """Multiple short texts in header zone + enough elements -> cluster."""
        children = [
            _text('t1', x=0, y=10, w=80, h=20, characters='Home'),
            _text('t2', x=100, y=10, w=80, h=20, characters='About'),
            _text('t3', x=200, y=10, w=80, h=20, characters='Contact'),
            _frame('logo', x=0, y=5, w=100, h=30),  # 4th element
        ]
        result = _detect_header_cluster(children, page_y=0)
        assert len(result) >= 3

    def test_no_cluster_few_texts(self):
        """Too few text elements -> no cluster."""
        children = [
            _text('t1', x=0, y=10, w=80, h=20, characters='Home'),
            _frame('logo', x=0, y=5, w=100, h=30),
        ]
        result = _detect_header_cluster(children, page_y=0)
        assert result == []

    def test_empty_children(self):
        assert _detect_header_cluster([], page_y=0) == []

    def test_elements_outside_header_zone(self):
        """Elements below header zone -> no cluster."""
        children = [
            _text('t1', x=0, y=500, w=80, h=20, characters='Home'),
            _text('t2', x=100, y=500, w=80, h=20, characters='About'),
            _text('t3', x=200, y=500, w=80, h=20, characters='Contact'),
            _frame('f1', x=0, y=500, w=100, h=30),
        ]
        result = _detect_header_cluster(children, page_y=0)
        assert result == []


# ---------------------------------------------------------------------------
# detect_heuristic_hints (integration)
# ---------------------------------------------------------------------------

class TestDetectHeuristicHints:
    """Integration tests for the main heuristic hints function."""

    def _page_bbox(self, y=0, h=8500, w=1440):
        return {'x': 0, 'y': y, 'w': w, 'h': h}

    def test_empty_children(self):
        result = detect_heuristic_hints([], self._page_bbox())
        assert result['header_candidates'] == []
        assert result['footer_candidates'] == []
        assert result['gap_analysis'] == []

    def test_zero_height_page(self):
        result = detect_heuristic_hints([_frame('1')], self._page_bbox(h=0))
        assert result['header_candidates'] == []

    def test_hidden_children_filtered(self):
        """Hidden children are excluded from analysis."""
        children = [
            _frame('vis', x=0, y=0, w=1440, h=80),
            _frame('hid', x=0, y=100, w=1440, h=80, visible=False),
        ]
        result = detect_heuristic_hints(children, self._page_bbox())
        # Only 1 visible child, so 0 gap entries
        assert len(result['gap_analysis']) == 0

    def test_gap_analysis_between_children(self):
        """Two visible children produce one gap entry."""
        children = [
            _frame('1', x=0, y=0, w=1440, h=100),
            _frame('2', x=0, y=200, w=1440, h=100),
        ]
        result = detect_heuristic_hints(children, self._page_bbox())
        assert len(result['gap_analysis']) == 1
        assert result['gap_analysis'][0]['gap_px'] == 100

    def test_header_and_footer_detected(self):
        """Page with header at top and footer at bottom."""
        children = [
            _frame('hdr', x=0, y=0, w=1440, h=80),
            _frame('body', x=0, y=100, w=1440, h=7000),
            _frame('ftr', x=0, y=7800, w=1440, h=200),
        ]
        # Footer threshold: page_y + page_h * 0.9 = 0 + 8500*0.9 = 7650
        # ftr y+h = 7800+200 = 8000 > 7650 -> detected
        result = detect_heuristic_hints(children, self._page_bbox(h=8500))
        assert 'hdr' in result['header_candidates']
        assert 'ftr' in result['footer_candidates']

    def test_background_rect_detected(self):
        """Large RECTANGLE detected as background."""
        children = [
            _rect('bg', x=0, y=0, w=1440, h=500),
            _frame('content', x=0, y=0, w=1440, h=5000),
        ]
        result = detect_heuristic_hints(children, self._page_bbox())
        assert 'bg' in result['background_candidates']

    def test_negative_page_y(self):
        """Page with negative Y offset still works."""
        children = [
            _frame('hdr', x=0, y=-100, w=1440, h=80),
        ]
        result = detect_heuristic_hints(children, self._page_bbox(y=-100, h=5000))
        assert 'hdr' in result['header_candidates']

    def test_all_keys_present(self):
        """Result dict contains all expected keys."""
        result = detect_heuristic_hints([], self._page_bbox())
        expected_keys = {
            'header_candidates', 'header_cluster_ids', 'footer_candidates',
            'gap_analysis', 'background_candidates', 'consecutive_patterns',
            'heading_candidates', 'loose_elements',
        }
        assert set(result.keys()) == expected_keys


# ---------------------------------------------------------------------------
# count_children / get_child_types_summary / has_text_children
# ---------------------------------------------------------------------------

class TestHelperFunctions:
    """Small helper functions in sectioning module."""

    def test_count_children_filters_hidden(self):
        node = _frame('p', children=[
            _frame('1'),
            _frame('2', visible=False),
            _frame('3'),
        ])
        assert count_children(node) == 2

    def test_count_children_no_children(self):
        assert count_children(_frame('p')) == 0

    def test_get_child_types_summary(self):
        node = _frame('p', children=[
            _text('t1'), _text('t2'), _rect('r1'),
        ])
        summary = get_child_types_summary(node)
        assert 'TEXT:2' in summary
        assert 'RECTANGLE:1' in summary

    def test_get_child_types_summary_empty(self):
        assert get_child_types_summary(_frame('p')) == ''

    def test_has_text_children_true(self):
        node = _frame('p', children=[_text('t1')])
        assert has_text_children(node) is True

    def test_has_text_children_false(self):
        node = _frame('p', children=[_rect('r1')])
        assert has_text_children(node) is False

    def test_has_text_children_hidden_excluded(self):
        node = _frame('p', children=[
            _text('t1', visible=False),
        ])
        assert has_text_children(node) is False

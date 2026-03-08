"""Tests for Stage B -> Stage C context flow."""
import pytest

from figma_utils.sectioning import classify_section_type, _compute_gap_analysis
from figma_utils.nested_context import _format_stage_b_context


# ---------------------------------------------------------------------------
# classify_section_type
# ---------------------------------------------------------------------------

class TestClassifySectionType:
    def test_header_from_hints(self):
        assert classify_section_type({'is_header': True}) == 'header'

    def test_header_from_candidates(self):
        assert classify_section_type({'header_candidates': ['node-1']}) == 'header'

    def test_header_from_name(self):
        assert classify_section_type({}, 'section-header') == 'header'

    def test_footer_from_hints(self):
        assert classify_section_type({'is_footer': True}) == 'footer'

    def test_footer_from_candidates(self):
        assert classify_section_type({'footer_candidates': ['node-2']}) == 'footer'

    def test_footer_from_name(self):
        assert classify_section_type({}, 'section-footer') == 'footer'

    def test_hero_from_bg(self):
        assert classify_section_type({'has_hero_bg': True}) == 'hero'

    def test_hero_from_name(self):
        assert classify_section_type({}, 'hero-section') == 'hero'

    def test_content_with_heading(self):
        assert classify_section_type({'has_heading': True}) == 'content'

    def test_content_with_heading_candidates(self):
        assert classify_section_type({'heading_candidates': [{'id': 'n1'}]}) == 'content'

    def test_content_with_bg_candidate(self):
        assert classify_section_type({'has_bg_candidate': True}) == 'content'

    def test_content_with_background_candidates(self):
        assert classify_section_type({'background_candidates': ['node-3']}) == 'content'

    def test_unknown(self):
        assert classify_section_type({}) == 'unknown'

    def test_none_hints(self):
        assert classify_section_type(None) == 'unknown'

    def test_empty_name(self):
        assert classify_section_type({}, '') == 'unknown'

    def test_priority_header_over_footer(self):
        """Header takes priority when both hints present."""
        assert classify_section_type({'is_header': True, 'is_footer': True}) == 'header'


# ---------------------------------------------------------------------------
# _compute_gap_analysis
# ---------------------------------------------------------------------------

def _make_node(y, h=50):
    """Create a minimal node with given y position and height."""
    return {
        'type': 'FRAME',
        'visible': True,
        'absoluteBoundingBox': {'x': 0, 'y': y, 'width': 100, 'height': h},
        'children': [],
    }


class TestComputeGapAnalysis:
    def test_regular_spacing(self):
        children = [_make_node(0), _make_node(80), _make_node(160), _make_node(240)]
        # gaps: 30, 30, 30
        result = _compute_gap_analysis(children)
        assert result is not None
        assert result['consistency'] == 'high'
        assert result['median'] == 30

    def test_medium_consistency(self):
        # gaps: 20, 30, 40 -> cv ~ 0.27
        children = [_make_node(0), _make_node(70), _make_node(150), _make_node(240)]
        result = _compute_gap_analysis(children)
        assert result is not None
        assert result['consistency'] == 'medium'

    def test_irregular_spacing(self):
        children = [_make_node(0), _make_node(60), _make_node(200), _make_node(280)]
        # gaps: 10, 90, 30
        result = _compute_gap_analysis(children)
        assert result is not None
        assert result['consistency'] in ('medium', 'low')

    def test_too_few_children(self):
        assert _compute_gap_analysis([_make_node(0), _make_node(100)]) is None

    def test_single_child(self):
        assert _compute_gap_analysis([_make_node(0)]) is None

    def test_empty_list(self):
        assert _compute_gap_analysis([]) is None

    def test_hidden_children_filtered(self):
        """Hidden children should be excluded from gap computation."""
        children = [
            _make_node(0),
            {'type': 'FRAME', 'visible': False,
             'absoluteBoundingBox': {'x': 0, 'y': 40, 'width': 100, 'height': 50},
             'children': []},
            _make_node(80),
            _make_node(160),
        ]
        result = _compute_gap_analysis(children)
        # With hidden filtered: 3 visible nodes, gaps: 30, 30
        assert result is not None
        assert result['consistency'] == 'high'

    def test_overlapping_elements(self):
        """When elements overlap (negative gaps), only positive gaps count."""
        children = [_make_node(0), _make_node(30), _make_node(60), _make_node(200)]
        # gaps: -20 (overlap), -20 (overlap), 90
        # Only 1 positive gap -> not enough -> None
        result = _compute_gap_analysis(children)
        assert result is None

    def test_zero_gap_not_counted(self):
        """Zero gaps should not be included in analysis."""
        children = [_make_node(0, 50), _make_node(50, 50), _make_node(100, 50), _make_node(180, 50)]
        # gaps: 0, 0, 30 -> only 1 positive gap -> None
        result = _compute_gap_analysis(children)
        assert result is None


# ---------------------------------------------------------------------------
# _format_stage_b_context
# ---------------------------------------------------------------------------

class TestFormatStageBContext:
    def test_none_hints(self):
        assert _format_stage_b_context(None) == ''

    def test_empty_hints(self):
        assert _format_stage_b_context({}) == ''

    def test_with_section_type(self):
        result = _format_stage_b_context({'section_type': 'content'})
        assert '## Section Context (from Stage B)' in result
        assert '**content**' in result

    def test_default_section_type(self):
        """When section_type is missing, defaults to 'unknown'."""
        result = _format_stage_b_context({'has_hero_bg': True})
        assert '**unknown**' in result
        assert 'Hero background' in result

    def test_with_consecutive_patterns(self):
        hints = {
            'section_type': 'content',
            'consecutive_patterns': [
                {'count': 4, 'ids': ['a', 'b', 'c', 'd']},
                {'count': 3, 'ids': ['e', 'f', 'g']},
            ],
        }
        result = _format_stage_b_context(hints)
        assert 'Consecutive patterns detected: 2 group(s)' in result
        assert '4 similar elements' in result

    def test_consecutive_patterns_fallback_count(self):
        """When 'count' key is missing, fallback to len(ids)."""
        hints = {
            'section_type': 'content',
            'consecutive_patterns': [
                {'ids': ['a', 'b', 'c']},
            ],
        }
        result = _format_stage_b_context(hints)
        assert '3 similar elements' in result

    def test_consecutive_patterns_limit_three(self):
        """Should only show first 3 pattern groups."""
        hints = {
            'section_type': 'content',
            'consecutive_patterns': [
                {'count': 2}, {'count': 3}, {'count': 4}, {'count': 5},
            ],
        }
        result = _format_stage_b_context(hints)
        assert '4 group(s)' in result
        # Lines with "similar elements" should be at most 3
        similar_lines = [l for l in result.split('\n') if 'similar elements' in l]
        assert len(similar_lines) == 3

    def test_with_header_candidates(self):
        hints = {'section_type': 'header', 'header_candidates': ['node-1']}
        result = _format_stage_b_context(hints)
        assert 'Header elements detected' in result

    def test_with_footer_candidates(self):
        hints = {'section_type': 'footer', 'footer_candidates': ['node-2']}
        result = _format_stage_b_context(hints)
        assert 'Footer elements detected' in result

    def test_with_gap_analysis_dict(self):
        hints = {
            'section_type': 'content',
            'gap_analysis': {'median': 32, 'consistency': 'high'},
        }
        result = _format_stage_b_context(hints)
        assert '32px' in result
        assert 'high' in result

    def test_gap_analysis_non_dict_ignored(self):
        """Gap analysis as a list (Stage B raw format) should be ignored."""
        hints = {
            'section_type': 'content',
            'gap_analysis': [{'between': ['a', 'b'], 'gap_px': 30}],
        }
        result = _format_stage_b_context(hints)
        assert 'Median gap' not in result

    def test_hero_section(self):
        hints = {'section_type': 'hero', 'has_hero_bg': True}
        result = _format_stage_b_context(hints)
        assert 'Hero background detected' in result
        assert '**hero**' in result

    def test_with_heading_candidates(self):
        hints = {
            'section_type': 'content',
            'heading_candidates': [{'id': 'h1'}, {'id': 'h2'}],
        }
        result = _format_stage_b_context(hints)
        assert 'Heading candidates: 2' in result

    def test_with_loose_elements(self):
        hints = {
            'section_type': 'content',
            'loose_elements': [{'id': 'l1'}],
        }
        result = _format_stage_b_context(hints)
        assert 'Loose elements' in result
        assert '1' in result

    def test_full_context(self):
        """Test a fully populated hints dict produces all sections."""
        hints = {
            'section_type': 'content',
            'consecutive_patterns': [{'count': 5}],
            'header_candidates': ['h'],
            'footer_candidates': ['f'],
            'has_hero_bg': True,
            'heading_candidates': [{'id': 'x'}],
            'loose_elements': [{'id': 'y'}],
            'gap_analysis': {'median': 24, 'consistency': 'medium'},
        }
        result = _format_stage_b_context(hints)
        assert '## Section Context' in result
        assert 'Consecutive patterns' in result
        assert 'Header elements' in result
        assert 'Footer elements' in result
        assert 'Hero background' in result
        assert 'Heading candidates' in result
        assert 'Loose elements' in result
        assert '24px' in result

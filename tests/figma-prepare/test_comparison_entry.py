"""Tests for comparison.py entry point — compare_grouping_results and stage merge functions.

Focuses on the orchestration logic in comparison.py itself (not the submodules
which have their own tests in test_compare_grouping.py and test_graduated_merge.py).

Covers:
  - compare_grouping_results: Jaccard matching, coverage, edge cases
  - compare_grouping_by_section: per-section graduated merging
  - _merge_stage_c_with_a_remainder / _merge_stage_a_with_c_confident: merge edge cases
"""
import pytest

from figma_utils.comparison import (
    compare_grouping_results,
    compare_grouping_by_section,
    _merge_stage_c_with_a_remainder,
    _merge_stage_a_with_c_confident,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _a(node_ids, method='pattern', parent_id='sec1', **kw):
    d = {'method': method, 'node_ids': node_ids, 'parent_id': parent_id}
    d.update(kw)
    return d


def _c(node_ids, name='group', pattern='list', section_id=None, **kw):
    d = {'name': name, 'pattern': pattern, 'node_ids': node_ids}
    if section_id:
        d['section_id'] = section_id
    d.update(kw)
    return d


# ---------------------------------------------------------------------------
# compare_grouping_results
# ---------------------------------------------------------------------------

class TestCompareGroupingResults:
    """Core comparison entry point tests."""

    def test_both_empty(self):
        result = compare_grouping_results([], [])
        assert result['coverage'] == 1.0
        assert result['mean_jaccard'] == 1.0
        assert result['matched_pairs'] == []

    def test_a_empty_c_has_groups(self):
        result = compare_grouping_results([], [_c(['1', '2'])])
        assert result['coverage'] == 1.0
        assert len(result['stage_c_only']) == 1

    def test_c_empty_a_has_groups(self):
        result = compare_grouping_results([_a(['1', '2'])], [])
        assert result['coverage'] == 0.0
        assert len(result['stage_a_only']) == 1

    def test_perfect_match_single_group(self):
        result = compare_grouping_results(
            [_a(['1', '2', '3'])],
            [_c(['1', '2', '3'])],
        )
        assert result['coverage'] == 1.0
        assert result['mean_jaccard'] == 1.0
        assert len(result['matched_pairs']) == 1

    def test_no_overlap(self):
        result = compare_grouping_results(
            [_a(['1', '2'])],
            [_c(['3', '4'])],
        )
        assert result['coverage'] == 0.0
        assert result['mean_jaccard'] == 0.0

    def test_partial_overlap(self):
        """Stage C covers half of Stage A nodes."""
        result = compare_grouping_results(
            [_a(['1', '2', '3', '4'])],
            [_c(['1', '2'])],
        )
        assert result['coverage'] == 0.5

    def test_multiple_groups(self):
        result = compare_grouping_results(
            [_a(['1', '2']), _a(['3', '4'])],
            [_c(['1', '2']), _c(['3', '4'])],
        )
        assert result['coverage'] == 1.0
        assert len(result['matched_pairs']) == 2

    def test_parent_id_filter(self):
        """Only candidates matching parent_id are compared."""
        a = [_a(['1', '2'], parent_id='sec1'), _a(['3', '4'], parent_id='sec2')]
        c = [_c(['1', '2'], section_id='sec1')]
        result = compare_grouping_results(a, c, parent_id='sec1')
        assert result['coverage'] == 1.0
        assert len(result['stage_a_only']) == 0

    def test_parent_id_filter_no_match(self):
        """No candidates match parent_id -> empty comparison."""
        a = [_a(['1', '2'], parent_id='sec1')]
        c = [_c(['1', '2'], section_id='sec1')]
        result = compare_grouping_results(a, c, parent_id='nonexistent')
        assert result['coverage'] == 1.0  # both empty -> perfect

    def test_empty_node_ids_in_groups(self):
        """Groups with empty node_ids shouldn't crash."""
        result = compare_grouping_results(
            [_a([])],
            [_c([])],
        )
        # Both empty sets -> Jaccard is 1.0
        assert result['coverage'] == 1.0

    def test_pattern_accuracy_in_result(self):
        result = compare_grouping_results(
            [_a(['1', '2'], method='pattern')],
            [_c(['1', '2'], pattern='list')],
        )
        assert 'pattern_accuracy' in result
        assert 'pattern' in result['pattern_accuracy']

    def test_stage_a_only_indices(self):
        """Unmatched Stage A candidates are reported by index."""
        result = compare_grouping_results(
            [_a(['1']), _a(['2']), _a(['3'])],
            [_c(['1'])],
        )
        # Only first A candidate matches C
        assert 1 in result['stage_a_only'] or 2 in result['stage_a_only']

    def test_stage_c_only_indices(self):
        """Unmatched Stage C groups are reported by index."""
        result = compare_grouping_results(
            [_a(['1'])],
            [_c(['1']), _c(['99', '100'])],
        )
        assert 1 in result['stage_c_only']


# ---------------------------------------------------------------------------
# compare_grouping_by_section
# ---------------------------------------------------------------------------

class TestCompareGroupingBySection:
    """Per-section graduated comparison and merging."""

    def test_empty_inputs(self):
        result = compare_grouping_by_section([], [])
        assert result['total_sections'] == 0
        assert result['overall_coverage'] == 1.0

    def test_a_only_section(self):
        """Section with Stage A candidates but no Stage C."""
        a = [_a(['1', '2', '3'], parent_id='sec1')]
        result = compare_grouping_by_section(a, [])
        assert result['total_sections'] == 1
        sec = result['sections'][0]
        assert sec['source'] == 'stage_a'

    def test_c_only_section(self):
        """Section with Stage C groups but no Stage A."""
        c_sec = [{'section_id': 'sec1', 'groups': [_c(['1', '2'])]}]
        result = compare_grouping_by_section([], c_sec)
        assert result['total_sections'] == 1
        sec = result['sections'][0]
        assert sec['source'] == 'stage_c'

    def test_multiple_sections(self):
        """Multiple sections are processed independently."""
        a = [
            _a(['1', '2'], parent_id='s1'),
            _a(['3', '4'], parent_id='s2'),
        ]
        c_sec = [
            {'section_id': 's1', 'groups': [_c(['1', '2'])]},
            {'section_id': 's2', 'groups': [_c(['3', '4'])]},
        ]
        result = compare_grouping_by_section(a, c_sec)
        assert result['total_sections'] == 2
        assert result['stage_c_sections'] == 2  # both perfect match

    def test_section_metrics(self):
        """Result includes stage_a_sections, stage_c_sections, merged_sections."""
        a = [_a(['1', '2', '3'], parent_id='sec1')]
        c_sec = [{'section_id': 'sec1', 'groups': [_c(['1', '2', '3'])]}]
        result = compare_grouping_by_section(a, c_sec)
        assert 'stage_a_sections' in result
        assert 'stage_c_sections' in result
        assert 'merged_sections' in result

    def test_overall_coverage_is_average(self):
        """Overall coverage is average across sections."""
        a = [
            _a(['1', '2'], parent_id='s1'),
            _a(['3', '4', '5', '6', '7'], parent_id='s2'),
        ]
        c_sec = [
            {'section_id': 's1', 'groups': [_c(['1', '2'])]},
            # s2: 0 overlap
            {'section_id': 's2', 'groups': [_c(['99'])]},
        ]
        result = compare_grouping_by_section(a, c_sec)
        # s1: coverage=1.0, s2: coverage=0.0, avg=0.5
        assert result['overall_coverage'] == pytest.approx(0.5, abs=0.01)

    def test_parent_field_fallback(self):
        """Stage A candidates using 'parent' instead of 'parent_id' are grouped correctly."""
        a = [{'method': 'pattern', 'node_ids': ['1', '2'], 'parent': 'sec1'}]
        c_sec = [{'section_id': 'sec1', 'groups': [_c(['1', '2'])]}]
        result = compare_grouping_by_section(a, c_sec)
        assert result['total_sections'] == 1


# ---------------------------------------------------------------------------
# _merge_stage_c_with_a_remainder — additional edge cases
# ---------------------------------------------------------------------------

class TestMergeStageCWithARemainder:
    """Additional edge cases beyond test_graduated_merge.py."""

    def test_none_in_stage_a_only_key(self):
        """Missing stage_a_only key -> no error."""
        result = _merge_stage_c_with_a_remainder(
            [_c(['1', '2'])], [_a(['3', '4'])], {}
        )
        assert len(result) == 1  # just c_groups

    def test_multiple_unmatched_a(self):
        """Multiple unmatched A candidates all get added."""
        c_groups = [_c(['1'])]
        a_cands = [_a(['2', '3']), _a(['4', '5']), _a(['6', '7'])]
        comparison = {'stage_a_only': [0, 1, 2]}
        result = _merge_stage_c_with_a_remainder(c_groups, a_cands, comparison)
        assert len(result) == 4  # 1 c + 3 a


# ---------------------------------------------------------------------------
# _merge_stage_a_with_c_confident — additional edge cases
# ---------------------------------------------------------------------------

class TestMergeStageAWithCConfident:
    """Additional edge cases beyond test_graduated_merge.py."""

    def test_none_in_stage_c_only_key(self):
        """Missing stage_c_only key -> no error."""
        result = _merge_stage_a_with_c_confident(
            [_a(['1', '2'])], [_c(['3', '4', '5'])], {}
        )
        assert len(result) == 1  # just a_cands

    def test_exactly_3_nodes_threshold(self):
        """C group with exactly 3 nodes is included."""
        a_cands = [_a(['1'])]
        c_groups = [_c(['2', '3', '4'])]
        comparison = {'stage_a_only': [], 'stage_c_only': [0]}
        result = _merge_stage_a_with_c_confident(a_cands, c_groups, comparison)
        assert len(result) == 2

    def test_2_nodes_below_threshold(self):
        """C group with 2 nodes is excluded."""
        a_cands = [_a(['1'])]
        c_groups = [_c(['2', '3'])]
        comparison = {'stage_a_only': [], 'stage_c_only': [0]}
        result = _merge_stage_a_with_c_confident(a_cands, c_groups, comparison)
        assert len(result) == 1

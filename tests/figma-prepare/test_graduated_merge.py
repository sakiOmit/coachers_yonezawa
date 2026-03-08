"""Tests for graduated Stage A/C merging (Proposal 2).

Replaces the binary STAGE_C_COVERAGE_THRESHOLD decision with 4 tiers:
  Tier 1 (>= 0.8): Stage C fully adopted
  Tier 2 (>= 0.6): Stage C + unmatched Stage A merged
  Tier 3 (>= 0.4): Stage A + high-confidence Stage C
  Tier 4 (< 0.4):  Stage A only
"""
import pytest

from figma_utils.comparison import (
    compare_grouping_by_section,
    _merge_stage_c_with_a_remainder,
    _merge_stage_a_with_c_confident,
)
from figma_utils.constants import (
    STAGE_MERGE_TIER1,
    STAGE_MERGE_TIER2,
    STAGE_MERGE_TIER3,
)


def _a_cand(node_ids, method='proximity', parent_id='sec1'):
    return {'method': method, 'node_ids': node_ids, 'parent_id': parent_id}


def _c_group(node_ids, name='group', pattern='list'):
    return {'name': name, 'pattern': pattern, 'node_ids': node_ids}


# ================================================================
# Constants
# ================================================================

class TestTierConstants:
    """Tier threshold constants are correctly defined."""

    def test_tier1_value(self):
        assert STAGE_MERGE_TIER1 == 0.8

    def test_tier2_value(self):
        assert STAGE_MERGE_TIER2 == 0.6

    def test_tier3_value(self):
        assert STAGE_MERGE_TIER3 == 0.4

    def test_tier_ordering(self):
        assert STAGE_MERGE_TIER1 > STAGE_MERGE_TIER2 > STAGE_MERGE_TIER3


# ================================================================
# _merge_stage_c_with_a_remainder (Tier 2)
# ================================================================

class TestMergeStageCAReminder:
    """Tier 2 merge: Stage C primary + unmatched Stage A supplement."""

    def test_adds_unmatched_a_candidates(self):
        c_groups = [_c_group(['1', '2', '3'])]
        a_cands = [
            _a_cand(['1', '2', '3']),  # matched
            _a_cand(['4', '5']),        # unmatched
        ]
        comparison = {
            'stage_a_only': [1],  # index 1 is unmatched
            'stage_c_only': [],
        }
        result = _merge_stage_c_with_a_remainder(c_groups, a_cands, comparison)
        all_ids = set()
        for r in result:
            all_ids.update(r.get('node_ids', []))
        assert '4' in all_ids
        assert '5' in all_ids
        # Should have c_group + unmatched a_cand = 2 entries
        assert len(result) == 2

    def test_skips_overlapping_a_candidates(self):
        c_groups = [_c_group(['1', '2', '3'])]
        a_cands = [
            _a_cand(['1', '2']),  # mostly overlapping with Stage C (100%)
        ]
        comparison = {
            'stage_a_only': [0],
            'stage_c_only': [],
        }
        result = _merge_stage_c_with_a_remainder(c_groups, a_cands, comparison)
        # Should NOT add the overlapping a_cand
        assert len(result) == 1

    def test_empty_c_groups(self):
        """Empty Stage C groups with unmatched A candidates."""
        a_cands = [_a_cand(['1', '2'])]
        comparison = {'stage_a_only': [0], 'stage_c_only': []}
        result = _merge_stage_c_with_a_remainder([], a_cands, comparison)
        assert len(result) == 1
        assert result[0]['node_ids'] == ['1', '2']

    def test_empty_a_cands(self):
        """No Stage A candidates to supplement."""
        c_groups = [_c_group(['1', '2'])]
        comparison = {'stage_a_only': [], 'stage_c_only': []}
        result = _merge_stage_c_with_a_remainder(c_groups, [], comparison)
        assert len(result) == 1

    def test_out_of_range_index(self):
        """Out-of-range index in stage_a_only is safely skipped."""
        c_groups = [_c_group(['1', '2'])]
        a_cands = [_a_cand(['3', '4'])]
        comparison = {'stage_a_only': [0, 5], 'stage_c_only': []}  # 5 is out of range
        result = _merge_stage_c_with_a_remainder(c_groups, a_cands, comparison)
        assert len(result) == 2  # c_group + a_cand[0]

    def test_empty_node_ids_a_candidate(self):
        """A candidate with empty node_ids is skipped (no division by zero)."""
        c_groups = [_c_group(['1', '2'])]
        a_cands = [_a_cand([])]
        comparison = {'stage_a_only': [0], 'stage_c_only': []}
        result = _merge_stage_c_with_a_remainder(c_groups, a_cands, comparison)
        assert len(result) == 1  # only c_group, empty a_cand skipped

    def test_partial_overlap_below_50_percent(self):
        """A candidate with < 50% overlap is added."""
        c_groups = [_c_group(['1', '2', '3'])]
        a_cands = [_a_cand(['1', '4', '5'])]  # 1/3 = 33% overlap
        comparison = {'stage_a_only': [0], 'stage_c_only': []}
        result = _merge_stage_c_with_a_remainder(c_groups, a_cands, comparison)
        assert len(result) == 2

    def test_exact_50_percent_overlap_skipped(self):
        """A candidate with exactly 50% overlap is NOT added (< 0.5 required)."""
        c_groups = [_c_group(['1', '2', '3'])]
        a_cands = [_a_cand(['1', '4'])]  # 1/2 = 50% overlap
        comparison = {'stage_a_only': [0], 'stage_c_only': []}
        result = _merge_stage_c_with_a_remainder(c_groups, a_cands, comparison)
        assert len(result) == 1  # not added, exactly 50%


# ================================================================
# _merge_stage_a_with_c_confident (Tier 3)
# ================================================================

class TestMergeStageACConfident:
    """Tier 3 merge: Stage A primary + high-confidence Stage C supplement."""

    def test_adds_substantial_c_groups(self):
        a_cands = [_a_cand(['1', '2'])]
        c_groups = [_c_group(['3', '4', '5'])]  # 3+ nodes, novel
        comparison = {
            'stage_a_only': [],
            'stage_c_only': [0],
        }
        result = _merge_stage_a_with_c_confident(a_cands, c_groups, comparison)
        all_ids = set()
        for r in result:
            all_ids.update(r.get('node_ids', []))
        assert '3' in all_ids
        assert '4' in all_ids
        assert '5' in all_ids

    def test_skips_small_c_groups(self):
        a_cands = [_a_cand(['1', '2'])]
        c_groups = [_c_group(['3', '4'])]  # only 2 nodes -> skip
        comparison = {
            'stage_a_only': [],
            'stage_c_only': [0],
        }
        result = _merge_stage_a_with_c_confident(a_cands, c_groups, comparison)
        all_ids = set()
        for r in result:
            all_ids.update(r.get('node_ids', []))
        assert '3' not in all_ids

    def test_skips_overlapping_c_groups(self):
        a_cands = [_a_cand(['1', '2', '3'])]
        c_groups = [_c_group(['1', '2', '3'])]  # same nodes
        comparison = {
            'stage_a_only': [],
            'stage_c_only': [0],
        }
        result = _merge_stage_a_with_c_confident(a_cands, c_groups, comparison)
        assert len(result) == 1  # only original a_cand

    def test_empty_a_cands(self):
        """Empty Stage A candidates with confident C groups."""
        c_groups = [_c_group(['1', '2', '3'])]
        comparison = {'stage_a_only': [], 'stage_c_only': [0]}
        result = _merge_stage_a_with_c_confident([], c_groups, comparison)
        assert len(result) == 1
        assert result[0]['node_ids'] == ['1', '2', '3']

    def test_empty_c_groups(self):
        """No Stage C groups to supplement."""
        a_cands = [_a_cand(['1', '2'])]
        comparison = {'stage_a_only': [], 'stage_c_only': []}
        result = _merge_stage_a_with_c_confident(a_cands, [], comparison)
        assert len(result) == 1

    def test_out_of_range_index(self):
        """Out-of-range index in stage_c_only is safely skipped."""
        a_cands = [_a_cand(['1', '2'])]
        c_groups = [_c_group(['3', '4', '5'])]
        comparison = {'stage_a_only': [], 'stage_c_only': [0, 10]}  # 10 is out of range
        result = _merge_stage_a_with_c_confident(a_cands, c_groups, comparison)
        assert len(result) == 2  # a_cand + c_group[0]

    def test_empty_node_ids_c_group(self):
        """C group with empty node_ids is skipped (< 3 nodes)."""
        a_cands = [_a_cand(['1', '2'])]
        c_groups = [_c_group([])]
        comparison = {'stage_a_only': [], 'stage_c_only': [0]}
        result = _merge_stage_a_with_c_confident(a_cands, c_groups, comparison)
        assert len(result) == 1  # only a_cand


# ================================================================
# compare_grouping_by_section — graduated integration
# ================================================================

class TestGraduatedBySection:
    """End-to-end graduated merging via compare_grouping_by_section."""

    def test_tier1_high_coverage(self):
        """Coverage >= 80% -> Stage C fully adopted."""
        a_cands = [_a_cand(['1', '2', '3'])]
        c_sections = [{'section_id': 'sec1', 'groups': [_c_group(['1', '2', '3'])]}]
        result = compare_grouping_by_section(a_cands, c_sections)
        assert result['sections'][0]['source'] == 'stage_c'

    def test_tier4_low_coverage(self):
        """Coverage < 40% -> Stage A only."""
        a_cands = [
            _a_cand(['1', '2', '3']),
            _a_cand(['4', '5', '6']),
            _a_cand(['7', '8', '9']),
        ]
        c_sections = [{'section_id': 'sec1', 'groups': [_c_group(['10'])]}]  # no overlap
        result = compare_grouping_by_section(a_cands, c_sections)
        assert result['sections'][0]['source'] == 'stage_a'

    def test_tier2_medium_coverage(self):
        """Coverage 60-80% -> merged_c_priority."""
        a_cands = [
            _a_cand(['1', '2', '3']),
            _a_cand(['4', '5', '6']),
            _a_cand(['7', '8']),  # unmatched by Stage C
        ]
        # Stage C covers nodes 1-6 (6/8 = 75% of total Stage A nodes)
        c_sections = [{'section_id': 'sec1', 'groups': [
            _c_group(['1', '2', '3']),
            _c_group(['4', '5', '6']),
        ]}]
        result = compare_grouping_by_section(a_cands, c_sections)
        sec = result['sections'][0]
        # Coverage of A nodes in C: 6/8 = 75% (between 60-80%)
        assert sec['source'] == 'merged_c_priority'

    def test_tier3_low_medium_coverage(self):
        """Coverage 40-60% -> merged_a_priority."""
        # 10 Stage A nodes total
        a_cands = [
            _a_cand(['1', '2', '3', '4', '5']),
            _a_cand(['6', '7', '8', '9', '10']),
        ]
        # Stage C covers 5 of 10 = 50%
        c_sections = [{'section_id': 'sec1', 'groups': [
            _c_group(['1', '2', '3', '4', '5']),
        ]}]
        result = compare_grouping_by_section(a_cands, c_sections)
        sec = result['sections'][0]
        assert sec['coverage'] == 0.5
        assert sec['source'] == 'merged_a_priority'

    def test_merged_sections_count(self):
        """Result includes merged_sections count."""
        a_cands = [_a_cand(['1', '2', '3'])]
        c_sections = [{'section_id': 'sec1', 'groups': [_c_group(['1', '2', '3'])]}]
        result = compare_grouping_by_section(a_cands, c_sections)
        assert 'merged_sections' in result

    def test_empty_inputs(self):
        """Empty inputs include merged_sections key."""
        result = compare_grouping_by_section([], [])
        assert result['merged_sections'] == 0
        assert result['total_sections'] == 0

    def test_mixed_tiers_across_sections(self):
        """Multiple sections with different coverage levels get different tiers."""
        stage_a = [
            # sec-A: perfect coverage expected
            _a_cand(['1', '2'], parent_id='sec-A'),
            # sec-B: no coverage expected
            _a_cand(['3', '4', '5', '6', '7'], parent_id='sec-B'),
        ]
        c_sections = [
            {
                'section_id': 'sec-A',
                'groups': [_c_group(['1', '2'])],  # 100% coverage
            },
            {
                'section_id': 'sec-B',
                'groups': [_c_group(['99'])],  # 0% coverage
            },
        ]
        result = compare_grouping_by_section(stage_a, c_sections)
        sec_a = next(s for s in result['sections'] if s['section_id'] == 'sec-A')
        sec_b = next(s for s in result['sections'] if s['section_id'] == 'sec-B')
        assert sec_a['source'] == 'stage_c'
        assert sec_b['source'] == 'stage_a'

    def test_tier2_includes_unmatched_a_nodes(self):
        """Tier 2 merged result includes Stage A nodes that Stage C missed."""
        a_cands = [
            _a_cand(['1', '2', '3']),
            _a_cand(['4', '5']),  # unmatched
        ]
        # Stage C covers 3 of 5 = 60%, but nodes 1-3 cover the first A cand
        c_sections = [{'section_id': 'sec1', 'groups': [
            _c_group(['1', '2', '3']),
        ]}]
        result = compare_grouping_by_section(a_cands, c_sections)
        sec = result['sections'][0]
        assert sec['source'] == 'merged_c_priority'
        # Candidates should include both Stage C group and unmatched A cand
        all_ids = set()
        for cand in sec['candidates']:
            all_ids.update(cand.get('node_ids', []))
        assert '4' in all_ids
        assert '5' in all_ids

    def test_boundary_exactly_80_percent(self):
        """Coverage exactly 80% should be Tier 1 (stage_c)."""
        # 5 nodes in Stage A, 4 covered by Stage C = 80%
        a_cands = [_a_cand(['1', '2', '3', '4', '5'])]
        c_sections = [{'section_id': 'sec1', 'groups': [
            _c_group(['1', '2', '3', '4']),
        ]}]
        result = compare_grouping_by_section(a_cands, c_sections)
        sec = result['sections'][0]
        assert sec['coverage'] == 0.8
        assert sec['source'] == 'stage_c'

    def test_boundary_just_below_80_percent(self):
        """Coverage just below 80% should be Tier 2 (merged_c_priority)."""
        # 10 nodes, 7 covered = 70%
        a_cands = [_a_cand(['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'])]
        c_sections = [{'section_id': 'sec1', 'groups': [
            _c_group(['1', '2', '3', '4', '5', '6', '7']),
        ]}]
        result = compare_grouping_by_section(a_cands, c_sections)
        sec = result['sections'][0]
        assert sec['coverage'] == 0.7
        assert sec['source'] == 'merged_c_priority'

    def test_boundary_exactly_60_percent(self):
        """Coverage exactly 60% should be Tier 2 (merged_c_priority)."""
        # 5 nodes, 3 covered = 60%
        a_cands = [_a_cand(['1', '2', '3', '4', '5'])]
        c_sections = [{'section_id': 'sec1', 'groups': [
            _c_group(['1', '2', '3']),
        ]}]
        result = compare_grouping_by_section(a_cands, c_sections)
        sec = result['sections'][0]
        assert sec['coverage'] == 0.6
        assert sec['source'] == 'merged_c_priority'

    def test_boundary_exactly_40_percent(self):
        """Coverage exactly 40% should be Tier 3 (merged_a_priority)."""
        # 5 nodes, 2 covered = 40%
        a_cands = [_a_cand(['1', '2', '3', '4', '5'])]
        c_sections = [{'section_id': 'sec1', 'groups': [
            _c_group(['1', '2']),
        ]}]
        result = compare_grouping_by_section(a_cands, c_sections)
        sec = result['sections'][0]
        assert sec['coverage'] == 0.4
        assert sec['source'] == 'merged_a_priority'

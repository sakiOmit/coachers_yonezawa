"""Tests for compare grouping results: comparison logic."""
import json
import os
import tempfile
import pytest

from helpers import run_script, write_fixture

from figma_utils import (
    compare_grouping_by_section,
    compare_grouping_results,
    _stage_a_pattern_key,
    STAGE_C_COVERAGE_THRESHOLD,
)


class TestCompareGroupingResults:
    """Tests for compare_grouping_results (Issue 194 Phase 3)."""

    def test_perfect_match(self):
        """Both stages produce identical groups -> full coverage, Jaccard=1.0."""
        stage_a = [
            {'method': 'pattern', 'node_ids': ['1:1', '1:2', '1:3'], 'count': 3,
             'suggested_name': 'card-list'},
        ]
        stage_c = [
            {'name': 'card-list', 'pattern': 'card', 'node_ids': ['1:1', '1:2', '1:3']},
        ]
        result = compare_grouping_results(stage_a, stage_c)
        assert result['coverage'] == 1.0
        assert result['mean_jaccard'] == 1.0
        assert len(result['matched_pairs']) == 1
        assert result['matched_pairs'][0]['jaccard'] == 1.0
        assert result['stage_a_only'] == []
        assert result['stage_c_only'] == []
        # Pattern accuracy: pattern -> card is valid match
        assert result['pattern_accuracy']['pattern']['matched'] == 1
        assert result['pattern_accuracy']['pattern']['total'] == 1

    def test_partial_overlap(self):
        """Stage A and C overlap partially -> Jaccard between 0 and 1."""
        stage_a = [
            {'method': 'semantic', 'semantic_type': 'card-list',
             'node_ids': ['1:1', '1:2', '1:3', '1:4'], 'count': 4,
             'suggested_name': 'card-list'},
        ]
        stage_c = [
            {'name': 'cards', 'pattern': 'card',
             'node_ids': ['1:1', '1:2', '1:3']},  # missing 1:4
        ]
        result = compare_grouping_results(stage_a, stage_c)
        # 3 out of 4 Stage A nodes covered
        assert result['coverage'] == 0.75
        # Jaccard = 3 / 4 = 0.75
        assert abs(result['jaccard_by_group'][0] - 0.75) < 0.01
        assert len(result['matched_pairs']) == 1

    def test_stage_a_only(self):
        """Stage A detects a group that Stage C misses entirely."""
        stage_a = [
            {'method': 'highlight', 'semantic_type': 'highlight',
             'node_ids': ['2:1', '2:2'], 'count': 2,
             'suggested_name': 'highlight-text'},
            {'method': 'pattern', 'node_ids': ['3:1', '3:2', '3:3'], 'count': 3,
             'suggested_name': 'list-items'},
        ]
        stage_c = [
            {'name': 'card-list', 'pattern': 'card',
             'node_ids': ['3:1', '3:2', '3:3']},
        ]
        result = compare_grouping_results(stage_a, stage_c)
        # highlight group (2:1, 2:2) not covered
        assert result['coverage'] == 3 / 5  # 3 of 5 Stage A nodes covered
        assert len(result['stage_a_only']) == 1
        assert 0 in result['stage_a_only']  # index 0 = highlight
        assert result['stage_c_only'] == []

    def test_stage_c_only(self):
        """Stage C detects a group that Stage A does not have."""
        stage_a = [
            {'method': 'pattern', 'node_ids': ['1:1', '1:2'], 'count': 2,
             'suggested_name': 'list-items'},
        ]
        stage_c = [
            {'name': 'list-items', 'pattern': 'list',
             'node_ids': ['1:1', '1:2']},
            {'name': 'decoration-dots', 'pattern': 'single',
             'node_ids': ['5:1', '5:2']},
        ]
        result = compare_grouping_results(stage_a, stage_c)
        assert len(result['stage_c_only']) == 1
        assert 1 in result['stage_c_only']  # decoration-dots

    def test_both_empty(self):
        """Both empty -> perfect agreement."""
        result = compare_grouping_results([], [])
        assert result['coverage'] == 1.0
        assert result['mean_jaccard'] == 1.0
        assert result['matched_pairs'] == []

    def test_stage_a_empty(self):
        """Stage A empty, Stage C has groups -> coverage=1.0 (nothing to cover)."""
        stage_c = [
            {'name': 'g1', 'pattern': 'card', 'node_ids': ['1:1']},
        ]
        result = compare_grouping_results([], stage_c)
        assert result['coverage'] == 1.0
        assert result['stage_c_only'] == [0]

    def test_stage_c_empty(self):
        """Stage C empty, Stage A has groups -> coverage=0.0."""
        stage_a = [
            {'method': 'pattern', 'node_ids': ['1:1', '1:2'], 'count': 2,
             'suggested_name': 'items'},
        ]
        result = compare_grouping_results(stage_a, [])
        assert result['coverage'] == 0.0
        assert result['mean_jaccard'] == 0.0
        assert result['stage_a_only'] == [0]

    def test_pattern_type_mapping(self):
        """Pattern accuracy correctly maps Stage A methods to Stage C patterns."""
        stage_a = [
            {'method': 'semantic', 'semantic_type': 'card-list',
             'node_ids': ['1:1', '1:2', '1:3'], 'count': 3},
            {'method': 'table', 'node_ids': ['2:1', '2:2', '2:3'], 'count': 3},
            {'method': 'heading-content',
             'node_ids': ['3:1', '3:2'], 'count': 2},
        ]
        stage_c = [
            {'name': 'cards', 'pattern': 'card',
             'node_ids': ['1:1', '1:2', '1:3']},
            {'name': 'data-table', 'pattern': 'table',
             'node_ids': ['2:1', '2:2', '2:3']},
            {'name': 'section-heading', 'pattern': 'heading-pair',
             'node_ids': ['3:1', '3:2']},
        ]
        result = compare_grouping_results(stage_a, stage_c)
        pa = result['pattern_accuracy']
        assert pa['semantic:card-list']['matched'] == 1
        assert pa['table']['matched'] == 1
        assert pa['heading-content']['matched'] == 1
        assert result['mean_jaccard'] == 1.0

    def test_no_match_below_threshold(self):
        """Jaccard below 0.5 -> no match."""
        stage_a = [
            {'method': 'pattern',
             'node_ids': ['1:1', '1:2', '1:3', '1:4', '1:5'], 'count': 5},
        ]
        stage_c = [
            # Only 1 overlap out of 5+4=8 unique -> Jaccard = 1/8 = 0.125
            {'name': 'other', 'pattern': 'list',
             'node_ids': ['1:1', '2:1', '2:2', '2:3']},
        ]
        result = compare_grouping_results(stage_a, stage_c)
        # Jaccard < 0.5 -> no match
        assert len(result['matched_pairs']) == 0
        assert 0 in result['stage_a_only']

    def test_stage_a_pattern_key(self):
        """_stage_a_pattern_key returns correct keys."""
        assert _stage_a_pattern_key({'method': 'semantic', 'semantic_type': 'card-list'}) == 'semantic:card-list'
        assert _stage_a_pattern_key({'method': 'pattern'}) == 'pattern'
        assert _stage_a_pattern_key({'method': 'table'}) == 'table'
        assert _stage_a_pattern_key({'method': 'highlight', 'semantic_type': 'highlight'}) == 'highlight'
        assert _stage_a_pattern_key({'method': 'heading-content'}) == 'heading-content'


# ================================================================
# Issue 226: Section-level (parent_id-based) matching tests
# ================================================================


class TestCompareGroupingResultsWithParentId:
    """Tests for compare_grouping_results parent_id filtering (Issue 226)."""

    def test_compare_grouping_results_with_parent_id_filter(self):
        """parent_id filters Stage A and Stage C to matching section only."""
        stage_a = [
            {'method': 'pattern', 'node_ids': ['1:1', '1:2'], 'parent_id': 'sec-A'},
            {'method': 'pattern', 'node_ids': ['2:1', '2:2'], 'parent_id': 'sec-B'},
        ]
        stage_c = [
            {'name': 'group-a', 'pattern': 'card', 'node_ids': ['1:1', '1:2'],
             'section_id': 'sec-A'},
            {'name': 'group-b', 'pattern': 'list', 'node_ids': ['2:1', '2:2', '2:3'],
             'section_id': 'sec-B'},
        ]
        # Filter to sec-A only
        result = compare_grouping_results(stage_a, stage_c, parent_id='sec-A')
        assert result['coverage'] == 1.0
        assert result['mean_jaccard'] == 1.0
        assert len(result['matched_pairs']) == 1

    def test_parent_id_filter_uses_parent_field(self):
        """Stage A 'parent' field is also accepted for filtering."""
        stage_a = [
            {'method': 'pattern', 'node_ids': ['1:1'], 'parent': 'sec-X'},
        ]
        stage_c = [
            {'name': 'g1', 'pattern': 'card', 'node_ids': ['1:1'],
             'parent_group': 'sec-X'},
        ]
        result = compare_grouping_results(stage_a, stage_c, parent_id='sec-X')
        assert result['coverage'] == 1.0
        assert len(result['matched_pairs']) == 1

    def test_parent_id_no_match_returns_empty(self):
        """parent_id that matches nothing -> both empty behavior."""
        stage_a = [
            {'method': 'pattern', 'node_ids': ['1:1'], 'parent_id': 'sec-A'},
        ]
        stage_c = [
            {'name': 'g1', 'pattern': 'card', 'node_ids': ['1:1'],
             'section_id': 'sec-A'},
        ]
        result = compare_grouping_results(stage_a, stage_c, parent_id='sec-NONE')
        assert result['coverage'] == 1.0  # both empty
        assert result['mean_jaccard'] == 1.0

    def test_parent_id_none_is_current_behavior(self):
        """parent_id=None (default) compares all candidates globally."""
        stage_a = [
            {'method': 'pattern', 'node_ids': ['1:1', '1:2'], 'parent_id': 'sec-A'},
            {'method': 'pattern', 'node_ids': ['2:1', '2:2'], 'parent_id': 'sec-B'},
        ]
        stage_c = [
            {'name': 'g1', 'pattern': 'card', 'node_ids': ['1:1', '1:2'],
             'section_id': 'sec-A'},
            {'name': 'g2', 'pattern': 'list', 'node_ids': ['2:1', '2:2'],
             'section_id': 'sec-B'},
        ]
        result = compare_grouping_results(stage_a, stage_c)
        assert result['coverage'] == 1.0
        assert len(result['matched_pairs']) == 2


class TestCompareGroupingBySection:
    """Tests for compare_grouping_by_section (Issue 226)."""

    def test_compare_grouping_by_section_basic(self):
        """Two sections: Stage C covers one well, other poorly -> mixed adoption."""
        stage_a = [
            # Section A: 3 nodes
            {'method': 'pattern', 'node_ids': ['1:1', '1:2', '1:3'],
             'parent_id': 'sec-A', 'suggested_name': 'cards'},
            # Section B: 3 nodes
            {'method': 'pattern', 'node_ids': ['2:1', '2:2', '2:3'],
             'parent_id': 'sec-B', 'suggested_name': 'items'},
        ]
        stage_c_sections = [
            {
                'section_id': 'sec-A',
                'groups': [
                    {'name': 'card-list', 'pattern': 'card',
                     'node_ids': ['1:1', '1:2', '1:3']},  # perfect match
                ],
            },
            {
                'section_id': 'sec-B',
                'groups': [
                    {'name': 'other', 'pattern': 'list',
                     'node_ids': ['2:1']},  # poor coverage: 1/3
                ],
            },
        ]
        result = compare_grouping_by_section(stage_a, stage_c_sections)
        assert result['total_sections'] == 2
        # sec-A: coverage=1.0 >= 0.8 -> stage_c
        sec_a = next(s for s in result['sections'] if s['section_id'] == 'sec-A')
        assert sec_a['source'] == 'stage_c'
        assert sec_a['coverage'] == 1.0
        # sec-B: coverage=1/3 < 0.8 -> stage_a
        sec_b = next(s for s in result['sections'] if s['section_id'] == 'sec-B')
        assert sec_b['source'] == 'stage_a'
        assert sec_b['coverage'] < 0.8
        # Mixed: 1 stage_a + 1 stage_c
        assert result['stage_a_sections'] == 1
        assert result['stage_c_sections'] == 1

    def test_compare_grouping_by_section_all_stage_c(self):
        """All sections well-covered -> all Stage C adopted."""
        stage_a = [
            {'method': 'pattern', 'node_ids': ['1:1', '1:2'],
             'parent_id': 'sec-A'},
            {'method': 'pattern', 'node_ids': ['2:1', '2:2'],
             'parent_id': 'sec-B'},
        ]
        stage_c_sections = [
            {
                'section_id': 'sec-A',
                'groups': [
                    {'name': 'g1', 'pattern': 'card',
                     'node_ids': ['1:1', '1:2']},
                ],
            },
            {
                'section_id': 'sec-B',
                'groups': [
                    {'name': 'g2', 'pattern': 'list',
                     'node_ids': ['2:1', '2:2']},
                ],
            },
        ]
        result = compare_grouping_by_section(stage_a, stage_c_sections)
        assert result['stage_c_sections'] == 2
        assert result['stage_a_sections'] == 0
        for sec in result['sections']:
            assert sec['source'] == 'stage_c'
            assert sec['coverage'] >= 0.8

    def test_compare_grouping_by_section_all_fallback(self):
        """All sections poorly covered -> all Stage A fallback."""
        stage_a = [
            {'method': 'pattern', 'node_ids': ['1:1', '1:2', '1:3', '1:4', '1:5'],
             'parent_id': 'sec-A'},
            {'method': 'pattern', 'node_ids': ['2:1', '2:2', '2:3', '2:4', '2:5'],
             'parent_id': 'sec-B'},
        ]
        stage_c_sections = [
            {
                'section_id': 'sec-A',
                'groups': [
                    {'name': 'g1', 'pattern': 'card',
                     'node_ids': ['1:1']},  # 1/5 coverage
                ],
            },
            {
                'section_id': 'sec-B',
                'groups': [
                    {'name': 'g2', 'pattern': 'list',
                     'node_ids': ['2:1']},  # 1/5 coverage
                ],
            },
        ]
        result = compare_grouping_by_section(stage_a, stage_c_sections)
        assert result['stage_a_sections'] == 2
        assert result['stage_c_sections'] == 0
        for sec in result['sections']:
            assert sec['source'] == 'stage_a'
            assert sec['coverage'] < 0.8

    def test_compare_grouping_by_section_empty(self):
        """Empty inputs handled gracefully."""
        result = compare_grouping_by_section([], [])
        assert result['sections'] == []
        assert result['overall_coverage'] == 1.0
        assert result['total_sections'] == 0

    def test_compare_grouping_by_section_stage_c_only_sections(self):
        """Stage C has sections not in Stage A -> still processed."""
        stage_a = []
        stage_c_sections = [
            {
                'section_id': 'sec-X',
                'groups': [
                    {'name': 'g1', 'pattern': 'card',
                     'node_ids': ['1:1', '1:2']},
                ],
            },
        ]
        result = compare_grouping_by_section(stage_a, stage_c_sections)
        assert result['total_sections'] == 1
        sec = result['sections'][0]
        assert sec['section_id'] == 'sec-X'
        # No Stage A candidates => coverage=1.0 (nothing to cover) -> stage_c
        assert sec['source'] == 'stage_c'

    def test_compare_grouping_by_section_stage_a_only_sections(self):
        """Stage A has sections not in Stage C -> falls back to Stage A."""
        stage_a = [
            {'method': 'pattern', 'node_ids': ['1:1', '1:2'],
             'parent_id': 'sec-Y'},
        ]
        stage_c_sections = []
        result = compare_grouping_by_section(stage_a, stage_c_sections)
        assert result['total_sections'] == 1
        sec = result['sections'][0]
        assert sec['section_id'] == 'sec-Y'
        # No Stage C groups => coverage=0.0 -> stage_a
        assert sec['source'] == 'stage_a'
        assert sec['coverage'] == 0.0

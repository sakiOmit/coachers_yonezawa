"""Tests for merge-aware deduplication (Round 2, Proposal F)."""
import pytest
from figma_utils.comparison_dedup import (
    deduplicate_candidates, _should_absorb_into_higher,
)


def _cand(node_ids, method='proximity', score=0.5):
    return {'method': method, 'node_ids': list(node_ids), 'score': score}


class TestShouldAbsorbIntoHigher:
    def test_high_loss_small_remainder(self):
        """Losing >30% AND remainder <3 -> absorb"""
        lower = _cand(['A', 'B', 'C', 'D'])
        higher = _cand(['B', 'C', 'D'])
        assert _should_absorb_into_higher(lower, higher) is True

    def test_high_loss_large_remainder(self):
        """Losing >30% BUT remainder >=3 -> don't absorb (still viable)"""
        lower = _cand(['A', 'B', 'C', 'D', 'E', 'F'])
        higher = _cand(['D', 'E', 'F'])
        # loss = 3/6 = 50%, but remaining = 3 -> don't absorb
        assert _should_absorb_into_higher(lower, higher) is False

    def test_low_loss(self):
        """Losing <=30% -> don't absorb (trim is fine)"""
        lower = _cand(['A', 'B', 'C', 'D', 'E'])
        higher = _cand(['E'])
        # loss = 1/5 = 20% -> fine to trim
        assert _should_absorb_into_higher(lower, higher) is False

    def test_empty_lower(self):
        assert _should_absorb_into_higher(_cand([]), _cand(['A'])) is False

    def test_no_overlap(self):
        lower = _cand(['A', 'B'])
        higher = _cand(['C', 'D'])
        assert _should_absorb_into_higher(lower, higher) is False

    def test_complete_overlap(self):
        """100% loss, 0 remaining -> absorb"""
        lower = _cand(['A', 'B'])
        higher = _cand(['A', 'B'])
        assert _should_absorb_into_higher(lower, higher) is True

    def test_large_group_not_absorbed(self):
        """Large group (>6 nodes) should never be absorbed even with high loss."""
        lower = _cand(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'])
        higher = _cand(['C', 'D', 'E', 'F', 'G', 'H'])
        # loss = 6/8 = 75%, remaining = 2 < 3, BUT original has 8 nodes > 6
        assert _should_absorb_into_higher(lower, higher) is False


class TestDeduplicateMergeAware:
    def test_small_remainder_absorbed(self):
        """Group losing most nodes -> remainder absorbed into higher-priority"""
        candidates = [
            _cand(['A', 'B', 'C', 'D'], method='proximity'),   # lower priority
            _cand(['B', 'C', 'D'], method='semantic'),          # higher priority
        ]
        result = deduplicate_candidates(candidates)

        # A should be absorbed into the semantic group
        semantic_groups = [c for c in result if c['method'] == 'semantic']
        assert len(semantic_groups) == 1
        assert 'A' in semantic_groups[0]['node_ids']

    def test_large_remainder_not_absorbed(self):
        """Group with viable remainder after trim -> stays separate"""
        candidates = [
            _cand(['A', 'B', 'C', 'D', 'E', 'F'], method='proximity'),
            _cand(['D', 'E', 'F'], method='semantic'),
        ]
        result = deduplicate_candidates(candidates)

        # Proximity group should still exist with A, B, C
        prox_groups = [c for c in result if c['method'] == 'proximity']
        assert len(prox_groups) == 1
        remaining = set(prox_groups[0]['node_ids'])
        assert 'A' in remaining
        assert 'B' in remaining
        assert 'C' in remaining

    def test_no_conflict_unchanged(self):
        """Non-overlapping groups -> no change"""
        candidates = [
            _cand(['A', 'B'], method='proximity'),
            _cand(['C', 'D'], method='semantic'),
        ]
        result = deduplicate_candidates(candidates)
        assert len(result) == 2

    def test_empty_after_trim_removed(self):
        """Group that becomes empty after trim -> removed entirely"""
        candidates = [
            _cand(['A', 'B'], method='proximity'),
            _cand(['A', 'B'], method='semantic'),
        ]
        result = deduplicate_candidates(candidates)
        # Proximity group fully absorbed, should be removed
        prox_groups = [c for c in result if c['method'] == 'proximity']
        assert len(prox_groups) == 0

    def test_spacing_method_absorbed(self):
        """Spacing groups are also eligible for absorption"""
        candidates = [
            _cand(['A', 'B', 'C', 'D'], method='spacing'),
            _cand(['B', 'C', 'D'], method='semantic'),
        ]
        result = deduplicate_candidates(candidates)
        semantic_groups = [c for c in result if c['method'] == 'semantic']
        assert len(semantic_groups) == 1
        assert 'A' in semantic_groups[0]['node_ids']

    def test_pattern_method_not_absorbed(self):
        """Pattern groups should NOT be absorbed (only proximity/spacing)"""
        candidates = [
            _cand(['A', 'B', 'C', 'D'], method='pattern'),
            _cand(['B', 'C', 'D'], method='semantic'),
        ]
        result = deduplicate_candidates(candidates)
        # Pattern keeps its remainder ['A'] even though < 3
        pattern_groups = [c for c in result if c['method'] == 'pattern']
        assert len(pattern_groups) == 1
        assert pattern_groups[0]['node_ids'] == ['A']

    def test_heading_content_not_absorbed(self):
        """heading-content groups should NOT be absorbed"""
        candidates = [
            _cand(['X', 'Y'], method='heading-content'),
            _cand(['X', 'Z'], method='semantic'),
        ]
        result = deduplicate_candidates(candidates)
        hc_groups = [c for c in result if c['method'] == 'heading-content']
        assert len(hc_groups) == 1
        assert hc_groups[0]['node_ids'] == ['Y']

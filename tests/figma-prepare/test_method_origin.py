"""Tests for method origin propagation.

Verifies that grouping candidates carry 'score' metadata and that the
enriched table can display a Method column from Stage A candidates.
"""
import pytest

from figma_utils.enrichment import _compute_method_tag, generate_enriched_table
from figma_utils.grouping_engine import detect_pattern_groups, detect_spacing_groups
from figma_utils.grouping_proximity import detect_proximity_groups
from figma_utils.grouping_semantic import detect_semantic_groups


# ---------------------------------------------------------------------------
# _compute_method_tag
# ---------------------------------------------------------------------------

class TestComputeMethodTag:
    def test_found_proximity(self):
        candidates = [
            {'method': 'proximity', 'score': 0.72, 'node_ids': ['1:1', '1:2']},
            {'method': 'pattern', 'score': 0.85, 'node_ids': ['2:1', '2:2', '2:3']},
        ]
        assert _compute_method_tag('1:1', candidates) == 'proximity@0.7'
        assert _compute_method_tag('2:2', candidates) == 'pattern@0.8'

    def test_not_found(self):
        candidates = [
            {'method': 'proximity', 'score': 0.72, 'node_ids': ['1:1']},
        ]
        assert _compute_method_tag('9:9', candidates) == '-'

    def test_none_candidates(self):
        assert _compute_method_tag('1:1', None) == '-'

    def test_empty_candidates(self):
        assert _compute_method_tag('1:1', []) == '-'

    def test_missing_score_defaults_to_zero(self):
        candidates = [{'method': 'zone', 'node_ids': ['1:1']}]
        assert _compute_method_tag('1:1', candidates) == 'zone@0.0'

    def test_missing_method_shows_question_mark(self):
        candidates = [{'score': 0.5, 'node_ids': ['1:1']}]
        assert _compute_method_tag('1:1', candidates) == '?@0.5'


# ---------------------------------------------------------------------------
# Enriched table with Method column
# ---------------------------------------------------------------------------

class TestEnrichedTableMethodColumn:
    def _make_child(self, node_id, x=0, y=0, w=100, h=50, node_type='FRAME', name='Frame 1'):
        return {
            'id': node_id, 'type': node_type, 'name': name, 'visible': True,
            'absoluteBoundingBox': {'x': x, 'y': y, 'width': w, 'height': h},
            'children': [],
        }

    def test_with_candidates_shows_method_column(self):
        children = [self._make_child('1:1')]
        candidates = [{'method': 'proximity', 'score': 0.8, 'node_ids': ['1:1']}]
        table = generate_enriched_table(children, stage_a_candidates=candidates)
        assert 'Method' in table
        assert 'proximity@0.8' in table

    def test_without_candidates_no_method_column(self):
        children = [self._make_child('1:1')]
        table = generate_enriched_table(children)
        # Header should not contain Method column
        header_line = table.split('\n')[0]
        assert 'Method' not in header_line

    def test_unmatched_node_shows_dash(self):
        children = [
            self._make_child('1:1'),
            self._make_child('1:2', x=200),
        ]
        candidates = [{'method': 'pattern', 'score': 0.9, 'node_ids': ['1:1']}]
        table = generate_enriched_table(children, stage_a_candidates=candidates)
        lines = table.split('\n')
        # Second data row (index 3) should have '-' for method
        assert 'pattern@0.9' in lines[2]  # first data row
        # The unmatched node's row should have a '-' in the method position
        assert '| - |' in lines[3]  # last column before Text

    def test_multiple_candidates(self):
        children = [
            self._make_child('1:1'),
            self._make_child('2:1', x=200),
        ]
        candidates = [
            {'method': 'proximity', 'score': 0.7, 'node_ids': ['1:1']},
            {'method': 'semantic', 'score': 0.9, 'node_ids': ['2:1']},
        ]
        table = generate_enriched_table(children, stage_a_candidates=candidates)
        assert 'proximity@0.7' in table
        assert 'semantic@0.9' in table


# ---------------------------------------------------------------------------
# Score propagation in detectors
# ---------------------------------------------------------------------------

class TestProximityGroupScore:
    def test_proximity_groups_have_score(self):
        children = [
            {'id': '1:1', 'type': 'FRAME', 'name': 'A', 'visible': True,
             'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 50}, 'children': []},
            {'id': '1:2', 'type': 'FRAME', 'name': 'B', 'visible': True,
             'absoluteBoundingBox': {'x': 110, 'y': 0, 'width': 100, 'height': 50}, 'children': []},
        ]
        groups = detect_proximity_groups(children)
        for g in groups:
            assert 'score' in g
            assert 0.0 <= g['score'] <= 1.0


class TestPatternGroupScore:
    def test_pattern_groups_have_score(self):
        # 3 identical FRAME nodes → pattern detection
        children = [
            {'id': f'1:{i}', 'type': 'FRAME', 'name': f'Item {i}', 'visible': True,
             'absoluteBoundingBox': {'x': i * 120, 'y': 0, 'width': 100, 'height': 50},
             'children': [{'type': 'TEXT', 'visible': True, 'name': f'T{i}',
                           'absoluteBoundingBox': {'x': i * 120, 'y': 0, 'width': 80, 'height': 20}}]}
            for i in range(4)
        ]
        groups = detect_pattern_groups(children)
        for g in groups:
            assert 'score' in g
            assert 0.0 <= g['score'] <= 1.0


class TestSpacingGroupScore:
    def test_spacing_groups_have_score(self):
        # 4 evenly spaced elements
        children = [
            {'id': f'1:{i}', 'type': 'FRAME', 'name': f'Item {i}', 'visible': True,
             'absoluteBoundingBox': {'x': i * 120, 'y': 0, 'width': 100, 'height': 50},
             'children': []}
            for i in range(4)
        ]
        groups = detect_spacing_groups(children)
        for g in groups:
            assert 'score' in g
            assert 0.0 <= g['score'] <= 1.0


class TestSemanticGroupScore:
    def test_card_detection_has_score(self):
        # 3 card-like nodes
        children = [
            {'id': f'1:{i}', 'type': 'FRAME', 'name': f'Card {i}', 'visible': True,
             'absoluteBoundingBox': {'x': i * 200, 'y': 0, 'width': 180, 'height': 300},
             'children': [
                 {'type': 'RECTANGLE', 'visible': True, 'name': 'img',
                  'absoluteBoundingBox': {'x': i * 200, 'y': 0, 'width': 180, 'height': 120}},
                 {'type': 'TEXT', 'visible': True, 'name': 'title', 'characters': f'Title {i}',
                  'absoluteBoundingBox': {'x': i * 200, 'y': 130, 'width': 160, 'height': 20}},
             ]}
            for i in range(3)
        ]
        groups = detect_semantic_groups(children)
        card_groups = [g for g in groups if g.get('semantic_type') == 'card-list']
        assert len(card_groups) >= 1
        for g in card_groups:
            assert g['score'] == 0.9

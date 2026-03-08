"""Tests for cross-section pattern registry (Round 2, Proposal D)."""
import pytest
from figma_utils.pattern_registry import (
    build_pattern_registry, lookup_pattern, format_registry_summary,
    _walk_for_patterns,
)
from figma_utils.scoring import structure_hash


def _leaf(node_id, node_type='TEXT'):
    return {'id': node_id, 'type': node_type, 'name': f'{node_type} {node_id}',
            'visible': True, 'children': []}


def _frame(node_id, name, children):
    return {'id': node_id, 'type': 'FRAME', 'name': name,
            'visible': True, 'children': children}


def _instance(node_id, name, children):
    return {'id': node_id, 'type': 'INSTANCE', 'name': name,
            'visible': True, 'children': children}


class TestBuildPatternRegistry:
    def test_detects_repeated_patterns(self):
        """Same structure in 2 sections -> registered"""
        card1 = _frame('c1', 'Card 1', [_leaf('t1'), _leaf('r1', 'RECTANGLE')])
        card2 = _frame('c2', 'Card 2', [_leaf('t2'), _leaf('r2', 'RECTANGLE')])
        card3 = _frame('c3', 'Card 3', [_leaf('t3'), _leaf('r3', 'RECTANGLE')])

        section1 = _frame('s1', 'section-features', [card1, card2])
        section2 = _frame('s2', 'section-about', [card3])
        root = _frame('root', 'Page', [section1, section2])

        registry = build_pattern_registry(root, min_occurrences=2)
        # card structure hash should appear 3 times
        assert len(registry) >= 1
        # At least one entry with count >= 2
        assert any(v['count'] >= 2 for v in registry.values())

    def test_single_occurrence_excluded(self):
        """Unique structures (only 1 occurrence) are excluded"""
        unique = _frame('u1', 'unique', [_leaf('t1'), _leaf('v1', 'VECTOR'), _leaf('e1', 'ELLIPSE')])
        root = _frame('root', 'Page', [unique])
        registry = build_pattern_registry(root, min_occurrences=2)
        assert len(registry) == 0

    def test_sections_tracked(self):
        """Registry tracks which sections contain the pattern"""
        card1 = _frame('c1', 'Frame 1', [_leaf('t1')])
        card2 = _frame('c2', 'Frame 2', [_leaf('t2')])

        sec1 = _frame('s1', 'section-A', [card1])
        sec2 = _frame('s2', 'section-B', [card2])
        root = _frame('root', 'Page', [sec1, sec2])

        registry = build_pattern_registry(root, min_occurrences=2)
        for v in registry.values():
            if v['count'] >= 2:
                assert len(v['sections']) >= 2

    def test_example_ids_limited_to_5(self):
        """example_ids capped at 5"""
        cards = [_frame(f'c{i}', f'Frame {i}', [_leaf(f't{i}')]) for i in range(10)]
        root = _frame('root', 'Page', cards)
        registry = build_pattern_registry(root, min_occurrences=2)
        for v in registry.values():
            assert len(v['example_ids']) <= 5

    def test_empty_root(self):
        root = _frame('root', 'Page', [])
        registry = build_pattern_registry(root)
        assert registry == {}

    def test_hidden_nodes_excluded(self):
        card1 = _frame('c1', 'Frame 1', [_leaf('t1')])
        card2 = {'id': 'c2', 'type': 'FRAME', 'name': 'Frame 2',
                 'visible': False, 'children': [_leaf('t2')]}
        root = _frame('root', 'Page', [card1, card2])
        registry = build_pattern_registry(root, min_occurrences=2)
        # Only 1 visible card -> not enough for registry
        assert len(registry) == 0

    def test_instance_nodes_tracked(self):
        inst1 = _instance('i1', 'Button', [_leaf('t1')])
        inst2 = _instance('i2', 'Button', [_leaf('t2')])
        root = _frame('root', 'Page', [inst1, inst2])
        registry = build_pattern_registry(root, min_occurrences=2)
        assert any(v['node_type'] == 'INSTANCE' for v in registry.values())

    def test_list_input_basic(self):
        """build_pattern_registry() accepts a list of children (Issue #273)"""
        card1 = _frame('c1', 'Frame 1', [_leaf('t1'), _leaf('r1', 'RECTANGLE')])
        card2 = _frame('c2', 'Frame 2', [_leaf('t2'), _leaf('r2', 'RECTANGLE')])
        card3 = _frame('c3', 'Frame 3', [_leaf('t3'), _leaf('r3', 'RECTANGLE')])
        root_children = [card1, card2, card3]
        registry = build_pattern_registry(root_children, min_occurrences=2)
        assert len(registry) >= 1
        assert any(v['count'] >= 2 for v in registry.values())

    def test_list_input_empty(self):
        """Empty list input returns empty registry (Issue #273)"""
        registry = build_pattern_registry([])
        assert registry == {}

    def test_dict_input_empty(self):
        """Empty dict with no children returns empty registry"""
        registry = build_pattern_registry({'type': 'FRAME', 'name': 'root', 'children': []})
        assert registry == {}

    def test_list_input_with_hidden_children(self):
        """List input filters hidden children (Issue #273)"""
        card1 = _frame('c1', 'Frame 1', [_leaf('t1')])
        card2 = {'id': 'c2', 'type': 'FRAME', 'name': 'Frame 2',
                 'visible': False, 'children': [_leaf('t2')]}
        card3 = _frame('c3', 'Frame 3', [_leaf('t3')])
        root_children = [card1, card2, card3]
        registry = build_pattern_registry(root_children, min_occurrences=2)
        # card2 is hidden, so only 2 visible cards with same structure
        assert any(v['count'] >= 2 for v in registry.values())
        # Verify hidden node ID is not in example_ids
        for v in registry.values():
            assert 'c2' not in v['example_ids']


class TestLookupPattern:
    def test_found(self):
        registry = {'FRAME:[TEXT]': {'count': 3, 'sections': ['A'], 'example_ids': ['1']}}
        assert lookup_pattern('FRAME:[TEXT]', registry) is not None

    def test_not_found(self):
        assert lookup_pattern('NONEXISTENT', {}) is None


class TestFormatRegistrySummary:
    def test_empty_registry(self):
        assert format_registry_summary({}) == ''

    def test_format_with_entries(self):
        registry = {
            'FRAME:[TEXT,RECTANGLE]': {
                'count': 5, 'sections': ['sec-A', 'sec-B'],
                'example_ids': ['1', '2'], 'node_type': 'FRAME',
            }
        }
        result = format_registry_summary(registry)
        assert 'Cross-Section Pattern Registry' in result
        assert '5x' in result
        assert 'sec-A' in result

    def test_max_entries_limit(self):
        registry = {f'hash-{i}': {'count': i + 2, 'sections': ['A'],
                                   'example_ids': ['1'], 'node_type': 'FRAME'}
                    for i in range(20)}
        result = format_registry_summary(registry, max_entries=5)
        # Should only show top 5
        lines = [l for l in result.split('\n') if l.startswith(('1.', '2.', '3.', '4.', '5.', '6.'))]
        assert len(lines) <= 5

    def test_many_sections_truncated(self):
        registry = {
            'FRAME:[TEXT]': {
                'count': 10, 'sections': ['s1', 's2', 's3', 's4', 's5'],
                'example_ids': ['1'], 'node_type': 'FRAME',
            }
        }
        result = format_registry_summary(registry)
        assert '+2 more' in result  # 5 sections, shows 3 + "+2 more"

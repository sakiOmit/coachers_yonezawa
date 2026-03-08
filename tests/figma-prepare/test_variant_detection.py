"""Tests for component variant detection (Proposal 5)."""
import pytest
from figma_utils.grouping_semantic import detect_variant_groups


def _instance(node_id, comp_id, name='Instance'):
    return {
        'id': node_id, 'type': 'INSTANCE', 'componentId': comp_id,
        'name': name, 'visible': True,
        'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 50},
        'children': [],
    }


def _frame(node_id, name='Frame'):
    return {
        'id': node_id, 'type': 'FRAME', 'name': name, 'visible': True,
        'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 50},
        'children': [],
    }


class TestDetectVariantGroups:
    def test_same_component_id_grouped(self):
        children = [
            _instance('1:1', 'comp-A', 'Button/Primary'),
            _instance('1:2', 'comp-A', 'Button/Secondary'),
            _instance('1:3', 'comp-A', 'Button/Tertiary'),
        ]
        result = detect_variant_groups(children)
        assert len(result) == 1
        assert set(result[0]['node_ids']) == {'1:1', '1:2', '1:3'}
        assert result[0]['method'] == 'variant'
        assert result[0]['score'] == 0.95

    def test_different_component_ids_separate(self):
        children = [
            _instance('1:1', 'comp-A'),
            _instance('1:2', 'comp-B'),
            _instance('1:3', 'comp-A'),
        ]
        result = detect_variant_groups(children)
        assert len(result) == 1  # Only comp-A has 2+ instances
        assert set(result[0]['node_ids']) == {'1:1', '1:3'}

    def test_single_instance_not_grouped(self):
        children = [
            _instance('1:1', 'comp-A'),
            _instance('1:2', 'comp-B'),
        ]
        result = detect_variant_groups(children)
        assert len(result) == 0

    def test_non_instance_nodes_ignored(self):
        children = [
            _frame('1:1'),
            _instance('1:2', 'comp-A'),
            _instance('1:3', 'comp-A'),
        ]
        result = detect_variant_groups(children)
        assert len(result) == 1
        assert '1:1' not in result[0]['node_ids']

    def test_no_component_id_ignored(self):
        children = [
            {'id': '1:1', 'type': 'INSTANCE', 'name': 'No ID', 'visible': True,
             'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 50}, 'children': []},
            {'id': '1:2', 'type': 'INSTANCE', 'name': 'No ID 2', 'visible': True,
             'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 50}, 'children': []},
        ]
        result = detect_variant_groups(children)
        assert len(result) == 0

    def test_suggested_name_from_component(self):
        children = [
            _instance('1:1', 'comp-A', 'Card/Featured'),
            _instance('1:2', 'comp-A', 'Card/Standard'),
        ]
        result = detect_variant_groups(children)
        assert len(result) == 1
        assert 'card' in result[0]['suggested_name']

    def test_empty_children(self):
        assert detect_variant_groups([]) == []

    def test_hidden_instances_included(self):
        """Visible filtering should happen before calling this function."""
        children = [
            _instance('1:1', 'comp-A'),
            _instance('1:2', 'comp-A'),
        ]
        result = detect_variant_groups(children)
        assert len(result) == 1

    def test_multiple_component_groups(self):
        """Multiple different componentIds each with 2+ instances."""
        children = [
            _instance('1:1', 'comp-A', 'Button/Primary'),
            _instance('1:2', 'comp-A', 'Button/Secondary'),
            _instance('1:3', 'comp-B', 'Card/Small'),
            _instance('1:4', 'comp-B', 'Card/Large'),
            _instance('1:5', 'comp-B', 'Card/Medium'),
        ]
        result = detect_variant_groups(children)
        assert len(result) == 2
        ids_per_group = [set(r['node_ids']) for r in result]
        assert {'1:1', '1:2'} in ids_per_group
        assert {'1:3', '1:4', '1:5'} in ids_per_group

    def test_fallback_name_without_slash(self):
        """Instances without '/' in name get fallback naming."""
        children = [
            _instance('1:1', 'comp-A', 'SimpleButton'),
            _instance('1:2', 'comp-A', 'SimpleButton'),
        ]
        result = detect_variant_groups(children)
        assert len(result) == 1
        assert result[0]['suggested_name'].startswith('variant-group-')

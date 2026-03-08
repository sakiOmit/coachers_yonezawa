"""Tests for 2-level structure hash."""
import pytest
from figma_utils.scoring import structure_hash, structure_similarity


def _node(node_type, children=None):
    node = {'type': node_type, 'visible': True, 'children': children or []}
    return node


def _leaf(node_type):
    return {'type': node_type, 'visible': True, 'children': []}


class TestStructureHashDepth:
    def test_depth1_same_as_legacy(self):
        """depth=1 should produce same format as before"""
        node = _node('FRAME', [_leaf('TEXT'), _leaf('RECTANGLE')])
        h = structure_hash(node, depth=1)
        assert h == 'FRAME:[RECTANGLE,TEXT]'
        assert '|' not in h

    def test_depth2_adds_grandchild_info(self):
        """depth=2 adds |GC:count:dominant_type"""
        child = _node('FRAME', [_leaf('TEXT'), _leaf('TEXT'), _leaf('VECTOR')])
        node = _node('FRAME', [child])
        h = structure_hash(node, depth=2)
        assert '|GC:' in h
        assert 'TEXT' in h.split('|')[1]  # TEXT is dominant

    def test_depth2_leaf_children_no_gc(self):
        """Leaf children (no grandchildren) -> no GC suffix"""
        node = _node('FRAME', [_leaf('TEXT'), _leaf('RECTANGLE')])
        h = structure_hash(node, depth=2)
        assert '|GC:' not in h  # gc_count=0, no suffix

    def test_depth2_default(self):
        """depth defaults to 2"""
        child = _node('FRAME', [_leaf('TEXT')])
        node = _node('FRAME', [child])
        h1 = structure_hash(node)
        h2 = structure_hash(node, depth=2)
        assert h1 == h2

    def test_different_gc_counts_differ(self):
        """Nodes with same children but different grandchildren produce different hashes"""
        child_a = _node('FRAME', [_leaf('TEXT')])
        child_b = _node('FRAME', [_leaf('TEXT'), _leaf('TEXT'), _leaf('RECTANGLE')])
        node_a = _node('FRAME', [child_a, _leaf('RECTANGLE')])
        node_b = _node('FRAME', [child_b, _leaf('RECTANGLE')])
        ha = structure_hash(node_a)
        hb = structure_hash(node_b)
        assert ha != hb  # Same L1, different L2

    def test_leaf_node(self):
        """Leaf node returns just type string"""
        assert structure_hash(_leaf('TEXT')) == 'TEXT'

    def test_hidden_grandchildren_excluded(self):
        """Hidden grandchildren should not contribute to GC count"""
        child = _node('FRAME', [
            _leaf('TEXT'),
            {'type': 'RECTANGLE', 'visible': False},
        ])
        node = _node('FRAME', [child])
        h = structure_hash(node, depth=2)
        # Only 1 visible grandchild (TEXT)
        assert '|GC:1:TEXT' in h

    def test_multiple_children_gc_aggregated(self):
        """Grandchildren from all children are aggregated"""
        child1 = _node('FRAME', [_leaf('TEXT'), _leaf('TEXT')])
        child2 = _node('FRAME', [_leaf('RECTANGLE')])
        node = _node('FRAME', [child1, child2])
        h = structure_hash(node, depth=2)
        assert '|GC:3:TEXT' in h  # 2 TEXT + 1 RECTANGLE = 3, dominant=TEXT


class TestStructureSimilarityDepth2:
    def test_identical_l2_hashes(self):
        """Identical 2-level hashes -> 1.0"""
        h = 'FRAME:[RECTANGLE,TEXT]|GC:3:TEXT'
        assert structure_similarity(h, h) == pytest.approx(1.0)

    def test_same_l1_different_l2(self):
        """Same children, different grandchild counts -> < 1.0 but > 0.5"""
        ha = 'FRAME:[RECTANGLE,TEXT]|GC:3:TEXT'
        hb = 'FRAME:[RECTANGLE,TEXT]|GC:8:TEXT'
        sim = structure_similarity(ha, hb)
        assert 0.5 < sim < 1.0

    def test_different_l1_same_l2(self):
        """Different children, same grandchildren -> low similarity"""
        ha = 'FRAME:[RECTANGLE,TEXT]|GC:3:TEXT'
        hb = 'FRAME:[VECTOR,ELLIPSE]|GC:3:TEXT'
        sim = structure_similarity(ha, hb)
        assert sim < 0.5

    def test_backward_compat_l1_only(self):
        """Old-format (L1 only) hashes still work"""
        ha = 'FRAME:[RECTANGLE,TEXT]'
        hb = 'FRAME:[RECTANGLE,TEXT]'
        assert structure_similarity(ha, hb) == pytest.approx(1.0)

    def test_mixed_l1_and_l2(self):
        """One L1-only, one L2 -> uses L1 only (backward compat)"""
        ha = 'FRAME:[RECTANGLE,TEXT]'
        hb = 'FRAME:[RECTANGLE,TEXT]|GC:5:TEXT'
        sim = structure_similarity(ha, hb)
        assert sim == pytest.approx(1.0)  # L1 match is enough

    def test_dominant_type_bonus(self):
        """Same dominant type -> slight bonus"""
        ha = 'FRAME:[TEXT]|GC:5:TEXT'
        hb = 'FRAME:[TEXT]|GC:3:TEXT'  # same dominant type
        hc = 'FRAME:[TEXT]|GC:3:RECTANGLE'  # different dominant type
        sim_same = structure_similarity(ha, hb)
        sim_diff = structure_similarity(ha, hc)
        assert sim_same > sim_diff

    def test_l2_zero_gc_count(self):
        """Both hashes with GC:0 -> l2_sim=1.0"""
        ha = 'FRAME:[TEXT]|GC:0:'
        hb = 'FRAME:[TEXT]|GC:0:'
        assert structure_similarity(ha, hb) == pytest.approx(1.0)

    def test_leaf_hashes_backward_compat(self):
        """Leaf-type hashes (no brackets) still work"""
        assert structure_similarity('TEXT', 'TEXT') == pytest.approx(1.0)
        assert structure_similarity('TEXT', 'IMAGE') == pytest.approx(0.0)

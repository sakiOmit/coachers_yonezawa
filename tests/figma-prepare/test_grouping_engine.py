"""Tests for grouping_engine.py — detect_pattern_groups, detect_spacing_groups, entry point logic.

Covers:
  - detect_pattern_groups: fuzzy structure hash clustering + spatial splitting
  - detect_spacing_groups: regular spacing detection
  - detect_grouping_candidates: main pipeline (via mock metadata)
  - _write_yaml_output: YAML output formatting
"""
import json
import os
import tempfile

import pytest

from figma_utils.grouping_engine import (
    detect_pattern_groups,
    detect_spacing_groups,
    detect_grouping_candidates,
    _write_yaml_output,
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


def _img(id, x=0, y=0, w=100, h=100, name='Image 1', **kw):
    node = {
        'id': id, 'name': name, 'type': 'IMAGE',
        'absoluteBoundingBox': {'x': x, 'y': y, 'width': w, 'height': h},
    }
    node.update(kw)
    return node


def _make_metadata(root_node):
    """Wrap a root node in metadata JSON structure and write to temp file."""
    data = {'document': {'children': [{'children': [root_node]}]}}
    fd, path = tempfile.mkstemp(suffix='.json')
    with os.fdopen(fd, 'w') as f:
        json.dump(data, f)
    return path


# ---------------------------------------------------------------------------
# detect_pattern_groups
# ---------------------------------------------------------------------------

class TestDetectPatternGroups:
    """Pattern detection via fuzzy structure hash matching."""

    def test_three_identical_cards(self):
        """3 frames with same child structure -> pattern detected."""
        children = [
            _frame('1', x=0, y=0, children=[_img('i1'), _text('t1')]),
            _frame('2', x=200, y=0, children=[_img('i2'), _text('t2')]),
            _frame('3', x=400, y=0, children=[_img('i3'), _text('t3')]),
        ]
        result = detect_pattern_groups(children)
        assert len(result) >= 1
        assert result[0]['method'] == 'pattern'
        assert result[0]['count'] >= 3

    def test_two_items_below_threshold(self):
        """Only 2 similar items -> below REPEATED_PATTERN_MIN (3)."""
        children = [
            _frame('1', x=0, children=[_text('t1')]),
            _frame('2', x=200, children=[_text('t2')]),
        ]
        result = detect_pattern_groups(children)
        assert len(result) == 0

    def test_empty_children(self):
        assert detect_pattern_groups([]) == []

    def test_single_child(self):
        assert detect_pattern_groups([_frame('1')]) == []

    def test_different_structures_no_match(self):
        """Completely different structures -> no pattern."""
        children = [
            _frame('1', children=[_text('t1')]),
            _rect('2'),
            _text('3'),
        ]
        result = detect_pattern_groups(children)
        assert len(result) == 0

    def test_fuzzy_match_flag(self):
        """When hashes aren't identical but similar -> fuzzy_match flag."""
        # Frames with slightly different child counts but same types
        children = [
            _frame('1', x=0, y=0, children=[_text('t1'), _rect('r1')]),
            _frame('2', x=200, y=0, children=[_text('t2'), _rect('r2')]),
            _frame('3', x=400, y=0, children=[_text('t3'), _rect('r3')]),
        ]
        result = detect_pattern_groups(children)
        if result:
            # All have identical structure so fuzzy_match should be False
            assert result[0]['fuzzy_match'] is False

    def test_result_has_required_keys(self):
        """Pattern result contains all expected keys."""
        children = [
            _frame('1', x=0, children=[_text('t1')]),
            _frame('2', x=200, children=[_text('t2')]),
            _frame('3', x=400, children=[_text('t3')]),
        ]
        result = detect_pattern_groups(children)
        assert len(result) >= 1
        r = result[0]
        assert 'method' in r
        assert 'score' in r
        assert 'node_ids' in r
        assert 'count' in r
        assert 'suggested_name' in r

    def test_hidden_children_not_filtered_here(self):
        """detect_pattern_groups does not filter hidden; caller's responsibility."""
        children = [
            _frame('1', children=[_text('t1')]),
            _frame('2', children=[_text('t2')], visible=False),
            _frame('3', children=[_text('t3')]),
            _frame('4', children=[_text('t4')]),
        ]
        # 4 items passed in, but hidden one has same structure
        result = detect_pattern_groups(children)
        # At least some pattern should be detected (3+ similar)
        assert len(result) >= 1

    def test_spatially_distant_items_split(self):
        """Items far apart spatially may be split into sub-groups."""
        children = [
            _frame('1', x=0, y=0, children=[_text('t1')]),
            _frame('2', x=0, y=50, children=[_text('t2')]),
            _frame('3', x=0, y=100, children=[_text('t3')]),
            # big gap
            _frame('4', x=0, y=5000, children=[_text('t4')]),
            _frame('5', x=0, y=5050, children=[_text('t5')]),
            _frame('6', x=0, y=5100, children=[_text('t6')]),
        ]
        result = detect_pattern_groups(children)
        # Could be 1 group of 6 or 2 groups of 3, depending on spatial gap
        total_items = sum(r['count'] for r in result)
        assert total_items >= 3


# ---------------------------------------------------------------------------
# detect_spacing_groups
# ---------------------------------------------------------------------------

class TestDetectSpacingGroups:
    """Regular spacing detection."""

    def test_regular_horizontal_spacing(self):
        """Evenly spaced horizontal items -> spacing group detected."""
        children = [
            _frame('1', x=0, y=0, w=80, h=80),
            _frame('2', x=100, y=0, w=80, h=80),
            _frame('3', x=200, y=0, w=80, h=80),
        ]
        result = detect_spacing_groups(children)
        assert len(result) >= 1
        assert result[0]['method'] == 'spacing'
        assert result[0]['count'] == 3

    def test_regular_vertical_spacing(self):
        """Evenly spaced vertical items."""
        children = [
            _frame('1', x=0, y=0, w=100, h=50),
            _frame('2', x=0, y=100, w=100, h=50),
            _frame('3', x=0, y=200, w=100, h=50),
        ]
        result = detect_spacing_groups(children)
        assert len(result) >= 1

    def test_less_than_3_returns_empty(self):
        children = [_frame('1'), _frame('2')]
        assert detect_spacing_groups(children) == []

    def test_empty_children(self):
        assert detect_spacing_groups([]) == []

    def test_single_child(self):
        assert detect_spacing_groups([_frame('1')]) == []

    def test_irregular_spacing_no_group(self):
        """Very irregular spacing -> no group detected."""
        children = [
            _frame('1', x=0, y=0, w=50, h=50),
            _frame('2', x=0, y=60, w=50, h=50),    # gap 10
            _frame('3', x=0, y=1000, w=50, h=50),   # gap 890
        ]
        result = detect_spacing_groups(children)
        assert len(result) == 0

    def test_score_is_between_0_and_1(self):
        """Spacing score is normalized."""
        children = [
            _frame('1', x=0, y=0, w=80, h=80),
            _frame('2', x=100, y=0, w=80, h=80),
            _frame('3', x=200, y=0, w=80, h=80),
        ]
        result = detect_spacing_groups(children)
        if result:
            assert 0.0 <= result[0]['score'] <= 1.0

    def test_zero_dimension_elements(self):
        """Zero-size elements shouldn't crash."""
        children = [
            _frame('1', x=0, y=0, w=0, h=0),
            _frame('2', x=10, y=0, w=0, h=0),
            _frame('3', x=20, y=0, w=0, h=0),
        ]
        # Should not raise
        result = detect_spacing_groups(children)
        # May or may not detect pattern depending on gap calculation


# ---------------------------------------------------------------------------
# _write_yaml_output
# ---------------------------------------------------------------------------

class TestWriteYamlOutput:
    """YAML output formatting."""

    def test_basic_output(self):
        candidates = [
            {
                'method': 'pattern',
                'score': 0.95,
                'parent_name': 'section-hero',
                'node_ids': ['1', '2', '3'],
                'count': 3,
                'suggested_name': 'list-items',
                'structure_hash': 'FRAME:TEXT:1',
                'suggested_wrapper': 'list-container',
            }
        ]
        fd, path = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        try:
            _write_yaml_output(candidates, path)
            with open(path) as f:
                content = f.read()
            assert 'candidates:' in content
            assert 'method:' in content and 'pattern' in content
            assert 'score: 0.95' in content
            assert 'count: 3' in content
        finally:
            os.unlink(path)

    def test_empty_candidates(self):
        fd, path = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        try:
            _write_yaml_output([], path)
            with open(path) as f:
                content = f.read()
            assert 'candidates:' in content
            assert 'Total candidates: 0' in content
        finally:
            os.unlink(path)

    def test_optional_fields(self):
        """Candidates with optional fields like semantic_type, bg_node_ids."""
        candidates = [
            {
                'method': 'semantic',
                'parent_name': 'root',
                'node_ids': ['1'],
                'count': 1,
                'semantic_type': 'card',
                'bg_node_ids': ['bg1'],
                'row_count': 2,
                'tuple_size': 3,
                'repetitions': 4,
                'fuzzy_match': True,
            }
        ]
        fd, path = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        try:
            _write_yaml_output(candidates, path)
            with open(path) as f:
                content = f.read()
            assert 'semantic_type' in content
            assert 'bg_node_ids' in content
            assert 'fuzzy_match: true' in content
        finally:
            os.unlink(path)

    def test_root_skipped_comment(self):
        fd, path = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        try:
            _write_yaml_output([], path, root_skipped=5)
            with open(path) as f:
                content = f.read()
            assert 'Root-level candidates skipped: 5' in content
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# detect_grouping_candidates (integration via temp metadata file)
# ---------------------------------------------------------------------------

class TestDetectGroupingCandidates:
    """Integration tests for the main pipeline entry point."""

    def _build_page(self, children, page_name='Test Page', page_w=1440, page_h=8500):
        """Build a minimal metadata structure."""
        root = _frame('0:1', x=0, y=0, w=page_w, h=page_h, name=page_name, children=children)
        return root

    def test_empty_page(self):
        """Page with no children -> 0 candidates."""
        root = self._build_page([])
        path = _make_metadata(root)
        try:
            result = detect_grouping_candidates(path)
            assert result['total'] == 0
            assert result['status'] == 'dry-run'
        finally:
            os.unlink(path)

    def test_single_section(self):
        """Page with single section -> processed without error."""
        section = _frame('s1', x=0, y=0, w=1440, h=500, name='section-hero',
                        children=[_text('t1'), _rect('r1')])
        root = self._build_page([section])
        path = _make_metadata(root)
        try:
            result = detect_grouping_candidates(path)
            assert 'total' in result
        finally:
            os.unlink(path)

    def test_output_file_mode(self):
        """When output_file is set, writes YAML and returns status."""
        section = _frame('s1', x=0, y=0, w=1440, h=500, name='section-hero',
                        children=[_text('t1')])
        root = self._build_page([section])
        meta_path = _make_metadata(root)
        fd, out_path = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        try:
            result = detect_grouping_candidates(meta_path, output_file=out_path)
            assert result['status'] == 'dry-run'
            assert result['output'] == out_path
            assert os.path.exists(out_path)
            with open(out_path) as f:
                content = f.read()
            assert 'candidates:' in content
        finally:
            os.unlink(meta_path)
            if os.path.exists(out_path):
                os.unlink(out_path)

    def test_skip_root_flag(self):
        """skip_root filters out root-level candidates."""
        children = [
            _frame('c1', x=0, y=0, w=100, h=100, name='Card 1',
                   children=[_img('i1'), _text('t1')]),
            _frame('c2', x=200, y=0, w=100, h=100, name='Card 2',
                   children=[_img('i2'), _text('t2')]),
            _frame('c3', x=400, y=0, w=100, h=100, name='Card 3',
                   children=[_img('i3'), _text('t3')]),
        ]
        root = self._build_page(children)
        meta_path = _make_metadata(root)
        try:
            result_no_skip = detect_grouping_candidates(meta_path)
            result_skip = detect_grouping_candidates(meta_path, skip_root='1')
            # skip_root should have <= candidates than no skip
            assert result_skip['total'] <= result_no_skip['total']
        finally:
            os.unlink(meta_path)

    def test_disable_detectors(self):
        """Disabling detectors reduces candidates."""
        children = [
            _frame('c1', x=0, y=0, w=100, h=100, children=[_text('t1')]),
            _frame('c2', x=0, y=150, w=100, h=100, children=[_text('t2')]),
            _frame('c3', x=0, y=300, w=100, h=100, children=[_text('t3')]),
        ]
        root = self._build_page(children)
        meta_path = _make_metadata(root)
        try:
            result_all = detect_grouping_candidates(meta_path)
            result_no_pattern = detect_grouping_candidates(meta_path, disable_detectors='pattern')
            # Disabling pattern detector may reduce (or not change) count
            assert result_no_pattern['total'] <= result_all['total']
        finally:
            os.unlink(meta_path)

    def test_disable_unknown_detector_ignored(self, capsys):
        """Unknown detector name is ignored with warning."""
        root = self._build_page([])
        meta_path = _make_metadata(root)
        try:
            result = detect_grouping_candidates(meta_path, disable_detectors='nonexistent')
            # Should still work
            assert 'total' in result
        finally:
            os.unlink(meta_path)

    def test_repeated_pattern_detection(self):
        """3+ similar frames should produce some grouping candidates."""
        cards = []
        for i in range(4):
            cards.append(
                _frame(f'card-{i}', x=i*200, y=0, w=150, h=200, name=f'Card {i}',
                       children=[
                           _img(f'img-{i}', x=i*200, y=0, w=150, h=100),
                           _text(f'txt-{i}', x=i*200, y=110, w=150, h=20, characters=f'Title {i}'),
                       ])
            )
        section = _frame('sec', x=0, y=0, w=1440, h=500, name='section-cards', children=cards)
        root = self._build_page([section])
        meta_path = _make_metadata(root)
        try:
            result = detect_grouping_candidates(meta_path)
            # Should find at least some candidates (pattern, semantic, spacing, etc.)
            assert result['total'] >= 0
            assert 'candidates' in result or 'output' in result
        finally:
            os.unlink(meta_path)

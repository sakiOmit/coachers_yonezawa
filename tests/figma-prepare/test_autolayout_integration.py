"""Tests for autolayout integration functions (tree walking and main entry point).

Covers:
  - walk_and_infer
  - run_autolayout_inference
"""

import json
import os

import pytest

from figma_utils.autolayout import (
    walk_and_infer,
    run_autolayout_inference,
)

from autolayout_helpers import _node


# ===========================================================================
# walk_and_infer
# ===========================================================================

class TestWalkAndInfer:
    """Tests for recursive tree walking with layout inference."""

    def test_single_frame_with_children(self):
        root = _node('root', 'FRAME', 0, 0, 400, 100, children=[
            _node('a', 'FRAME', 20, 20, 100, 60),
            _node('b', 'FRAME', 140, 20, 100, 60),
            _node('c', 'FRAME', 260, 20, 100, 60),
        ])
        results = walk_and_infer(root)
        assert len(results) >= 1
        assert results[0]['node_name'] == 'root'
        assert results[0]['source'] == 'inferred'
        assert results[0]['applicable'] is True

    def test_nested_frames(self):
        """Both parent and child frames with 2+ children get inferred."""
        inner = _node('inner', 'FRAME', 0, 0, 200, 200, children=[
            _node('c1', 'FRAME', 10, 10, 80, 80),
            _node('c2', 'FRAME', 10, 100, 80, 80),
        ])
        root = _node('outer', 'FRAME', 0, 0, 500, 300, children=[
            inner,
            _node('sibling', 'FRAME', 220, 0, 200, 200),
        ])
        results = walk_and_infer(root)
        names = [r['node_name'] for r in results]
        assert 'outer' in names
        assert 'inner' in names

    def test_hidden_children_excluded(self):
        """Hidden children don't count toward the 2-child minimum."""
        root = _node('root', 'FRAME', 0, 0, 400, 100, children=[
            _node('visible', 'FRAME', 20, 20, 100, 60),
            _node('hidden', 'FRAME', 200, 20, 100, 60, visible=False),
        ])
        results = walk_and_infer(root)
        # root has only 1 visible child => not eligible for layout inference
        root_results = [r for r in results if r['node_name'] == 'root']
        assert len(root_results) == 0

    def test_enriched_layout_mode(self):
        """Nodes with layoutMode use enriched data, source='exact'."""
        root = _node('auto-layout', 'FRAME', 0, 0, 400, 100, children=[
            _node('a', 'FRAME', 0, 0, 100, 100),
            _node('b', 'FRAME', 120, 0, 100, 100),
        ], layoutMode='HORIZONTAL', itemSpacing=20)
        results = walk_and_infer(root)
        assert len(results) >= 1
        assert results[0]['source'] == 'exact'
        assert results[0]['layout']['confidence'] == 'exact'

    def test_instance_not_applicable(self):
        """INSTANCE nodes are flagged as applicable=False."""
        root = _node('inst', 'INSTANCE', 0, 0, 400, 100, children=[
            _node('a', 'FRAME', 20, 20, 100, 60),
            _node('b', 'FRAME', 200, 20, 100, 60),
        ])
        results = walk_and_infer(root)
        assert len(results) >= 1
        assert results[0]['applicable'] is False

    def test_component_not_applicable(self):
        """COMPONENT nodes are flagged as applicable=False."""
        root = _node('comp', 'COMPONENT', 0, 0, 400, 100, children=[
            _node('a', 'FRAME', 20, 20, 100, 60),
            _node('b', 'FRAME', 200, 20, 100, 60),
        ])
        results = walk_and_infer(root)
        assert len(results) >= 1
        assert results[0]['applicable'] is False

    def test_section_type_eligible(self):
        """SECTION type nodes should also be eligible."""
        root = _node('sec', 'SECTION', 0, 0, 400, 100, children=[
            _node('a', 'FRAME', 20, 20, 100, 60),
            _node('b', 'FRAME', 200, 20, 100, 60),
        ])
        results = walk_and_infer(root)
        assert len(results) >= 1
        assert results[0]['node_type'] == 'SECTION'

    def test_text_node_ignored(self):
        """TEXT nodes should not be inferred."""
        root = _node('text', 'TEXT', 0, 0, 100, 20)
        results = walk_and_infer(root)
        assert len(results) == 0

    # --- Edge case: empty tree ---

    def test_empty_node_no_children(self):
        root = _node('empty', 'FRAME', 0, 0, 400, 100)
        results = walk_and_infer(root)
        assert len(results) == 0

    def test_results_accumulation(self):
        """Passing an existing results list should accumulate."""
        root = _node('root', 'FRAME', 0, 0, 400, 100, children=[
            _node('a', 'FRAME', 20, 20, 100, 60),
            _node('b', 'FRAME', 200, 20, 100, 60),
        ])
        existing = [{'node_id': 'pre-existing', 'node_name': 'old'}]
        results = walk_and_infer(root, results=existing)
        assert len(results) >= 2
        assert results[0]['node_name'] == 'old'


# ===========================================================================
# run_autolayout_inference
# ===========================================================================

class TestRunAutolayoutInference:
    """Tests for the main entry point."""

    @pytest.fixture
    def metadata_file(self, tmp_path):
        """Create a temporary metadata JSON file."""
        data = {
            'document': _node('page', 'FRAME', 0, 0, 1440, 900, children=[
                _node('section', 'FRAME', 0, 0, 1440, 400, children=[
                    _node('card-1', 'FRAME', 20, 20, 300, 360),
                    _node('card-2', 'FRAME', 340, 20, 300, 360),
                    _node('card-3', 'FRAME', 660, 20, 300, 360),
                ]),
            ])
        }
        f = tmp_path / 'metadata.json'
        f.write_text(json.dumps(data), encoding='utf-8')
        return str(f)

    def test_returns_json_without_output(self, metadata_file):
        result_str = run_autolayout_inference(metadata_file)
        result = json.loads(result_str)
        assert 'total' in result
        assert 'frames' in result
        assert result['status'] == 'dry-run'
        assert result['total'] >= 1

    def test_writes_yaml_with_output(self, metadata_file, tmp_path):
        output_file = str(tmp_path / 'autolayout.yaml')
        result_str = run_autolayout_inference(metadata_file, output_file=output_file)
        result = json.loads(result_str)
        assert result['status'] == 'dry-run'
        assert result['output'] == output_file
        assert os.path.exists(output_file)

        with open(output_file, 'r') as f:
            content = f.read()
        assert 'Figma Auto Layout Plan' in content
        assert 'direction:' in content
        assert 'gap:' in content
        assert 'source:' in content

    def test_empty_page_returns_zero(self, tmp_path):
        """Page with no eligible frames returns total=0."""
        data = {'document': _node('page', 'FRAME', 0, 0, 1440, 900)}
        f = tmp_path / 'empty.json'
        f.write_text(json.dumps(data), encoding='utf-8')
        result_str = run_autolayout_inference(str(f))
        result = json.loads(result_str)
        assert result['total'] == 0

    def test_instance_flagged_in_yaml(self, tmp_path):
        """INSTANCE nodes should have applicable: false in YAML output."""
        data = {
            'document': _node('page', 'FRAME', 0, 0, 1440, 900, children=[
                _node('inst', 'INSTANCE', 0, 0, 400, 100, children=[
                    _node('a', 'FRAME', 20, 20, 100, 60),
                    _node('b', 'FRAME', 200, 20, 100, 60),
                ]),
            ])
        }
        f = tmp_path / 'instance.json'
        f.write_text(json.dumps(data), encoding='utf-8')
        output_file = str(tmp_path / 'out.yaml')
        run_autolayout_inference(str(f), output_file=output_file)
        with open(output_file, 'r') as fh:
            content = fh.read()
        assert 'applicable: false' in content

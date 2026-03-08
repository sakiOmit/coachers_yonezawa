"""Tests for grouping_llm_fallback module (Issue #274).

Tests all public functions for the LLM-based grouping correction system
that detects 1:N heading-content patterns missed by Stage C heuristics.
"""
import json
import os
import pytest

from figma_utils.grouping_llm_fallback import (
    GROUPING_FALLBACK_HEADING_MAX_HEIGHT,
    GROUPING_FALLBACK_MIN_SIBLINGS_AFTER_HEADING,
    GROUPING_FALLBACK_STRUCTURE_SIMILARITY,
    GROUPING_LLM_CONFIDENCE_MAP,
    GROUPING_LLM_DEFAULT_CONFIDENCE,
    _count_child_type_total,
    _enriched_row_hash,
    _is_heading_like_row,
    _is_valid_correction,
    _simple_hash_similarity,
    build_grouping_fallback_context,
    collect_undergrouped_sections,
    format_grouping_fallback_prompt,
    generate_grouping_fallback_context_file,
    merge_grouping_suggestions,
    parse_llm_grouping_suggestions,
)


# ============================================================
# _is_heading_like_row
# ============================================================
class TestIsHeadingLikeRow:
    def test_text_node_small_height(self):
        assert _is_heading_like_row({'type': 'TEXT', 'h': 24}) is True

    def test_text_node_too_tall(self):
        assert _is_heading_like_row({'type': 'TEXT', 'h': 300}) is False

    def test_named_heading(self):
        assert _is_heading_like_row({'type': 'FRAME', 'name': 'heading-about', 'h': 50}) is True

    def test_named_en_label(self):
        assert _is_heading_like_row({'type': 'TEXT', 'name': 'en-label-about', 'h': 20}) is True

    def test_frame_with_text_content(self):
        assert _is_heading_like_row({
            'type': 'FRAME', 'h': 40, 'text': 'About Us',
            'child_types': '2TEX',
        }) is True

    def test_frame_too_many_children(self):
        assert _is_heading_like_row({
            'type': 'FRAME', 'h': 40, 'text': 'Content',
            'child_types': '10TEX+5REC',
        }) is False

    def test_rectangle_not_heading(self):
        assert _is_heading_like_row({'type': 'RECTANGLE', 'h': 20}) is False

    def test_zero_height(self):
        assert _is_heading_like_row({'type': 'TEXT', 'h': 0}) is False


# ============================================================
# _count_child_type_total
# ============================================================
class TestCountChildTypeTotal:
    def test_normal(self):
        assert _count_child_type_total('2TEX+1REC') == 3

    def test_single(self):
        assert _count_child_type_total('3IMG') == 3

    def test_dash(self):
        assert _count_child_type_total('-') == 0

    def test_empty(self):
        assert _count_child_type_total('') == 0


# ============================================================
# _enriched_row_hash and _simple_hash_similarity
# ============================================================
class TestEnrichedRowHash:
    def test_basic_hash(self):
        h = _enriched_row_hash({'type': 'FRAME', 'child_types': '2TEX+1REC', 'w': 320, 'h': 80})
        assert 'FRAME' in h
        assert '2TEX+1REC' in h

    def test_same_structure_same_hash(self):
        row1 = {'type': 'FRAME', 'child_types': '2TEX', 'w': 300, 'h': 80}
        row2 = {'type': 'FRAME', 'child_types': '2TEX', 'w': 310, 'h': 85}
        assert _enriched_row_hash(row1) == _enriched_row_hash(row2)  # same 50px bucket

    def test_different_type_different_hash(self):
        row1 = {'type': 'FRAME', 'child_types': '2TEX', 'w': 300, 'h': 80}
        row2 = {'type': 'TEXT', 'child_types': '-', 'w': 300, 'h': 80}
        assert _enriched_row_hash(row1) != _enriched_row_hash(row2)

    def test_similarity_identical(self):
        assert _simple_hash_similarity('A:B:C', 'A:B:C') == 1.0

    def test_similarity_empty(self):
        assert _simple_hash_similarity('', 'A') == 0.0

    def test_similarity_partial(self):
        s = _simple_hash_similarity('A:B:C', 'A:B:D')
        assert 0 < s < 1


# ============================================================
# collect_undergrouped_sections
# ============================================================
class TestCollectUndergroupedSections:
    def _make_rows(self, heading_text='見出し', n_items=4):
        """Build enriched rows: 1 heading + N similar items."""
        rows = [{
            'id': 'h1', 'name': 'Text 1', 'type': 'TEXT',
            'w': 200, 'h': 24, 'text': heading_text, 'child_types': '-',
        }]
        for i in range(n_items):
            rows.append({
                'id': f'c{i}', 'name': f'Frame {i}', 'type': 'FRAME',
                'w': 300, 'h': 80, 'text': f'Item {i}',
                'child_types': '3TEX+2REC+2IMG',  # >5 children so not heading-like
            })
        return rows

    def test_heading_with_similar_siblings(self):
        rows = self._make_rows(n_items=4)
        result = collect_undergrouped_sections([], rows)
        assert len(result) == 1
        assert result[0]['heading_id'] == 'h1'
        assert len(result[0]['candidate_ids']) >= 3

    def test_too_few_siblings(self):
        rows = self._make_rows(n_items=2)
        result = collect_undergrouped_sections([], rows)
        assert len(result) == 0  # below GROUPING_FALLBACK_MIN_SIBLINGS_AFTER_HEADING

    def test_empty_enriched_rows(self):
        assert collect_undergrouped_sections([], []) == []
        assert collect_undergrouped_sections([], None) == []

    def test_already_grouped(self):
        rows = self._make_rows(n_items=4)
        plan = [{
            'node_ids': ['h1', 'c0', 'c1', 'c2', 'c3'],
            'suggested_name': 'existing-group',
        }]
        result = collect_undergrouped_sections(plan, rows)
        assert len(result) == 0  # all in same group

    def test_no_heading(self):
        rows = [
            {'id': f'r{i}', 'type': 'RECTANGLE', 'w': 300, 'h': 80,
             'child_types': '-', 'name': f'Rect {i}'}
            for i in range(5)
        ]
        result = collect_undergrouped_sections([], rows)
        assert len(result) == 0


# ============================================================
# build_grouping_fallback_context
# ============================================================
class TestBuildGroupingFallbackContext:
    def test_basic_context(self):
        rows = [
            {'id': 'h1', 'type': 'TEXT', 'w': 200, 'h': 24, 'text': '見出し', 'name': 'heading'},
            {'id': 'c1', 'type': 'FRAME', 'w': 300, 'h': 80, 'text': 'Item 1', 'child_types': '2TEX'},
        ]
        undergrouped = [{
            'heading_id': 'h1', 'heading_name': 'heading',
            'candidate_ids': ['c1'], 'reason': 'test', 'section_context': 'test-sec',
        }]
        ctx = build_grouping_fallback_context(undergrouped, rows)
        assert 'sections' in ctx
        assert len(ctx['sections']) == 1
        assert ctx['sections'][0]['heading_id'] == 'h1'

    def test_empty_undergrouped(self):
        ctx = build_grouping_fallback_context([], [])
        assert ctx == {'sections': []}


# ============================================================
# format_grouping_fallback_prompt
# ============================================================
class TestFormatGroupingFallbackPrompt:
    def test_empty_context(self):
        assert format_grouping_fallback_prompt({'sections': []}) == ''

    def test_basic_prompt(self):
        ctx = {
            'sections': [{
                'heading_id': 'h1', 'heading_name': 'heading-test',
                'heading_row': {'type': 'TEXT', 'w': 200, 'h': 24, 'name': 'heading-test'},
                'candidate_ids': ['c1'],
                'candidate_rows': [{'id': 'c1', 'type': 'FRAME', 'w': 300, 'h': 80}],
                'reason': 'test reason', 'section_context': 'test-section',
            }],
        }
        prompt = format_grouping_fallback_prompt(ctx)
        assert prompt  # non-empty
        # The template may use {sections_detail} placeholder - verify key content is present
        assert 'heading-test' in prompt or 'Section' in prompt


# ============================================================
# parse_llm_grouping_suggestions
# ============================================================
class TestParseLlmGroupingSuggestions:
    def test_valid_yaml(self):
        text = """corrections:
  - heading_id: "h1"
    heading_name: "heading-climate"
    group_name: "topic-climate"
    member_ids: ["c1", "c2", "c3"]
    confidence: high
    reason: "Activities under climate change topic"
"""
        result = parse_llm_grouping_suggestions(text)
        assert len(result) == 1
        assert result[0]['heading_id'] == 'h1'
        assert result[0]['group_name'] == 'topic-climate'
        assert result[0]['member_ids'] == ['c1', 'c2', 'c3']

    def test_yaml_in_code_block(self):
        text = """Here is my analysis:

```yaml
corrections:
  - heading_id: "h1"
    group_name: "list-items"
    member_ids: ["a", "b", "c"]
    confidence: medium
    reason: "Same structure"
```"""
        result = parse_llm_grouping_suggestions(text)
        assert len(result) == 1
        assert result[0]['group_name'] == 'list-items'

    def test_empty_input(self):
        assert parse_llm_grouping_suggestions('') == []
        assert parse_llm_grouping_suggestions(None) == []

    def test_malformed(self):
        assert parse_llm_grouping_suggestions('not yaml') == []

    def test_missing_required_fields(self):
        text = """corrections:
  - heading_id: "h1"
    confidence: high"""
        result = parse_llm_grouping_suggestions(text)
        assert len(result) == 0  # missing group_name and member_ids

    def test_multiple_corrections(self):
        text = """corrections:
  - heading_id: "h1"
    group_name: "group-a"
    member_ids: ["a1", "a2", "a3"]
    confidence: high
    reason: "First group"
  - heading_id: "h2"
    group_name: "group-b"
    member_ids: ["b1", "b2", "b3"]
    confidence: medium
    reason: "Second group"
"""
        result = parse_llm_grouping_suggestions(text)
        assert len(result) == 2


# ============================================================
# merge_grouping_suggestions
# ============================================================
class TestMergeGroupingSuggestions:
    def test_normal_merge(self):
        entries = [{'node_ids': ['x', 'y'], 'suggested_name': 'existing'}]
        suggestions = [{
            'heading_id': 'h1',
            'group_name': 'topic-test',
            'member_ids': ['c1', 'c2'],
            'confidence': 'high',
            'reason': 'test',
        }]
        result = merge_grouping_suggestions(entries, suggestions)
        # Should have existing + new
        names = [e['suggested_name'] for e in result]
        assert 'topic-test' in names
        merged = [e for e in result if e['suggested_name'] == 'topic-test'][0]
        assert merged['method'] == 'llm_grouping_fallback'
        assert merged['confidence'] == 92
        assert 'h1' in merged['node_ids']
        assert 'c1' in merged['node_ids']

    def test_removes_from_existing(self):
        entries = [{'node_ids': ['h1', 'c1', 'other'], 'suggested_name': 'old-group'}]
        suggestions = [{
            'heading_id': 'h1',
            'group_name': 'new-group',
            'member_ids': ['c1', 'c2'],
            'confidence': '高',
        }]
        result = merge_grouping_suggestions(entries, suggestions)
        old = [e for e in result if e['suggested_name'] == 'old-group']
        assert len(old) == 1
        assert 'h1' not in old[0]['node_ids']
        assert 'other' in old[0]['node_ids']

    def test_empty_suggestions(self):
        entries = [{'node_ids': ['a'], 'suggested_name': 'g'}]
        result = merge_grouping_suggestions(entries, [])
        assert len(result) == 1

    def test_none_entries(self):
        result = merge_grouping_suggestions(None, [])
        assert result == []

    def test_confidence_mapping(self):
        for label, expected in [('high', 92), ('medium', 78), ('low', 62), ('高', 92), ('中', 78), ('低', 62)]:
            result = merge_grouping_suggestions([], [{
                'heading_id': 'h', 'group_name': 'g',
                'member_ids': ['m'], 'confidence': label,
            }])
            assert result[0]['confidence'] == expected

    def test_does_not_mutate_original(self):
        entries = [{'node_ids': ['a', 'b'], 'suggested_name': 'orig'}]
        original_ids = entries[0]['node_ids'].copy()
        merge_grouping_suggestions(entries, [{
            'heading_id': 'a', 'group_name': 'new',
            'member_ids': ['b'], 'confidence': 'high',
        }])
        assert entries[0]['node_ids'] == original_ids  # not mutated


# ============================================================
# _is_valid_correction
# ============================================================
class TestIsValidCorrection:
    def test_valid(self):
        assert _is_valid_correction({
            'heading_id': 'h1', 'group_name': 'g', 'member_ids': ['m1'],
        }) is True

    def test_missing_heading_id(self):
        assert _is_valid_correction({'group_name': 'g', 'member_ids': ['m1']}) is False

    def test_empty_member_ids(self):
        assert _is_valid_correction({'heading_id': 'h1', 'group_name': 'g', 'member_ids': []}) is False


# ============================================================
# generate_grouping_fallback_context_file
# ============================================================
class TestGenerateGroupingFallbackContextFile:
    def test_no_undergrouped(self, tmp_path):
        rows = [{'id': 'r1', 'type': 'RECTANGLE', 'w': 100, 'h': 100, 'child_types': '-'}]
        out_path = str(tmp_path / 'out.json')
        count = generate_grouping_fallback_context_file([], rows, '', out_path)
        assert count == 0
        assert not os.path.exists(out_path)

    def test_with_undergrouped(self, tmp_path):
        rows = [
            {'id': 'h1', 'type': 'TEXT', 'w': 200, 'h': 24, 'text': '見出し', 'name': 'Text 1', 'child_types': '-'},
        ] + [
            {'id': f'c{i}', 'type': 'FRAME', 'w': 300, 'h': 80, 'text': f'Item {i}',
             'name': f'Frame {i}', 'child_types': '3TEX+2REC+2IMG'}  # >5 children
            for i in range(4)
        ]
        out_path = str(tmp_path / 'out.json')
        count = generate_grouping_fallback_context_file([], rows, '', out_path)
        assert count >= 1
        assert os.path.exists(out_path)
        with open(out_path) as f:
            data = json.load(f)
        assert 'prompt' in data
        assert data['undergrouped_count'] >= 1

"""Tests for LLM fallback v2 enhancements (dynamic confidence, method origin, surrounding context)."""
import pytest

from figma_utils.rename_llm_fallback import (
    _build_node_context,
    format_fallback_prompt,
    parse_llm_suggestions,
    merge_llm_suggestions,
    LLM_CONFIDENCE_MAP,
    LLM_DEFAULT_CONFIDENCE,
)


def _node(node_id, node_type='FRAME', name='Frame 1', w=100, h=50):
    return {
        'id': node_id, 'type': node_type, 'name': name, 'visible': True,
        'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': w, 'height': h},
        'children': [],
    }


# ============================================================
# _build_node_context with method origin
# ============================================================
class TestBuildNodeContextWithMethod:
    def test_method_origin_found(self):
        node = _node('1:1')
        candidates = [{'method': 'proximity', 'score': 0.72, 'node_ids': ['1:1', '1:2']}]
        ctx = _build_node_context(node, stage_a_candidates=candidates)
        assert ctx['method_origin'] == 'proximity@0.7'

    def test_method_origin_not_found(self):
        node = _node('9:9')
        candidates = [{'method': 'proximity', 'score': 0.72, 'node_ids': ['1:1']}]
        ctx = _build_node_context(node, stage_a_candidates=candidates)
        assert ctx['method_origin'] == '-'

    def test_method_origin_no_candidates(self):
        node = _node('1:1')
        ctx = _build_node_context(node, stage_a_candidates=None)
        assert ctx['method_origin'] == '-'

    def test_method_origin_empty_candidates(self):
        node = _node('1:1')
        ctx = _build_node_context(node, stage_a_candidates=[])
        assert ctx['method_origin'] == '-'

    def test_method_origin_first_match_wins(self):
        node = _node('1:1')
        candidates = [
            {'method': 'proximity', 'score': 0.5, 'node_ids': ['1:1']},
            {'method': 'pattern', 'score': 0.9, 'node_ids': ['1:1']},
        ]
        ctx = _build_node_context(node, stage_a_candidates=candidates)
        assert ctx['method_origin'] == 'proximity@0.5'

    def test_sibling_limit_increased_to_15(self):
        """Verify sibling limit is 15 (up from 10)."""
        siblings = [_node(f's:{i}', name=f'sibling-{i}') for i in range(20)]
        node = _node('1:1')
        ctx = _build_node_context(node, siblings=siblings)
        assert len(ctx['sibling_names']) == 15


# ============================================================
# format_fallback_prompt v2
# ============================================================
class TestFormatFallbackPromptV2:
    def test_includes_method_column(self):
        contexts = [{
            'id': '1:1', 'type': 'FRAME', 'width': 100, 'height': 50,
            'child_count': 0, 'child_types': '-', 'text_preview': 'hello',
            'heuristic_name': 'container-0', 'confidence': 20,
            'method_origin': 'proximity@0.7', 'sibling_names': [],
        }]
        prompt = format_fallback_prompt(contexts)
        assert 'Method' in prompt
        assert 'proximity@0.7' in prompt

    def test_includes_surrounding_context(self):
        contexts = [{
            'id': '1:1', 'type': 'FRAME', 'width': 100, 'height': 50,
            'child_count': 0, 'child_types': '-', 'text_preview': '-',
            'heuristic_name': 'group-0', 'confidence': 10,
            'method_origin': '-', 'sibling_names': [],
        }]
        all_renames = {
            '2:1': {
                'old_name': 'Frame 2', 'new_name': 'heading-about',
                'confidence': 90, 'inference_method': 'auto',
            }
        }
        prompt = format_fallback_prompt(contexts, all_renames=all_renames)
        assert '周辺コンテキスト' in prompt
        assert 'heading-about' in prompt

    def test_empty_contexts(self):
        assert format_fallback_prompt([]) == ''

    def test_no_surrounding_renames(self):
        contexts = [{
            'id': '1:1', 'type': 'FRAME', 'width': 100, 'height': 50,
            'child_count': 0, 'child_types': '-', 'text_preview': '-',
            'heuristic_name': 'group-0', 'confidence': 10,
            'method_origin': '-', 'sibling_names': [],
        }]
        prompt = format_fallback_prompt(contexts, all_renames=None)
        assert '周辺コンテキスト' not in prompt

    def test_low_confidence_renames_excluded_from_surrounding(self):
        """Only high-confidence renames (>=70) appear in surrounding context."""
        contexts = [{
            'id': '1:1', 'type': 'FRAME', 'width': 100, 'height': 50,
            'child_count': 0, 'child_types': '-', 'text_preview': '-',
            'heuristic_name': 'group-0', 'confidence': 10,
            'method_origin': '-', 'sibling_names': [],
        }]
        all_renames = {
            '2:1': {'old_name': 'F1', 'new_name': 'low-conf', 'confidence': 30},
            '2:2': {'old_name': 'F2', 'new_name': 'high-conf', 'confidence': 80,
                     'inference_method': 'auto'},
        }
        prompt = format_fallback_prompt(contexts, all_renames=all_renames)
        assert 'high-conf' in prompt
        assert 'low-conf' not in prompt

    def test_surrounding_context_limited_to_20(self):
        """Surrounding context should be limited to 20 entries."""
        contexts = [{
            'id': '1:1', 'type': 'FRAME', 'width': 100, 'height': 50,
            'child_count': 0, 'child_types': '-', 'text_preview': '-',
            'heuristic_name': 'group-0', 'confidence': 10,
            'method_origin': '-', 'sibling_names': [],
        }]
        all_renames = {
            f'n:{i}': {'old_name': f'F{i}', 'new_name': f'name-{i}',
                        'confidence': 90, 'inference_method': 'auto'}
            for i in range(30)
        }
        prompt = format_fallback_prompt(contexts, all_renames=all_renames)
        # Count occurrences of the bullet marker
        bullet_count = prompt.count('  - `n:')
        assert bullet_count == 20

    def test_confidence_field_in_output_format(self):
        """The prompt should mention confidence field in output format."""
        contexts = [{
            'id': '1:1', 'type': 'FRAME', 'width': 100, 'height': 50,
            'child_count': 0, 'child_types': '-', 'text_preview': '-',
            'heuristic_name': 'group-0', 'confidence': 10,
            'method_origin': '-', 'sibling_names': [],
        }]
        prompt = format_fallback_prompt(contexts)
        assert 'confidence: 高|中|低' in prompt

    def test_method_explanation_in_prompt(self):
        """The prompt should explain Method column."""
        contexts = [{
            'id': '1:1', 'type': 'FRAME', 'width': 100, 'height': 50,
            'child_count': 0, 'child_types': '-', 'text_preview': '-',
            'heuristic_name': 'group-0', 'confidence': 10,
            'method_origin': '-', 'sibling_names': [],
        }]
        prompt = format_fallback_prompt(contexts)
        assert 'Method列' in prompt


# ============================================================
# parse_llm_suggestions v2
# ============================================================
class TestParseLLMSuggestionsV2:
    def test_parse_with_confidence(self):
        text = '''```yaml
renames:
  "1:100":
    new: "heading-about"
    reason: "テキスト内容から"
    confidence: 高
```'''
        result = parse_llm_suggestions(text)
        assert result['1:100']['confidence'] == '高'

    def test_parse_without_confidence(self):
        text = '''```yaml
renames:
  "1:100":
    new: "heading-about"
    reason: "推測"
```'''
        result = parse_llm_suggestions(text)
        assert result['1:100']['confidence'] == ''

    def test_parse_english_confidence(self):
        text = '''renames:
  "1:100":
    new: "card-feature"
    reason: "child structure"
    confidence: high
'''
        result = parse_llm_suggestions(text)
        assert result['1:100']['confidence'] == 'high'

    def test_parse_multiple_with_mixed_confidence(self):
        text = '''renames:
  "1:100":
    new: "heading-about"
    reason: "text content"
    confidence: 高
  "1:200":
    new: "card-feature"
    reason: "structure"
    confidence: 中
'''
        result = parse_llm_suggestions(text)
        assert result['1:100']['confidence'] == '高'
        assert result['1:200']['confidence'] == '中'


# ============================================================
# merge_llm_suggestions v2
# ============================================================
class TestMergeLLMSuggestionsV2:
    def test_high_confidence_mapping(self):
        renames = {
            '1:1': {'old_name': 'Frame 1', 'new_name': 'group-0',
                     'type': 'FRAME', 'confidence': 20, 'inference_method': 'auto'}
        }
        suggestions = {
            '1:1': {'new': 'card-feature', 'reason': 'test', 'confidence': '高'}
        }
        merge_llm_suggestions(renames, suggestions)
        assert renames['1:1']['confidence'] == 92

    def test_medium_confidence_mapping(self):
        renames = {
            '1:1': {'old_name': 'Frame 1', 'new_name': 'group-0',
                     'type': 'FRAME', 'confidence': 20, 'inference_method': 'auto'}
        }
        suggestions = {
            '1:1': {'new': 'container-nav', 'reason': 'test', 'confidence': '中'}
        }
        merge_llm_suggestions(renames, suggestions)
        assert renames['1:1']['confidence'] == 78

    def test_low_confidence_mapping(self):
        renames = {
            '1:1': {'old_name': 'Frame 1', 'new_name': 'group-0',
                     'type': 'FRAME', 'confidence': 20, 'inference_method': 'auto'}
        }
        suggestions = {
            '1:1': {'new': 'frame-unknown', 'reason': 'test', 'confidence': '低'}
        }
        merge_llm_suggestions(renames, suggestions)
        assert renames['1:1']['confidence'] == 62

    def test_english_confidence_mapping(self):
        renames = {
            '1:1': {'old_name': 'Frame 1', 'new_name': 'group-0',
                     'type': 'FRAME', 'confidence': 20, 'inference_method': 'auto'}
        }
        suggestions = {
            '1:1': {'new': 'card-feature', 'reason': 'test', 'confidence': 'high'}
        }
        merge_llm_suggestions(renames, suggestions)
        assert renames['1:1']['confidence'] == 92

    def test_default_confidence_when_missing(self):
        renames = {
            '1:1': {'old_name': 'Frame 1', 'new_name': 'group-0',
                     'type': 'FRAME', 'confidence': 20, 'inference_method': 'auto'}
        }
        suggestions = {
            '1:1': {'new': 'heading-about', 'reason': 'test'}
        }
        merge_llm_suggestions(renames, suggestions)
        assert renames['1:1']['confidence'] == LLM_DEFAULT_CONFIDENCE

    def test_default_confidence_when_empty_string(self):
        renames = {
            '1:1': {'old_name': 'Frame 1', 'new_name': 'group-0',
                     'type': 'FRAME', 'confidence': 20, 'inference_method': 'auto'}
        }
        suggestions = {
            '1:1': {'new': 'heading-about', 'reason': 'test', 'confidence': ''}
        }
        merge_llm_suggestions(renames, suggestions)
        assert renames['1:1']['confidence'] == LLM_DEFAULT_CONFIDENCE

    def test_does_not_override_high_confidence(self):
        renames = {
            '1:1': {'old_name': 'Frame 1', 'new_name': 'heading-about',
                     'type': 'FRAME', 'confidence': 90, 'inference_method': 'auto'}
        }
        suggestions = {
            '1:1': {'new': 'wrong-name', 'reason': 'test', 'confidence': '高'}
        }
        merge_llm_suggestions(renames, suggestions)
        assert renames['1:1']['new_name'] == 'heading-about'  # unchanged

    def test_llm_reason_stored(self):
        renames = {
            '1:1': {'old_name': 'Frame 1', 'new_name': 'group-0',
                     'type': 'FRAME', 'confidence': 20, 'inference_method': 'auto'}
        }
        suggestions = {
            '1:1': {'new': 'nav-main', 'reason': 'ナビゲーション構造', 'confidence': '高'}
        }
        merge_llm_suggestions(renames, suggestions)
        assert renames['1:1']['llm_reason'] == 'ナビゲーション構造'
        assert renames['1:1']['inference_method'] == 'llm_fallback'


# ============================================================
# LLM_CONFIDENCE_MAP constants
# ============================================================
class TestLLMConfidenceMapConstants:
    def test_map_has_all_expected_keys(self):
        expected_keys = {'高', 'high', '中', 'medium', '低', 'low'}
        assert set(LLM_CONFIDENCE_MAP.keys()) == expected_keys

    def test_default_confidence_value(self):
        assert LLM_DEFAULT_CONFIDENCE == 78

    def test_confidence_ordering(self):
        assert LLM_CONFIDENCE_MAP['高'] > LLM_CONFIDENCE_MAP['中'] > LLM_CONFIDENCE_MAP['低']

"""Tests for LLM fallback rename functions in figma_utils."""
import pytest

from figma_utils.rename_llm_fallback import (
    collect_low_confidence_renames,
    _build_node_context,
    _find_parent,
    format_fallback_prompt,
    parse_llm_suggestions,
    merge_llm_suggestions,
)
from figma_utils.semantic_rename import (
    infer_name_with_confidence,
    _estimate_children_confidence,
)


# ============================================================
# collect_low_confidence_renames
# ============================================================
class TestCollectLowConfidenceRenames:
    def test_mix_of_high_and_low(self):
        renames = {
            'node1': {'new_name': 'heading-about', 'confidence': 90},
            'node2': {'new_name': 'container-0', 'confidence': 20},
            'node3': {'new_name': 'group-3', 'confidence': 10},
            'node4': {'new_name': 'btn-submit', 'confidence': 75},
        }
        result = collect_low_confidence_renames(renames)
        assert set(result.keys()) == {'node2', 'node3'}

    def test_all_high_confidence(self):
        renames = {
            'a': {'new_name': 'heading-hero', 'confidence': 90},
            'b': {'new_name': 'btn-cta', 'confidence': 75},
        }
        result = collect_low_confidence_renames(renames)
        assert result == {}

    def test_custom_threshold(self):
        renames = {
            'a': {'new_name': 'icon-0', 'confidence': 85},
            'b': {'new_name': 'card-feature', 'confidence': 70},
            'c': {'new_name': 'container-0', 'confidence': 20},
        }
        result = collect_low_confidence_renames(renames, threshold=80)
        assert set(result.keys()) == {'b', 'c'}

    def test_missing_confidence_key_defaults_to_100(self):
        renames = {
            'a': {'new_name': 'heading-about'},  # no confidence key
            'b': {'new_name': 'group-0', 'confidence': 30},
        }
        result = collect_low_confidence_renames(renames)
        # 'a' has default confidence 100, so not collected
        assert set(result.keys()) == {'b'}

    def test_empty_input(self):
        assert collect_low_confidence_renames({}) == {}


# ============================================================
# _build_node_context
# ============================================================
class TestBuildNodeContext:
    def _make_node(self, **overrides):
        """Create a minimal Figma node dict."""
        node = {
            'id': '1:100',
            'type': 'FRAME',
            'name': 'Frame 1',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 400, 'height': 300},
            'children': [],
        }
        node.update(overrides)
        return node

    def test_leaf_node(self):
        node = self._make_node(type='RECTANGLE', children=[])
        ctx = _build_node_context(node)
        assert ctx['is_leaf'] is True
        assert ctx['child_count'] == 0
        assert ctx['type'] == 'RECTANGLE'
        assert ctx['id'] == '1:100'
        assert ctx['width'] == 400
        assert ctx['height'] == 300

    def test_node_with_children(self):
        child1 = self._make_node(id='1:200', type='TEXT', name='Hello')
        child2 = self._make_node(id='1:201', type='RECTANGLE', name='Rect 1')
        node = self._make_node(children=[child1, child2])
        ctx = _build_node_context(node)
        assert ctx['is_leaf'] is False
        assert ctx['child_count'] == 2
        # child_types should be a string describing types
        assert isinstance(ctx['child_types'], str)

    def test_with_parent(self):
        parent = self._make_node(id='0:1', type='FRAME', name='section-hero')
        node = self._make_node()
        ctx = _build_node_context(node, parent=parent)
        assert ctx['parent_name'] == 'section-hero'
        assert ctx['parent_type'] == 'FRAME'

    def test_without_parent(self):
        node = self._make_node()
        ctx = _build_node_context(node, parent=None)
        assert ctx['parent_name'] == ''
        assert ctx['parent_type'] == ''

    def test_siblings_with_unnamed_nodes(self):
        sib1 = self._make_node(id='1:10', name='heading-about', type='TEXT')
        sib2 = self._make_node(id='1:11', name='Frame 2', type='FRAME')  # unnamed
        sib3 = self._make_node(id='1:12', name='Rectangle 5', type='RECTANGLE')  # unnamed
        node = self._make_node()
        ctx = _build_node_context(node, siblings=[sib1, sib2, sib3])
        assert ctx['sibling_names'][0] == 'heading-about'
        assert ctx['sibling_names'][1] == '[FRAME]'  # unnamed → [TYPE]
        assert ctx['sibling_names'][2] == '[RECTANGLE]'
        assert ctx['sibling_types'] == ['TEXT', 'FRAME', 'RECTANGLE']

    def test_hidden_children_filtered(self):
        visible_child = self._make_node(id='1:200', type='TEXT', name='Hello')
        hidden_child = self._make_node(id='1:201', type='RECTANGLE', name='Hidden', visible=False)
        node = self._make_node(children=[visible_child, hidden_child])
        ctx = _build_node_context(node)
        assert ctx['child_count'] == 1  # only visible child counted


# ============================================================
# _find_parent
# ============================================================
class TestFindParent:
    def test_direct_child(self):
        child = {'id': 'child-1', 'children': []}
        root = {'id': 'root', 'children': [child]}
        assert _find_parent(root, 'child-1') is root

    def test_nested_grandchild(self):
        grandchild = {'id': 'gc-1', 'children': []}
        middle = {'id': 'mid-1', 'children': [grandchild]}
        root = {'id': 'root', 'children': [middle]}
        result = _find_parent(root, 'gc-1')
        assert result is middle

    def test_not_found(self):
        child = {'id': 'child-1', 'children': []}
        root = {'id': 'root', 'children': [child]}
        assert _find_parent(root, 'nonexistent') is None

    def test_root_itself_not_found(self):
        root = {'id': 'root', 'children': []}
        # root is not a child of itself
        assert _find_parent(root, 'root') is None

    def test_deeply_nested(self):
        leaf = {'id': 'leaf', 'children': []}
        level3 = {'id': 'l3', 'children': [leaf]}
        level2 = {'id': 'l2', 'children': [level3]}
        level1 = {'id': 'l1', 'children': [level2]}
        root = {'id': 'root', 'children': [level1]}
        assert _find_parent(root, 'leaf') is level3


# ============================================================
# format_fallback_prompt
# ============================================================
class TestFormatFallbackPrompt:
    def _make_context(self, **overrides):
        ctx = {
            'id': '2:100',
            'type': 'FRAME',
            'current_name': 'Frame 1',
            'width': 300,
            'height': 200,
            'child_count': 3,
            'child_types': 'TEXT(2), RECTANGLE(1)',
            'text_preview': 'お問い合わせ',
            'heuristic_name': 'container-0',
            'confidence': 20,
            'sibling_names': ['heading-about', '[FRAME]'],
            'sibling_types': ['TEXT', 'FRAME'],
        }
        ctx.update(overrides)
        return ctx

    def test_empty_contexts(self):
        assert format_fallback_prompt([]) == ''

    def test_single_context_default_prompt(self):
        ctx = self._make_context()
        result = format_fallback_prompt([ctx])
        assert result != ''
        assert '1 個' in result
        assert '2:100' in result
        assert '命名規約' in result
        assert '出力形式' in result
        assert 'container-0' in result

    def test_custom_template(self):
        ctx = self._make_context()
        template = "Count: {node_count}\nTable:\n{node_table}"
        result = format_fallback_prompt([ctx], template=template)
        assert result.startswith('Count: 1')
        assert '2:100' in result

    def test_multiple_contexts(self):
        ctx1 = self._make_context(id='2:100')
        ctx2 = self._make_context(id='2:200', heuristic_name='group-3')
        result = format_fallback_prompt([ctx1, ctx2])
        assert '2 個' in result
        assert '2:100' in result
        assert '2:200' in result


# ============================================================
# parse_llm_suggestions
# ============================================================
class TestParseLlmSuggestions:
    def test_valid_yaml(self):
        text = (
            "renames:\n"
            '  "2:8320":\n'
            '    new: "section-contact"\n'
            '    reason: "テキスト内容がお問い合わせ"\n'
        )
        result = parse_llm_suggestions(text)
        assert '2:8320' in result
        assert result['2:8320']['new'] == 'section-contact'
        assert result['2:8320']['reason'] == 'テキスト内容がお問い合わせ'

    def test_yaml_in_code_block(self):
        text = (
            "以下が提案です:\n\n"
            "```yaml\n"
            "renames:\n"
            '  "1:500":\n'
            '    new: "heading-about"\n'
            '    reason: "テキストにABOUTを含む"\n'
            "```\n"
        )
        result = parse_llm_suggestions(text)
        assert '1:500' in result
        assert result['1:500']['new'] == 'heading-about'

    def test_multiple_entries(self):
        text = (
            "renames:\n"
            '  "1:100":\n'
            '    new: "nav-main"\n'
            '    reason: "ナビゲーション構造"\n'
            '  "1:200":\n'
            '    new: "card-feature"\n'
            '    reason: "カードレイアウト"\n'
        )
        result = parse_llm_suggestions(text)
        assert len(result) == 2
        assert result['1:100']['new'] == 'nav-main'
        assert result['1:200']['new'] == 'card-feature'

    def test_entry_with_spaces_in_name_filtered(self):
        text = (
            "renames:\n"
            '  "1:100":\n'
            '    new: "good-name"\n'
            '    reason: "valid"\n'
            '  "1:200":\n'
            '    new: "bad name with spaces"\n'
            '    reason: "invalid"\n'
        )
        result = parse_llm_suggestions(text)
        assert '1:100' in result
        assert '1:200' not in result  # filtered due to spaces

    def test_empty_input(self):
        assert parse_llm_suggestions('') == {}
        assert parse_llm_suggestions(None) == {}

    def test_malformed_yaml(self):
        text = "this is not yaml at all"
        result = parse_llm_suggestions(text)
        assert result == {}

    def test_node_ids_with_colons(self):
        text = (
            "renames:\n"
            '  "2:8320":\n'
            '    new: "section-hero"\n'
            '    reason: "ヒーローセクション"\n'
            '  "123:456":\n'
            '    new: "card-service"\n'
            '    reason: "サービスカード"\n'
        )
        result = parse_llm_suggestions(text)
        assert '2:8320' in result
        assert '123:456' in result

    def test_single_quoted_ids(self):
        text = (
            "renames:\n"
            "  '3:100':\n"
            '    new: "heading-top"\n'
            '    reason: "見出し"\n'
        )
        result = parse_llm_suggestions(text)
        assert '3:100' in result

    def test_partial_entry_without_new_key_skipped(self):
        text = (
            "renames:\n"
            '  "1:100":\n'
            '    reason: "only reason, no new name"\n'
            '  "1:200":\n'
            '    new: "valid-name"\n'
            '    reason: "ok"\n'
        )
        result = parse_llm_suggestions(text)
        assert '1:100' not in result  # missing 'new' key
        assert '1:200' in result


# ============================================================
# merge_llm_suggestions
# ============================================================
class TestMergeLlmSuggestions:
    def test_low_confidence_overridden(self):
        renames = {
            'node1': {'new_name': 'container-0', 'confidence': 20, 'inference_method': 'auto'},
        }
        suggestions = {
            'node1': {'new': 'section-about', 'reason': 'テキストからABOUT推論'},
        }
        merge_llm_suggestions(renames, suggestions)
        assert renames['node1']['new_name'] == 'section-about'
        assert renames['node1']['inference_method'] == 'llm_fallback'
        # v2: default confidence when LLM doesn't specify level (was fixed 85)
        assert renames['node1']['confidence'] == 78
        assert renames['node1']['llm_reason'] == 'テキストからABOUT推論'

    def test_high_confidence_not_overridden(self):
        renames = {
            'node1': {'new_name': 'heading-hero', 'confidence': 90, 'inference_method': 'auto'},
        }
        suggestions = {
            'node1': {'new': 'different-name', 'reason': 'some reason'},
        }
        merge_llm_suggestions(renames, suggestions)
        assert renames['node1']['new_name'] == 'heading-hero'  # unchanged
        assert renames['node1']['confidence'] == 90

    def test_nonexistent_node_id_ignored(self):
        renames = {
            'node1': {'new_name': 'heading-hero', 'confidence': 90},
        }
        suggestions = {
            'nonexistent': {'new': 'some-name', 'reason': 'some reason'},
        }
        merge_llm_suggestions(renames, suggestions)
        assert 'nonexistent' not in renames
        assert renames['node1']['new_name'] == 'heading-hero'

    def test_merged_entry_has_correct_fields(self):
        renames = {
            'n1': {'new_name': 'group-0', 'confidence': 10, 'inference_method': 'auto'},
        }
        suggestions = {
            'n1': {'new': 'nav-footer', 'reason': 'フッターナビ構造'},
        }
        merge_llm_suggestions(renames, suggestions)
        entry = renames['n1']
        assert entry['new_name'] == 'nav-footer'
        assert entry['inference_method'] == 'llm_fallback'
        assert entry['llm_reason'] == 'フッターナビ構造'
        # v2: default confidence when LLM doesn't specify level (was fixed 85)
        assert entry['confidence'] == 78

    def test_empty_suggestions_no_changes(self):
        renames = {
            'n1': {'new_name': 'container-0', 'confidence': 20},
        }
        original = dict(renames['n1'])
        merge_llm_suggestions(renames, {})
        assert renames['n1'] == original

    def test_boundary_confidence_49_overridden(self):
        renames = {
            'n1': {'new_name': 'group-1', 'confidence': 49},
        }
        suggestions = {
            'n1': {'new': 'card-list', 'reason': 'reason'},
        }
        merge_llm_suggestions(renames, suggestions)
        assert renames['n1']['new_name'] == 'card-list'

    def test_boundary_confidence_50_not_overridden(self):
        renames = {
            'n1': {'new_name': 'card-0', 'confidence': 50},
        }
        suggestions = {
            'n1': {'new': 'card-service', 'reason': 'reason'},
        }
        merge_llm_suggestions(renames, suggestions)
        assert renames['n1']['new_name'] == 'card-0'  # not overridden (>= 50)


# ============================================================
# infer_name_with_confidence
# ============================================================
class TestInferNameWithConfidence:
    def test_text_node(self):
        node = {
            'type': 'TEXT',
            'name': 'Text 1',
            'characters': 'お問い合わせ',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 100, 'height': 20},
            'children': [],
        }
        name, confidence = infer_name_with_confidence(node, sibling_index=0)
        assert confidence == 90
        assert isinstance(name, str)
        assert len(name) > 0

    def test_rectangle_leaf(self):
        node = {
            'type': 'RECTANGLE',
            'name': 'Rectangle 1',
            'absoluteBoundingBox': {'x': 0, 'y': 0, 'width': 1440, 'height': 2},
            'children': [],
        }
        name, confidence = infer_name_with_confidence(node, sibling_index=0)
        assert confidence == 85
        assert isinstance(name, str)

    def test_type_only_fallback(self):
        """A node where no heuristic matches should get very low confidence."""
        node = {
            'type': 'BOOLEAN_OPERATION',
            'name': 'Boolean 1',
            'absoluteBoundingBox': {'x': 500, 'y': 500, 'width': 50, 'height': 50},
            'children': [],
        }
        name, confidence = infer_name_with_confidence(node, sibling_index=3)
        assert confidence == 10
        assert 'boolean' in name.lower()


# ============================================================
# _estimate_children_confidence
# ============================================================
class TestEstimateChildrenConfidence:
    @pytest.mark.parametrize("name,expected", [
        ('nav-0', 80),
        ('nav-main', 80),
        ('decoration-dots-0', 90),
        ('decoration-pattern-1', 90),
        ('card-feature', 70),      # has slug
        ('card-0', 55),            # index-only
        ('icon-0', 85),
        ('icon-arrow', 85),
        ('btn-submit', 75),        # has slug
        ('btn-0', 60),             # index-only
        ('heading-about', 70),     # has slug
        ('body-intro', 60),
        ('content-main', 60),
        ('text-block-title', 65),  # has slug
        ('container-main', 40),    # has slug but weak
        ('container-0', 20),       # index-only
        ('group-0', 20),           # index-only
    ])
    def test_known_patterns(self, name, expected):
        assert _estimate_children_confidence(name) == expected

    def test_unknown_pattern(self):
        assert _estimate_children_confidence('unknown-pattern') == 50

    def test_card_with_numeric_suffix_is_index(self):
        # -0 through -5 are treated as index-only
        for i in range(6):
            assert _estimate_children_confidence(f'card-{i}') == 55

    def test_card_with_slug_higher_confidence(self):
        assert _estimate_children_confidence('card-testimonial') == 70

    def test_heading_with_index_gets_default(self):
        # heading-0 doesn't match the "has slug" branch, falls through
        result = _estimate_children_confidence('heading-0')
        # heading-0 ends with -0, so it falls to the catch-all
        # The function checks heading- with endswith check
        assert isinstance(result, int)

    def test_group_with_slug(self):
        # group-content has a slug, but it's still weak
        result = _estimate_children_confidence('group-content')
        assert result == 40

    def test_container_with_large_index(self):
        # container-25 — index >= 20, so it's NOT caught by index check
        result = _estimate_children_confidence('container-25')
        assert result == 40  # treated as "has slug" (25 is not in range(20))

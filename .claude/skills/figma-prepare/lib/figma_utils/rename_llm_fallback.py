"""LLM fallback for Phase 3 semantic rename.

Generates enriched context for low-confidence renames, enabling Claude
to suggest better names based on node structure, siblings, and text content.

Issue: Nodes where heuristic inference produced low-confidence results
(e.g., ``container-0``, ``group-3``) are collected and formatted into
a prompt that Claude can use to propose better semantic names.

Usage in SKILL.md workflow:
  1. ``generate_rename_map()`` calls ``generate_fallback_context_file()``
  2. SKILL.md reads the fallback context JSON
  3. Claude suggests better names via ``format_fallback_prompt()``
  4. Suggestions are parsed via ``parse_llm_suggestions()``
  5. Merged back via ``merge_llm_suggestions()``
"""

import json
import re

from .constants import (
    LLM_CONFIDENCE_MAP,
    LLM_DEFAULT_CONFIDENCE,
    LLM_FALLBACK_CONFIDENCE_THRESHOLD,
    UNNAMED_RE,
)
from .enrichment import _collect_text_preview, _compute_child_types
from .geometry import filter_visible_children, get_bbox, resolve_absolute_coords
from .metadata import find_node_by_id, get_root_node, is_unnamed, load_metadata


def collect_low_confidence_renames(renames, threshold=LLM_FALLBACK_CONFIDENCE_THRESHOLD):
    """Filter renames to only those below the confidence threshold.

    Args:
        renames: Full rename dict from collect_renames().
        threshold: Confidence score below which to include (exclusive).

    Returns:
        Dict of node_id -> rename info for low-confidence entries.
    """
    return {
        node_id: info
        for node_id, info in renames.items()
        if info.get('confidence', 100) < threshold
    }


def _build_node_context(node, parent=None, siblings=None, stage_a_candidates=None):
    """Build enriched context dict for a single node.

    Collects structural information (type, size, children, text preview,
    sibling context) to give the LLM enough signal to infer a good name.
    Now includes method origin from Stage A candidates when available.

    Args:
        node: The Figma node dict.
        parent: Parent node dict, or None.
        siblings: List of sibling nodes (visible children of parent).
        stage_a_candidates: Optional list of Stage A grouping candidates.

    Returns:
        Dict with node context fields.
    """
    children = filter_visible_children(node)
    bb = node.get('absoluteBoundingBox', {})

    # Collect text from children and grandchildren (deeper than default)
    text_preview = _collect_text_preview(node, max_depth=5)
    child_types = _compute_child_types(children) if children else '-'

    # Sibling context
    sibling_names = []
    sibling_types = []
    if siblings:
        for s in siblings[:15]:  # limit to 15 siblings
            s_name = s.get('name', '')
            s_type = s.get('type', '')
            sibling_names.append(s_name if not is_unnamed(s_name) else f'[{s_type}]')
            sibling_types.append(s_type)

    # Method origin context (v2)
    method_tag = '-'
    if stage_a_candidates:
        node_id = node.get('id', '')
        for cand in stage_a_candidates:
            if node_id in cand.get('node_ids', []):
                method = cand.get('method', '?')
                score = cand.get('score', 0)
                method_tag = f"{method}@{score:.1f}"
                break

    return {
        'id': node.get('id', ''),
        'type': node.get('type', ''),
        'current_name': node.get('name', ''),
        'width': bb.get('width', 0),
        'height': bb.get('height', 0),
        'x': bb.get('x', 0),
        'y': bb.get('y', 0),
        'child_count': len(children),
        'child_types': child_types,
        'text_preview': text_preview,
        'parent_name': parent.get('name', '') if parent else '',
        'parent_type': parent.get('type', '') if parent else '',
        'sibling_names': sibling_names,
        'sibling_types': sibling_types,
        'is_leaf': len(children) == 0,
        'method_origin': method_tag,
    }


def _find_parent(root, target_id):
    """Find parent node of target_id in the tree.

    Args:
        root: Root of the tree to search.
        target_id: ID of the node whose parent we want.

    Returns:
        Parent node dict, or None if not found.
    """
    children = root.get('children', [])
    for child in children:
        if child.get('id') == target_id:
            return root
        result = _find_parent(child, target_id)
        if result is not None:
            return result
    return None


def build_fallback_context(low_confidence_renames, metadata_path,
                           stage_a_candidates=None):
    """Build enriched context for all low-confidence renames.

    Loads metadata, resolves coordinates, and builds a context dict
    for each low-confidence node with structural and sibling information.

    Args:
        low_confidence_renames: Dict from collect_low_confidence_renames().
        metadata_path: Path to Figma metadata JSON file.
        stage_a_candidates: Optional list of Stage A grouping candidates.

    Returns:
        List of context dicts, one per node.
    """
    data = load_metadata(metadata_path)
    root = get_root_node(data)
    resolve_absolute_coords(root)

    contexts = []
    for node_id, info in low_confidence_renames.items():
        node = find_node_by_id(root, node_id)
        if not node:
            continue

        # Find parent and siblings
        parent = _find_parent(root, node_id)
        siblings = filter_visible_children(parent) if parent else []

        ctx = _build_node_context(node, parent, siblings,
                                  stage_a_candidates=stage_a_candidates)
        ctx['heuristic_name'] = info.get('new_name', '')
        ctx['confidence'] = info.get('confidence', 0)
        contexts.append(ctx)

    return contexts


def format_fallback_prompt(contexts, template=None, all_renames=None):
    """Format the LLM fallback prompt with enhanced context.

    Generates a markdown-formatted prompt containing a table of low-confidence
    nodes with their structural context, plus naming guidelines and expected
    output format.

    Args:
        contexts: List of context dicts from build_fallback_context().
        template: Optional prompt template string with {node_count} and
                  {node_table} placeholders. If None, uses default prompt.
        all_renames: Full rename dict (for surrounding context, optional).

    Returns:
        Formatted prompt string, or empty string if no contexts.
    """
    if not contexts:
        return ''

    # Build markdown table (v2: includes Method column)
    rows = []
    for i, ctx in enumerate(contexts, 1):
        sibling_str = ', '.join(ctx.get('sibling_names', [])[:5])
        method_tag = ctx.get('method_origin', '-')
        rows.append(
            f"| {i} | `{ctx['id']}` | {ctx['type']} | {ctx['width']}x{ctx['height']} "
            f"| {ctx['child_count']} | {ctx['child_types']} | {ctx['text_preview']} "
            f"| {ctx['heuristic_name']} ({ctx['confidence']}%) "
            f"| {method_tag} | {sibling_str} |"
        )

    table = (
        "| # | ID | Type | Size | Children | ChildTypes | Text | Heuristic | Method | Siblings |\n"
        "|----|-----|------|------|----------|------------|------|-----------|--------|----------|\n"
        + '\n'.join(rows)
    )

    # Build surrounding context section (v2: high-confidence renames)
    context_section = ''
    if all_renames:
        high_conf = {nid: info for nid, info in all_renames.items()
                     if info.get('confidence', 0) >= 70}
        if high_conf:
            context_rows = []
            for nid, info in list(high_conf.items())[:20]:  # limit to 20
                context_rows.append(
                    f"  - `{nid}`: {info.get('old_name', '?')} → **{info.get('new_name', '?')}** "
                    f"({info.get('confidence', 0)}%, {info.get('inference_method', '?')})"
                )
            context_section = (
                f"\n\n## 周辺コンテキスト（高信頼度のリネーム済みノード）\n"
                f"以下は同じデザイン内で高い信頼度でリネームされたノードです。\n"
                f"パターンや命名の一貫性の参考にしてください。\n\n"
                + '\n'.join(context_rows)
            )

    if template:
        return template.replace('{node_count}', str(len(contexts))).replace('{node_table}', table)

    # Default inline prompt (v2: enhanced with method and surrounding context)
    return (
        f"以下の {len(contexts)} 個のFigmaノードに対して、セマンティックな名前を提案してください。\n"
        f"ヒューリスティックでは低信頼度の名前しか付けられませんでした。\n\n"
        f"{table}\n"
        f"{context_section}\n\n"
        f"## 命名規約\n"
        f"- kebab-case（例: section-hero, card-feature, heading-about）\n"
        f"- プレフィックス: section-, card-, heading-, body-, btn-, nav-, img-, icon-, bg-, container-, list-, form-\n"
        f"- テキスト内容・子要素構成・兄弟コンテキスト・Method列から役割を推論\n"
        f"- Method列はヒューリスティック検出メソッドとスコア（例: proximity@0.7）\n"
        f"- 日本語テキストはローマ字/英訳でslug化\n\n"
        f"## 出力形式\n"
        f"```yaml\n"
        f"renames:\n"
        f"  \"node_id\":\n"
        f"    new: \"suggested-name\"\n"
        f"    reason: \"推論根拠（1行）\"\n"
        f"    confidence: 高|中|低\n"
        f"```\n"
    )


def parse_llm_suggestions(text):
    """Parse Claude's YAML rename suggestions.

    Handles both raw YAML and YAML inside markdown code blocks.
    Uses simple string parsing (no yaml dependency).

    Args:
        text: Raw text from Claude's response containing YAML.

    Returns:
        Dict of node_id -> {'new': name, 'reason': reason}.
    """
    if not text or not isinstance(text, str):
        return {}

    # Extract YAML from markdown code block if present
    match = re.search(r'```ya?ml\s*\n(.*?)```', text, re.DOTALL)
    yaml_text = match.group(1) if match else text

    # Simple line-by-line parser for the expected format:
    #   renames:
    #     "node_id":
    #       new: "name"
    #       reason: "reason text"
    suggestions = {}
    current_id = None
    current_info = {}

    for line in yaml_text.split('\n'):
        stripped = line.strip()

        # Skip comments and empty lines
        if not stripped or stripped.startswith('#') or stripped == 'renames:':
            continue

        # Node ID line: "2:8320": or '2:8320': (ID may contain colons)
        id_match = re.match(r'^["\']([^"\']+)["\']\s*:\s*$', stripped)
        if id_match:
            # Save previous entry
            if current_id and 'new' in current_info:
                suggestions[current_id] = current_info
            current_id = id_match.group(1)
            current_info = {}
            continue

        # Key-value line: new: "name", reason: "text", or confidence: "高"
        kv_match = re.match(r'^(new|reason|confidence)\s*:\s*["\']?(.*?)["\']?\s*$', stripped)
        if kv_match and current_id:
            key = kv_match.group(1)
            value = kv_match.group(2).strip()
            current_info[key] = value

    # Save last entry
    if current_id and 'new' in current_info:
        suggestions[current_id] = current_info

    # Validate: names must be kebab-case (no spaces)
    validated = {}
    for node_id, info in suggestions.items():
        new_name = info.get('new', '').strip()
        if new_name and ' ' not in new_name:
            validated[str(node_id)] = {
                'new': new_name,
                'reason': info.get('reason', ''),
                'confidence': info.get('confidence', ''),
            }

    return validated


def merge_llm_suggestions(renames, suggestions):
    """Merge LLM suggestions into the rename map.

    Only overrides entries with confidence < LLM_FALLBACK_CONFIDENCE_THRESHOLD.
    Uses the LLM's self-reported confidence level (高/中/低) for dynamic
    confidence scoring instead of a fixed 85%.
    Mutates the renames dict in-place and returns it.

    Args:
        renames: Full rename dict (mutated in-place).
        suggestions: Dict from parse_llm_suggestions().

    Returns:
        Updated renames dict.
    """
    for node_id, suggestion in suggestions.items():
        if node_id in renames:
            existing = renames[node_id]
            if existing.get('confidence', 100) < LLM_FALLBACK_CONFIDENCE_THRESHOLD:
                existing['new_name'] = suggestion['new']
                existing['inference_method'] = 'llm_fallback'
                existing['llm_reason'] = suggestion.get('reason', '')
                # Dynamic confidence from LLM response (v2)
                llm_conf_str = suggestion.get('confidence', '').strip().lower()
                existing['confidence'] = LLM_CONFIDENCE_MAP.get(
                    llm_conf_str, LLM_DEFAULT_CONFIDENCE
                )
    return renames


def generate_fallback_context_file(renames, metadata_path, output_path,
                                   stage_a_candidates=None):
    """Generate a fallback context JSON file for SKILL.md workflow.

    Writes enriched context for all low-confidence renames to a JSON file
    that the SKILL.md workflow can read and pass to Claude for better naming.

    Args:
        renames: Full rename dict with confidence scores.
        metadata_path: Path to metadata JSON.
        output_path: Path to write context JSON.
        stage_a_candidates: Optional list of Stage A grouping candidates.

    Returns:
        Number of low-confidence items (0 if none).
    """
    low_conf = collect_low_confidence_renames(renames)
    if not low_conf:
        return 0

    contexts = build_fallback_context(low_conf, metadata_path,
                                      stage_a_candidates=stage_a_candidates)
    prompt = format_fallback_prompt(contexts, all_renames=renames)

    output = {
        'total_renames': len(renames),
        'low_confidence_count': len(low_conf),
        'threshold': LLM_FALLBACK_CONFIDENCE_THRESHOLD,
        'contexts': contexts,
        'prompt': prompt,
    }

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return len(low_conf)

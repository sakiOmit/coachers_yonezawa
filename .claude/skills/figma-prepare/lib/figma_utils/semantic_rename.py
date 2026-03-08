"""Semantic rename logic for figma-prepare Phase 3.

Extracts all Python logic previously embedded in generate-rename-map.sh.
Provides ``generate_rename_map()`` as the main entry point, plus helper
functions for name inference and rename collection.

Split into submodules:
  rename_strategies  - Priority-level helpers (_infer_from_text_content,
                       _infer_from_shape, _infer_from_position, _infer_from_children)

Issue: Extracted from shell heredoc for maintainability.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from .constants import (
    UNNAMED_RE,
    BUTTON_TEXT_MAX_LEN,
    IMAGE_WRAPPER_RATIO,
    LABEL_MAX_LEN,
)
from .detection import (
    detect_en_jp_label_pairs,
)
from .geometry import FigmaNode, filter_visible_children, resolve_absolute_coords, yaml_str
from .metadata import get_root_node, get_text_children_content as _get_text_children, load_metadata
from .naming import _jp_keyword_lookup, to_kebab

# Re-export from rename_strategies for backward compatibility
from .rename_strategies import (  # noqa: F401
    RENAME_STRATEGIES,
    _infer_from_text_content,
    _infer_from_shape,
    _infer_from_position,
    _infer_from_children,
)
from .rename_strategies import _SHAPE_PREFIXES, _CTA_KEYWORDS  # noqa: F401

# ---------------------------------------------------------------------------
# Shape prefix mapping — re-export from rename_strategies (single source of truth)
# ---------------------------------------------------------------------------
SHAPE_PREFIXES = _SHAPE_PREFIXES

# CTA keywords used in Priority 3.15 — re-export from rename_strategies
CTA_KEYWORDS = _CTA_KEYWORDS


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def get_text_children_content(children):
    """Collect TEXT children's content, filtering unnamed. Delegates to shared util (Issue 49)."""
    return _get_text_children(children, filter_unnamed=True)


def infer_text_role(text_content, font_size=None):
    """Infer role from text content."""
    content = text_content.strip()
    if not content:
        return None
    # Short button-like text
    if len(content) <= BUTTON_TEXT_MAX_LEN and any(kw in content.lower() for kw in [
        'more', '詳しく', '一覧', 'submit', '送信', '申し込', 'contact', 'click',
        '見る', '戻る', '申込', '詳細',
    ]):
        return 'btn-text'
    # Labels
    if len(content) <= LABEL_MAX_LEN:
        return 'label'
    return 'body'


def has_image_wrapper(children):
    """Check if any child is an image wrapper frame (contains mostly images/rectangles).

    Detects patterns like: FRAME containing [RECTANGLE, RECTANGLE, IMAGE] where the
    sub-frame acts as an image container. Returns True if any child FRAME/GROUP has
    >= 50% of its children as image-like types (RECTANGLE, IMAGE, ELLIPSE).
    """
    for c in children:
        c_type = c.get('type', '')
        if c_type not in ('FRAME', 'GROUP', 'INSTANCE', 'COMPONENT'):
            continue
        sub_children = filter_visible_children(c)
        if not sub_children:
            continue
        rect_count = sum(1 for sc in sub_children if sc.get('type', '') in ('RECTANGLE', 'IMAGE', 'ELLIPSE'))
        if rect_count >= len(sub_children) * IMAGE_WRAPPER_RATIO and rect_count >= 1:
            return True
    return False


def _resolve_slug(text_contents_list):
    """Get a meaningful slug, trying to_kebab then JP keyword lookup.

    Issue 170: Helper to resolve a slug that avoids bare 'content'.
    """
    for t in text_contents_list:
        slug = to_kebab(t[:30])
        if slug and slug != 'content':
            return slug
    # to_kebab returned 'content' for all — try JP keyword lookup
    for t in text_contents_list:
        jp_slug = _jp_keyword_lookup(t)
        if jp_slug:
            return jp_slug
    return ''


def _estimate_children_confidence(name):
    """Estimate confidence of a children-based inference result.

    Returns a score 0-100 based on the name prefix and whether the name
    has a meaningful slug (vs just a numeric index).
    """
    if name.startswith('nav-'):
        return 80
    if name.startswith('decoration-'):
        return 90
    if name.startswith('card-') and not name.endswith(('-0', '-1', '-2', '-3', '-4', '-5')):
        return 70  # has slug
    if name.startswith('card-'):
        return 55  # index-only
    if name.startswith('icon-'):
        return 85
    if name.startswith('btn-') and not name.endswith(('-0', '-1', '-2', '-3', '-4', '-5')):
        return 75  # has slug
    if name.startswith('btn-'):
        return 60
    if name.startswith('heading-') and not name.endswith(('-0', '-1', '-2', '-3', '-4', '-5')):
        return 70
    if name.startswith(('body-', 'content-')):
        return 60
    if name.startswith('text-block-') and not name.endswith(('-0', '-1', '-2', '-3', '-4', '-5')):
        return 65
    if name.startswith(('container-', 'group-')) and not any(name.endswith(f'-{i}') for i in range(20)):
        return 40  # has slug but weak
    if name.startswith(('container-', 'group-')):
        return 20  # index-only, very weak
    return 50  # unknown pattern


def infer_name_with_confidence(node: FigmaNode, parent: FigmaNode | None = None, sibling_index: int = 0, total_siblings: int = 1) -> tuple[str, int]:
    """Infer semantic name with confidence score (0-100).

    Iterates over RENAME_STRATEGIES in priority order, invoking each
    strategy function with the appropriate arguments.  Returns the first
    non-None result together with its confidence score.

    Returns (name, confidence) tuple. Higher confidence means the heuristic
    is more certain about the inferred name.

    Confidence guidelines (see RENAME_STRATEGIES for canonical values):
      90     - Text content match (Priority 0-1)
      85     - Shape analysis match (Priority 2)
      75     - Position analysis match (Priority 3)
      varies - Children-based match (Priority 3.5-4), depends on pattern
      10     - Fallback (type-index)
    """
    node_type = node.get('type', '')
    children = filter_visible_children(node)
    name = node.get('name', '')
    abs_bbox = node.get('absoluteBoundingBox', {})
    w = abs_bbox.get('width', 0)
    h = abs_bbox.get('height', 0)

    # Dispatch through RENAME_STRATEGIES in priority order
    for _priority, strategy_fn, _desc, confidence in RENAME_STRATEGIES:
        if strategy_fn is _infer_from_text_content:
            result = strategy_fn(node, node_type, name, sibling_index)
        elif strategy_fn is _infer_from_shape:
            result = strategy_fn(node, node_type, children, w, h, sibling_index)
        elif strategy_fn is _infer_from_position:
            result = strategy_fn(
                node, node_type, parent, children, abs_bbox, w, h,
                sibling_index, total_siblings,
            )
        elif strategy_fn is _infer_from_children:
            result = strategy_fn(node, node_type, children, w, h, sibling_index)
        else:
            # Unknown strategy — log warning and skip
            import warnings
            warnings.warn(f"Unknown rename strategy: {strategy_fn.__name__}", stacklevel=2)
            continue

        if result is not None:
            if confidence is None:
                # Dynamic confidence (children-based strategies)
                confidence = _estimate_children_confidence(result)
            return (result, confidence)

    # Priority 5: Fallback — no strategy matched
    type_prefix = node_type.lower().replace('_', '-')
    return (f'{type_prefix}-{sibling_index}', 10)


def infer_name(node: FigmaNode, parent: FigmaNode | None = None, sibling_index: int = 0, total_siblings: int = 1) -> str:
    """Infer semantic name for an unnamed node.

    Dispatches to priority-level helpers in rename_strategies.py.
    Returns first non-None result, or a type-based fallback.

    Note: For (name, confidence) tuple, use infer_name_with_confidence().
    """
    name, _confidence = infer_name_with_confidence(node, parent, sibling_index, total_siblings)
    return name


def collect_renames(node, parent=None, sibling_index=0, total_siblings=1, renames=None, en_jp_overrides=None):
    """Recursively collect rename candidates."""
    if renames is None:
        renames = {}
    if en_jp_overrides is None:
        en_jp_overrides = {}

    if node.get('visible') == False:
        return renames

    name = node.get('name', '')
    node_id = node.get('id', '')

    # Issue 185: Check if this node has an EN+JP pair override
    if node_id in en_jp_overrides:
        override_name = en_jp_overrides[node_id]
        if override_name != name:
            renames[node_id] = {
                'old_name': name,
                'new_name': override_name,
                'type': node.get('type', ''),
                'inference_method': 'en_jp_pair',
            }
    elif UNNAMED_RE.match(name) and node_id:
        new_name, confidence = infer_name_with_confidence(node, parent, sibling_index, total_siblings)
        if new_name and new_name != name:
            renames[node_id] = {
                'old_name': name,
                'new_name': new_name,
                'type': node.get('type', ''),
                'inference_method': 'auto',
                'confidence': confidence,
            }

    children = filter_visible_children(node)

    # Issue 185: Detect EN+JP label pairs among children
    child_overrides = {}
    if children:
        pairs = detect_en_jp_label_pairs(children)
        for pair in pairs:
            en_child = children[pair['en_idx']]
            jp_child = children[pair['jp_idx']]
            en_id = en_child.get('id', '')
            jp_id = jp_child.get('id', '')
            en_name_val = en_child.get('name', '')
            jp_name_val = jp_child.get('name', '')
            en_slug = to_kebab(pair['en_text'][:20])
            # Only override unnamed nodes
            if en_id and UNNAMED_RE.match(en_name_val):
                child_overrides[en_id] = f'en-label-{en_slug}' if en_slug and en_slug != 'content' else f'en-label-{pair["en_idx"]}'
            if jp_id and UNNAMED_RE.match(jp_name_val):
                jp_slug = _jp_keyword_lookup(pair['jp_text'])
                if not jp_slug:
                    jp_slug = to_kebab(pair['jp_text'][:30])
                if jp_slug and jp_slug != 'content':
                    child_overrides[jp_id] = f'heading-{jp_slug}'
                else:
                    child_overrides[jp_id] = f'heading-{pair["jp_idx"]}'

    for i, child in enumerate(children):
        collect_renames(child, node, i, len(children), renames, child_overrides)

    return renames


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_rename_map(metadata_path: str, output_file: str = '', fallback_context_path: str = '') -> None:
    """Generate a semantic rename map from Figma metadata.

    Args:
        metadata_path: Path to Figma metadata JSON file.
        output_file: If non-empty, write YAML to this path and print summary JSON.
                     If empty, print full rename JSON to stdout.
        fallback_context_path: If non-empty, generate LLM fallback context JSON
                               for low-confidence renames at this path.

    Returns:
        None (output goes to stdout/file).

    Raises:
        Prints error JSON to stderr and calls sys.exit(1) on failure.
    """
    sys.setrecursionlimit(3000)  # Guard against deeply nested Figma files (Issue 48)

    try:
        data = load_metadata(metadata_path)
        root = get_root_node(data)
        resolve_absolute_coords(root)
        renames = collect_renames(root)

        # Generate LLM fallback context if requested
        low_confidence_count = 0
        if fallback_context_path:
            from .rename_llm_fallback import generate_fallback_context_file
            low_confidence_count = generate_fallback_context_file(
                renames, metadata_path, fallback_context_path
            )

        if output_file:
            # YAML output
            with open(output_file, 'w') as f:
                f.write('# Figma Rename Map\n')
                f.write(f'# Total renames: {len(renames)}\n')
                f.write('# Generated by /figma-prepare Phase 3\n')
                f.write('# Review before applying with --apply\n\n')
                f.write('renames:\n')
                for node_id, info in sorted(renames.items()):
                    f.write(f'  {yaml_str(node_id)}:\n')
                    f.write(f'    old: {yaml_str(info["old_name"])}\n')
                    f.write(f'    new: {yaml_str(info["new_name"])}\n')
                    f.write(f'    type: {yaml_str(info["type"])}\n')
                    f.write(f'    confidence: {info.get("confidence", 100)}\n')
            summary = {
                'total': len(renames),
                'output': output_file,
                'status': 'dry-run',
            }
            if fallback_context_path and low_confidence_count > 0:
                summary['low_confidence_count'] = low_confidence_count
                summary['fallback_context'] = fallback_context_path
            print(json.dumps(summary, indent=2))
        else:
            # JSON to stdout
            result = {
                'total': len(renames),
                'renames': renames,
                'status': 'dry-run',
            }
            if fallback_context_path and low_confidence_count > 0:
                result['low_confidence_count'] = low_confidence_count
                result['fallback_context'] = fallback_context_path
            print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        print(json.dumps({'error': str(e)}), file=sys.stderr)
        sys.exit(1)

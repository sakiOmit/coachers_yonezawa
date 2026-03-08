"""LLM fallback for grouping correction (1:N heading-content patterns).

After Stage C grouping, reviews the grouping plan to identify sections where
heading-to-multiple-content patterns may have been missed. Generates enriched
context for Claude to propose corrections.

Symmetric to rename_llm_fallback.py:
  rename_llm_fallback → low-confidence *renames* → Claude suggests better names
  grouping_llm_fallback → undergrouped *sections* → Claude suggests grouping corrections

Issue #274: 1:N heading-content grouping via LLM fallback intervention.

Usage in SKILL.md workflow:
  1. Stage C generates nested-grouping-plan.yaml
  2. ``collect_undergrouped_sections()`` finds candidate sections
  3. ``build_grouping_fallback_context()`` enriches them with metadata
  4. ``format_grouping_fallback_prompt()`` generates the prompt
  5. Claude suggests corrections → ``parse_llm_grouping_suggestions()``
  6. ``merge_grouping_suggestions()`` patches the plan
"""

import json
import os
import re

from .constants import (
    GROUPING_FALLBACK_HEADING_MAX_HEIGHT,
    GROUPING_FALLBACK_MAX_SIBLINGS,
    GROUPING_FALLBACK_MIN_SIBLINGS_AFTER_HEADING,
    GROUPING_FALLBACK_STRUCTURE_SIMILARITY,
    HEADING_MAX_CHILDREN,
    HEADING_TEXT_RATIO,
    LLM_CONFIDENCE_MAP,
    LLM_DEFAULT_CONFIDENCE,
)

# Re-export from constants for backward compatibility
GROUPING_LLM_CONFIDENCE_MAP = LLM_CONFIDENCE_MAP
GROUPING_LLM_DEFAULT_CONFIDENCE = LLM_DEFAULT_CONFIDENCE

__all__ = [
    "GROUPING_LLM_CONFIDENCE_MAP",
    "GROUPING_LLM_DEFAULT_CONFIDENCE",
    "build_grouping_fallback_context",
    "collect_undergrouped_sections",
    "format_grouping_fallback_prompt",
    "generate_grouping_fallback_context_file",
    "merge_grouping_suggestions",
    "parse_llm_grouping_suggestions",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_heading_like_row(row):
    """Check if an enriched table row looks like a heading element.

    Args:
        row: Dict from enriched table with 'type', 'h', 'text', 'name',
             'child_types', etc.

    Returns:
        True if the row appears heading-like.
    """
    row_type = str(row.get('type', ''))
    h = _parse_dimension(row.get('h', 0))

    # TEXT nodes are heading candidates if height is reasonable
    if row_type == 'TEXT' and 0 < h <= GROUPING_FALLBACK_HEADING_MAX_HEIGHT:
        return True

    # Named heading nodes
    name = str(row.get('name', '')).lower()
    if 'heading' in name or 'en-label' in name:
        return True

    # FRAME with text content and small height
    if h > 0 and h <= GROUPING_FALLBACK_HEADING_MAX_HEIGHT:
        text = str(row.get('text', '')).strip()
        if text:
            # Check if leaf or has few children
            child_types = str(row.get('child_types', '-'))
            if child_types == '-' or _count_child_type_total(child_types) <= HEADING_MAX_CHILDREN:
                return True

    return False


def _count_child_type_total(child_types_str):
    """Parse ChildTypes string like '2TEX+1REC' and return total count."""
    if not child_types_str or child_types_str == '-':
        return 0
    total = 0
    for part in child_types_str.split('+'):
        part = part.strip()
        match = re.match(r'(\d+)', part)
        if match:
            total += int(match.group(1))
    return total


def _parse_dimension(val):
    """Parse a dimension value, handling int, float, and string formats.

    Args:
        val: int, float, or string dimension value.

    Returns:
        int: Parsed dimension value, or 0 on failure.
    """
    if isinstance(val, (int, float)):
        return int(val)
    val_str = str(val).strip()
    # Handle "WxH" format — return the value itself (caller picks w or h)
    try:
        return int(val_str)
    except (ValueError, TypeError):
        return 0


def _enriched_row_hash(row):
    """Build a simple hash string from an enriched table row for similarity.

    Args:
        row: Dict from enriched table.

    Returns:
        str: Hash string combining type, child types, and quantized dimensions.
    """
    rtype = str(row.get('type', ''))
    child_types = str(row.get('child_types', '-'))
    w = _parse_dimension(row.get('w', 0))
    h = _parse_dimension(row.get('h', 0))
    # Quantize dimensions to 50px buckets for fuzzy matching
    w_bucket = (w // 50) * 50 if w > 0 else 0
    h_bucket = (h // 50) * 50 if h > 0 else 0
    return f"{rtype}:{child_types}:{w_bucket}x{h_bucket}"


def _simple_hash_similarity(hash_a, hash_b):
    """Compute simple similarity between two enriched row hashes.

    Uses Jaccard-like comparison on the hash components.

    Args:
        hash_a: Hash string from _enriched_row_hash.
        hash_b: Hash string from _enriched_row_hash.

    Returns:
        float: Similarity score 0.0-1.0.
    """
    if hash_a == hash_b:
        return 1.0
    if not hash_a or not hash_b:
        return 0.0

    parts_a = set(hash_a.split(':'))
    parts_b = set(hash_b.split(':'))
    intersection = len(parts_a & parts_b)
    union = len(parts_a | parts_b)
    if union <= 0:  # Zero division guard
        return 0.0
    return intersection / union


def _sanitize_row(row):
    """Convert enriched row to a JSON-safe dict.

    Args:
        row: Dict with potentially non-serializable values.

    Returns:
        Dict with all values as JSON-safe types.
    """
    result = {}
    for k, v in row.items():
        if isinstance(v, (str, int, float, bool)):
            result[k] = v
        elif v is None:
            result[k] = ''
        else:
            result[k] = str(v)
    return result


def _is_valid_correction(correction):
    """Check if a parsed correction dict has all required fields.

    Args:
        correction: Dict parsed from LLM YAML response.

    Returns:
        True if the correction has heading_id, group_name, and member_ids.
    """
    return (
        bool(correction.get('heading_id'))
        and bool(correction.get('group_name'))
        and bool(correction.get('member_ids'))
        and isinstance(correction.get('member_ids'), list)
        and len(correction['member_ids']) > 0
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def collect_undergrouped_sections(grouping_plan_entries, enriched_rows):
    """Find sections where heading→N-content patterns may be missed.

    Detection criteria:
    - A heading-like entry (small height, text-heavy) followed by 3+ siblings
      with similar structure that are not already in the same group.
    - Consecutive items with same structure hash not yet grouped together.

    Args:
        grouping_plan_entries: list of dicts from grouping plan YAML.
            Each has 'node_ids', 'suggested_name', 'method', etc.
        enriched_rows: list of dicts from enriched table.
            Each has 'id', 'name', 'type', 'w', 'h', 'flags', 'text', etc.

    Returns:
        list of dicts: [{
            'heading_id': str,
            'heading_name': str,
            'candidate_ids': [str, ...],
            'reason': str,
            'section_context': str,
        }]
    """
    if not enriched_rows:
        return []

    # Build set of already-grouped IDs and group membership map
    grouped_ids = set()
    id_to_group = {}
    for entry in (grouping_plan_entries or []):
        nids = entry.get('node_ids', [])
        group_name = entry.get('suggested_name', '')
        for nid in nids:
            grouped_ids.add(str(nid))
            id_to_group[str(nid)] = group_name

    # Index enriched rows by ID, preserving order
    row_by_id = {}
    row_order = []
    for row in enriched_rows:
        rid = str(row.get('id', ''))
        if rid:
            row_by_id[rid] = row
            row_order.append(rid)

    results = []

    for i, rid in enumerate(row_order):
        row = row_by_id[rid]

        # Check if this row looks like a heading
        if not _is_heading_like_row(row):
            continue

        # Heading must not already be fully grouped with its followers
        heading_group = id_to_group.get(rid, '')

        # Collect subsequent siblings with similar structure
        candidates = []
        ref_hash = None

        for j in range(i + 1, min(i + 1 + GROUPING_FALLBACK_MAX_SIBLINGS, len(row_order))):
            next_rid = row_order[j]
            next_row = row_by_id[next_rid]

            # Stop at next heading-like element (new topic boundary)
            if _is_heading_like_row(next_row):
                break

            cur_hash = _enriched_row_hash(next_row)

            if ref_hash is None:
                ref_hash = cur_hash
                candidates.append(next_rid)
            else:
                sim = _simple_hash_similarity(ref_hash, cur_hash)
                if sim >= GROUPING_FALLBACK_STRUCTURE_SIMILARITY:
                    candidates.append(next_rid)
                else:
                    break

        if len(candidates) < GROUPING_FALLBACK_MIN_SIBLINGS_AFTER_HEADING:
            continue

        # Check if heading + candidates are already in the same group
        if heading_group:
            all_in_same_group = all(
                id_to_group.get(cid, '') == heading_group
                for cid in candidates
            )
            if all_in_same_group:
                continue

        # Determine section context
        text_content = str(row.get('text', '')).strip()
        row_name = str(row.get('name', ''))
        section_ctx = row_name if row_name and row_name != '-' else (text_content[:30] if text_content else 'unknown')

        h = _parse_dimension(row.get('h', 0))
        results.append({
            'heading_id': rid,
            'heading_name': row_name,
            'candidate_ids': candidates,
            'reason': (
                f"Heading ({h}px height) with text '{text_content[:30]}' "
                f"followed by {len(candidates)} structurally similar siblings "
                f"not grouped together"
            ),
            'section_context': section_ctx,
        })

    return results


def build_grouping_fallback_context(undergrouped, enriched_rows, metadata_path=''):
    """Build context for LLM review of undergrouped sections.

    Args:
        undergrouped: output from collect_undergrouped_sections.
        enriched_rows: enriched table data (list of dicts).
        metadata_path: optional path for additional metadata.

    Returns:
        dict with 'sections' list, each containing heading info,
        candidates, enriched excerpts.
    """
    if not undergrouped:
        return {'sections': []}

    # Index enriched rows
    row_by_id = {}
    for row in enriched_rows:
        rid = str(row.get('id', ''))
        if rid:
            row_by_id[rid] = row

    sections = []
    for item in undergrouped:
        heading_row = row_by_id.get(item['heading_id'], {})
        candidate_rows = [
            row_by_id.get(cid, {'id': cid})
            for cid in item['candidate_ids']
        ]

        sections.append({
            'heading_id': item['heading_id'],
            'heading_name': item['heading_name'],
            'heading_row': _sanitize_row(heading_row),
            'candidate_ids': item['candidate_ids'],
            'candidate_rows': [_sanitize_row(r) for r in candidate_rows],
            'reason': item['reason'],
            'section_context': item['section_context'],
        })

    return {'sections': sections}


def format_grouping_fallback_prompt(context):
    """Generate prompt for Claude to review/correct groupings.

    Args:
        context: dict from build_grouping_fallback_context.

    Returns:
        str: formatted prompt string, or empty string if no sections.
    """
    sections = context.get('sections', [])
    if not sections:
        return ''

    # Try to load template
    template_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'references', 'grouping-fallback-prompt-template.md'
    )
    template = None
    if os.path.isfile(template_path):
        try:
            with open(template_path, 'r') as f:
                content = f.read()
            # Extract the template block between the first ``` pair
            tmpl_match = re.search(r'## Prompt Template.*?```\n(.*?)```', content, re.DOTALL)
            if tmpl_match:
                template = tmpl_match.group(1)
        except OSError:
            pass

    # Build section tables
    section_blocks = []
    for i, sec in enumerate(sections, 1):
        heading = sec.get('heading_row', {})
        candidates = sec.get('candidate_rows', [])

        rows = []
        # Heading row
        rows.append(
            f"| H | `{sec['heading_id']}` | {heading.get('name', '?')} | "
            f"{heading.get('type', '?')} | {heading.get('w', '?')}x{heading.get('h', '?')} | "
            f"{heading.get('child_types', '-')} | {heading.get('text', '-')} |"
        )
        # Candidate rows
        for j, cand in enumerate(candidates):
            rows.append(
                f"| C{j+1} | `{cand.get('id', '?')}` | {cand.get('name', '?')} | "
                f"{cand.get('type', '?')} | {cand.get('w', '?')}x{cand.get('h', '?')} | "
                f"{cand.get('child_types', '-')} | {cand.get('text', '-')} |"
            )

        table = (
            "| Role | ID | Name | Type | Size | ChildTypes | Text |\n"
            "|------|----|------|------|------|------------|------|\n"
            + '\n'.join(rows)
        )

        block = (
            f"### Section {i}: {sec.get('section_context', 'unknown')}\n\n"
            f"**Reason**: {sec.get('reason', '')}\n\n"
            f"{table}\n"
        )
        section_blocks.append(block)

    section_text = '\n\n'.join(section_blocks)

    if template:
        return (
            template
            .replace('{section_count}', str(len(sections)))
            .replace('{section_tables}', section_text)
        )

    # Default inline prompt
    return (
        f"以下の {len(sections)} セクションで、見出し（heading）と"
        f"後続コンテンツの1:Nグルーピングが不足している可能性があります。\n\n"
        f"各セクションの見出し（H行）と候補コンテンツ（C行）を確認し、"
        f"グルーピング修正を提案してください。\n\n"
        f"{section_text}\n\n"
        f"## グルーピング判断基準\n"
        f"- 見出しテキストがトピックを示し、後続要素がそのトピックの詳細である場合 → グループ化\n"
        f"- 後続要素の構造（ChildTypes）が類似している場合 → リスト/カード構造\n"
        f"- 見出しと後続要素の間に視覚的な関連がない場合 → グループ化しない\n\n"
        f"## 出力形式\n"
        f"```yaml\n"
        f"corrections:\n"
        f"  - heading_id: \"123:456\"\n"
        f"    heading_name: \"heading-climate-change\"\n"
        f"    group_name: \"topic-climate-change\"\n"
        f"    member_ids: [\"123:457\", \"123:458\", \"123:459\"]\n"
        f"    confidence: high\n"
        f"    reason: \"These items are activities under the climate change topic\"\n"
        f"```\n"
    )


def parse_llm_grouping_suggestions(llm_response):
    """Parse LLM's YAML suggestions for grouping corrections.

    Expected LLM output format::

        corrections:
          - heading_id: "123:456"
            heading_name: "heading-climate-change"
            group_name: "topic-climate-change"
            member_ids: ["123:457", "123:458", "123:459"]
            confidence: high
            reason: "These items are activities under the climate change topic"

    Args:
        llm_response: Raw text from Claude's response containing YAML.

    Returns:
        list of correction dicts.
    """
    if not llm_response or not isinstance(llm_response, str):
        return []

    # Extract YAML from markdown code block if present
    match = re.search(r'```ya?ml\s*\n(.*?)```', llm_response, re.DOTALL)
    yaml_text = match.group(1) if match else llm_response

    corrections = []
    current = {}

    for line in yaml_text.split('\n'):
        stripped = line.strip()

        # Skip empty lines, comments, and the corrections: header
        if not stripped or stripped.startswith('#') or stripped == 'corrections:':
            continue

        # New item starts with "- "
        if stripped.startswith('- '):
            # Save previous entry
            if _is_valid_correction(current):
                corrections.append(current)
            current = {}
            stripped = stripped[2:]  # remove "- " prefix

        # Parse key-value pairs
        kv_match = re.match(
            r'(heading_id|heading_name|group_name|confidence|reason)\s*:\s*["\']?(.*?)["\']?\s*$',
            stripped
        )
        if kv_match:
            current[kv_match.group(1)] = kv_match.group(2).strip()
            continue

        # Parse member_ids array
        member_match = re.match(r'member_ids\s*:\s*\[(.*)\]\s*$', stripped)
        if member_match:
            ids_str = member_match.group(1)
            # Parse quoted IDs: "123:456", "123:457"
            ids = re.findall(r'["\']([^"\']+)["\']', ids_str)
            current['member_ids'] = ids

    # Save last entry
    if _is_valid_correction(current):
        corrections.append(current)

    return corrections


def merge_grouping_suggestions(original_plan_entries, suggestions):
    """Merge LLM corrections into original grouping plan.

    For each suggestion:
    - Create a new group entry with the heading + member IDs
    - Remove those IDs from any existing groups they belong to
    - Set method='llm_grouping_fallback'

    Args:
        original_plan_entries: list of grouping plan entry dicts.
        suggestions: list of correction dicts from parse_llm_grouping_suggestions.

    Returns:
        list: updated plan entries (new list, original is not mutated).
    """
    if not suggestions:
        return list(original_plan_entries or [])

    # Deep copy entries to avoid mutation
    entries = [dict(e) for e in (original_plan_entries or [])]
    for e in entries:
        if 'node_ids' in e:
            e['node_ids'] = list(e['node_ids'])

    for suggestion in suggestions:
        heading_id = str(suggestion.get('heading_id', ''))
        member_ids = [str(mid) for mid in suggestion.get('member_ids', [])]
        group_name = suggestion.get('group_name', '')
        reason = suggestion.get('reason', '')
        conf_str = suggestion.get('confidence', '').strip().lower()

        if not heading_id or not member_ids or not group_name:
            continue

        all_ids = [heading_id] + member_ids

        # Remove these IDs from existing groups
        for entry in entries:
            nids = entry.get('node_ids', [])
            entry['node_ids'] = [nid for nid in nids if str(nid) not in all_ids]

        # Remove empty groups
        entries = [e for e in entries if e.get('node_ids')]

        # Add new group
        confidence = GROUPING_LLM_CONFIDENCE_MAP.get(
            conf_str, GROUPING_LLM_DEFAULT_CONFIDENCE
        )
        entries.append({
            'node_ids': all_ids,
            'suggested_name': group_name,
            'method': 'llm_grouping_fallback',
            'confidence': confidence,
            'reason': reason,
        })

    return entries


def generate_grouping_fallback_context_file(
    grouping_plan_entries, enriched_rows, metadata_path, output_path
):
    """Entry point: generate context file for LLM review.

    Detects undergrouped heading→N-content patterns, builds enriched
    context, and writes to a JSON file for SKILL.md workflow.

    Args:
        grouping_plan_entries: list of grouping plan entry dicts.
        enriched_rows: list of enriched table row dicts.
        metadata_path: path to metadata JSON (for additional context).
        output_path: path to write context JSON.

    Returns:
        int: number of undergrouped sections found.
    """
    undergrouped = collect_undergrouped_sections(
        grouping_plan_entries, enriched_rows
    )

    if not undergrouped:
        return 0

    context = build_grouping_fallback_context(
        undergrouped, enriched_rows, metadata_path
    )
    prompt = format_grouping_fallback_prompt(context)

    output = {
        'total_plan_entries': len(grouping_plan_entries or []),
        'undergrouped_count': len(undergrouped),
        'sections': context.get('sections', []),
        'prompt': prompt,
    }

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return len(undergrouped)

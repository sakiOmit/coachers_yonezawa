"""Grouping comparison, deduplication, and validation for figma-prepare.

Entry point module: re-exports all public API from submodules for backward
compatibility. Implements compare_grouping_results() and
compare_grouping_by_section() which orchestrate the submodules.

Submodules:
  comparison_dedup    - deduplicate_candidates, absorb_stage_c_dividers
  comparison_column   - validate_column_consistency
  comparison_matching - Jaccard matching, coverage metrics, report building
"""

from .constants import (
    COMPARE_MATCH_THRESHOLD,
    STAGE_MERGE_TIER1,
    STAGE_MERGE_TIER2,
    STAGE_MERGE_TIER3,
)

# Re-export from comparison_dedup
from .comparison_dedup import (  # noqa: F401
    deduplicate_candidates,
    absorb_stage_c_dividers,
    _is_divider_candidate,
    _find_adjacent_list_item,
    _should_absorb_into_higher,
)

# Re-export from comparison_column
from .comparison_column import (  # noqa: F401
    validate_column_consistency,
    _compute_col_for_nodes,
)

# Re-export from comparison_matching
from .comparison_matching import (  # noqa: F401
    _stage_a_pattern_key,
    _compute_jaccard_matches,
    _compute_coverage_metrics,
    _build_comparison_report,
    _aggregate_section_metrics,
)

__all__ = [
    "absorb_stage_c_dividers",
    "compare_grouping_by_section",
    "compare_grouping_results",
    "deduplicate_candidates",
    "validate_column_consistency",
]


def compare_grouping_results(stage_a_candidates, stage_c_groups, parent_id=None):
    """Compare Stage A and Stage C grouping results and return metrics.

    Stage A candidates come from detect-grouping-candidates.sh output
    (list of dicts with 'method', 'node_ids', 'semantic_type', etc.).

    Stage C groups come from nested-grouping-prompt-template.md output
    (list of dicts with 'name', 'pattern', 'node_ids', etc.).

    Args:
        stage_a_candidates: Stage A output (list of {method, node_ids, ...})
        stage_c_groups: Stage C output (list of {name, pattern, node_ids, ...})
        parent_id: Optional parent ID to filter candidates/groups by section.
            When specified, only Stage A candidates with matching parent_id
            (or parent field) and Stage C groups with matching section_id
            (or parent_group) are compared. When None, all are compared.

    Returns:
        dict: {
            'coverage': float,         # Stage C covers what fraction of Stage A nodes
            'jaccard_by_group': [...],  # Per Stage A group best-match Jaccard
            'mean_jaccard': float,      # Average Jaccard similarity
            'stage_a_only': [...],      # Stage A groups with no Stage C match
            'stage_c_only': [...],      # Stage C groups with no Stage A match
            'matched_pairs': [...],     # Matched (stage_a_idx, stage_c_idx, jaccard)
            'pattern_accuracy': {...},  # Per pattern type match/total
        }
    """
    # Filter by parent_id if specified
    if parent_id is not None:
        stage_a_candidates = [
            c for c in stage_a_candidates
            if c.get('parent_id') == parent_id or c.get('parent') == parent_id
        ]
        stage_c_groups = [
            g for g in stage_c_groups
            if g.get('section_id') == parent_id or g.get('parent_group') == parent_id
        ]
    if not stage_a_candidates and not stage_c_groups:
        return {
            'coverage': 1.0,
            'jaccard_by_group': [],
            'mean_jaccard': 1.0,
            'stage_a_only': [],
            'stage_c_only': [],
            'matched_pairs': [],
            'pattern_accuracy': {},
        }

    if not stage_a_candidates:
        return {
            'coverage': 1.0,
            'jaccard_by_group': [],
            'mean_jaccard': 0.0,
            'stage_a_only': [],
            'stage_c_only': list(range(len(stage_c_groups))),
            'matched_pairs': [],
            'pattern_accuracy': {},
        }

    if not stage_c_groups:
        return {
            'coverage': 0.0,
            'jaccard_by_group': [0.0] * len(stage_a_candidates),
            'mean_jaccard': 0.0,
            'stage_a_only': list(range(len(stage_a_candidates))),
            'stage_c_only': [],
            'matched_pairs': [],
            'pattern_accuracy': {},
        }

    # Build node_id sets
    a_sets = [set(c.get('node_ids', [])) for c in stage_a_candidates]
    c_sets = [set(g.get('node_ids', [])) for g in stage_c_groups]

    # Find matched pairs by Jaccard similarity
    jaccard_by_group, matched_pairs, matched_c_indices = _compute_jaccard_matches(
        a_sets, c_sets, COMPARE_MATCH_THRESHOLD
    )

    # Calculate coverage and unmatched groups
    coverage, mean_jaccard, stage_a_only, stage_c_only = _compute_coverage_metrics(
        a_sets, c_sets, matched_pairs, matched_c_indices,
        jaccard_by_group, len(stage_a_candidates), len(stage_c_groups)
    )

    # Assemble final report with pattern accuracy
    return _build_comparison_report(
        stage_a_candidates, stage_c_groups, matched_pairs,
        coverage, mean_jaccard, jaccard_by_group,
        stage_a_only, stage_c_only
    )


def _merge_stage_c_with_a_remainder(c_groups, a_cands, comparison_result):
    """Tier 2: Use Stage C groups + add unmatched Stage A candidates.

    Stage C is primary. For Stage A candidates that have no Stage C match
    (coverage gap), add them as supplementary groups.

    Args:
        c_groups: Stage C groups (primary)
        a_cands: Stage A candidates (supplement unmatched ones)
        comparison_result: dict from compare_grouping_results with 'stage_a_only'

    Returns:
        list: merged candidates (Stage C + unmatched Stage A)
    """
    # Start with all Stage C groups
    merged = list(c_groups)

    # Collect node IDs already covered by Stage C
    c_node_ids = set()
    for g in c_groups:
        c_node_ids.update(g.get('node_ids', []))

    # Add unmatched Stage A candidates whose nodes aren't in Stage C
    for a_idx in comparison_result.get('stage_a_only', []):
        if a_idx < len(a_cands):
            cand = a_cands[a_idx]
            cand_nodes = set(cand.get('node_ids', []))
            # Only add if majority of nodes are not already covered
            if len(cand_nodes) > 0:
                overlap = len(cand_nodes & c_node_ids)
                if overlap / len(cand_nodes) < 0.5:
                    merged.append(cand)
                    c_node_ids.update(cand_nodes)

    return merged


def _merge_stage_a_with_c_confident(a_cands, c_groups, comparison_result):
    """Tier 3: Use Stage A candidates + add high-confidence Stage C groups.

    Stage A is primary. Only adopt Stage C groups that:
    1. Have 3+ node_ids (substantial groups, not over-split)
    2. Don't conflict with existing Stage A coverage

    Args:
        a_cands: Stage A candidates (primary)
        c_groups: Stage C groups (supplement high-confidence ones)
        comparison_result: dict from compare_grouping_results with 'stage_c_only'

    Returns:
        list: merged candidates (Stage A + high-confidence Stage C)
    """
    # Start with all Stage A candidates
    merged = list(a_cands)

    # Collect node IDs already covered by Stage A
    a_node_ids = set()
    for c in a_cands:
        a_node_ids.update(c.get('node_ids', []))

    # Add Stage C groups that are novel and substantial
    for c_idx in comparison_result.get('stage_c_only', []):
        if c_idx < len(c_groups):
            group = c_groups[c_idx]
            group_nodes = set(group.get('node_ids', []))
            # Only add if: 3+ nodes AND majority not already covered
            if len(group_nodes) >= 3:
                overlap = len(group_nodes & a_node_ids)
                if len(group_nodes) > 0 and overlap / len(group_nodes) < 0.5:
                    merged.append(group)
                    a_node_ids.update(group_nodes)

    return merged


def compare_grouping_by_section(stage_a_candidates, stage_c_sections):
    """Compare Stage A and Stage C results section-by-section.

    Groups Stage A candidates by parent_id, matches them against Stage C
    sections, and decides per-section adoption using graduated merging:

    - Tier 1 (coverage >= 80%): Stage C fully adopted
    - Tier 2 (coverage >= 60%): Stage C + unmatched Stage A merged
    - Tier 3 (coverage >= 40%): Stage A + high-confidence Stage C
    - Tier 4 (coverage < 40%):  Stage A only

    Args:
        stage_a_candidates: List of Stage A grouping candidates (with parent_id field)
        stage_c_sections: List of dicts with 'section_id' and 'groups' keys

    Returns:
        Dict with per-section results and overall summary:
        {
            'sections': [
                {
                    'section_id': '2:8320',
                    'source': 'stage_c' | 'stage_a' | 'merged_c_priority' | 'merged_a_priority',
                    'coverage': 0.95,
                    'mean_jaccard': 0.82,
                    'candidates': [...]  # adopted candidates for this section
                }
            ],
            'overall_coverage': 0.88,
            'stage_a_sections': int,
            'stage_c_sections': int,
            'merged_sections': int,
            'total_sections': int
        }
    """
    if not stage_a_candidates and not stage_c_sections:
        return {
            'sections': [],
            'overall_coverage': 1.0,
            'stage_a_sections': 0,
            'stage_c_sections': 0,
            'merged_sections': 0,
            'total_sections': 0,
        }

    # Group Stage A candidates by parent_id
    a_by_parent = {}
    for c in stage_a_candidates:
        pid = c.get('parent_id') or c.get('parent')
        if pid is not None:
            a_by_parent.setdefault(pid, []).append(c)

    # Build Stage C lookup by section_id
    c_by_section = {}
    for sec in stage_c_sections:
        sid = sec.get('section_id')
        if sid is not None:
            c_by_section[sid] = sec.get('groups', [])

    # Collect all section IDs from both sides
    all_section_ids = list(dict.fromkeys(
        list(a_by_parent.keys()) + list(c_by_section.keys())
    ))

    sections = []
    for sid in all_section_ids:
        a_cands = a_by_parent.get(sid, [])
        c_groups = c_by_section.get(sid, [])

        result = compare_grouping_results(a_cands, c_groups)
        coverage = result['coverage']
        mean_jaccard = result['mean_jaccard']

        # Graduated adoption (4 tiers)
        if coverage >= STAGE_MERGE_TIER1:
            # Tier 1: High coverage -> Stage C fully adopted
            source = 'stage_c'
            candidates = c_groups
        elif coverage >= STAGE_MERGE_TIER2:
            # Tier 2: Medium coverage -> Stage C + unmatched Stage A merged
            source = 'merged_c_priority'
            candidates = _merge_stage_c_with_a_remainder(
                c_groups, a_cands, result
            )
        elif coverage >= STAGE_MERGE_TIER3:
            # Tier 3: Low coverage -> Stage A base + high-confidence Stage C
            source = 'merged_a_priority'
            candidates = _merge_stage_a_with_c_confident(
                a_cands, c_groups, result
            )
        else:
            # Tier 4: Very low coverage -> Stage A only
            source = 'stage_a'
            candidates = a_cands

        sections.append({
            'section_id': sid,
            'source': source,
            'coverage': coverage,
            'mean_jaccard': mean_jaccard,
            'candidates': candidates,
        })

    return _aggregate_section_metrics(sections)

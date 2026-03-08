"""Stage A vs Stage C matching and comparison report generation."""

from .constants import (
    COMPARE_MATCH_THRESHOLD,
    _STAGE_A_TO_C_PATTERN_MAP,
)


def _stage_a_pattern_key(candidate):
    """Derive a canonical pattern key from a Stage A candidate.

    Combines method and semantic_type (if present) for pattern mapping.
    """
    method = candidate.get('method', '')
    semantic_type = candidate.get('semantic_type', '')
    if method == 'semantic' and semantic_type:
        return f'semantic:{semantic_type}'
    # Special cases: bg-content and table are stored as method directly
    if method in ('bg-content', 'table', 'highlight', 'heading-content',
                  'tuple', 'consecutive', 'horizontal-bar'):
        return method
    return method


def _compute_jaccard_matches(a_sets, c_sets, threshold):
    """Find matched pairs between Stage A and Stage C groups by Jaccard similarity.

    For each Stage A group, finds the best-matching Stage C group. Pairs with
    Jaccard >= threshold are returned as matches.

    Args:
        a_sets: list of sets of node IDs from Stage A groups
        c_sets: list of sets of node IDs from Stage C groups
        threshold: minimum Jaccard similarity to consider a match

    Returns:
        tuple of (jaccard_by_group, matched_pairs, matched_c_indices)
        - jaccard_by_group: list of best Jaccard score per Stage A group
        - matched_pairs: list of dicts with stage_a_idx, stage_c_idx, jaccard
        - matched_c_indices: set of Stage C indices that were matched
    """
    jaccard_by_group = []
    matched_pairs = []
    matched_c_indices = set()

    for a_idx, a_set in enumerate(a_sets):
        best_jaccard = 0.0
        best_c_idx = -1
        for c_idx, c_set in enumerate(c_sets):
            if not a_set and not c_set:
                j = 1.0
            elif not a_set or not c_set:
                j = 0.0
            else:
                intersection = len(a_set & c_set)
                union = len(a_set | c_set)
                j = intersection / union if union > 0 else 0.0
            if j > best_jaccard:
                best_jaccard = j
                best_c_idx = c_idx
        jaccard_by_group.append(best_jaccard)
        if best_jaccard >= threshold and best_c_idx >= 0:
            matched_pairs.append({
                'stage_a_idx': a_idx,
                'stage_c_idx': best_c_idx,
                'jaccard': best_jaccard,
            })
            matched_c_indices.add(best_c_idx)

    return jaccard_by_group, matched_pairs, matched_c_indices


def _compute_coverage_metrics(a_sets, c_sets, matched_pairs, matched_c_indices,
                              jaccard_by_group, num_a, num_c):
    """Calculate coverage stats from Jaccard matching results.

    Args:
        a_sets: list of sets of node IDs from Stage A groups
        c_sets: list of sets of node IDs from Stage C groups
        matched_pairs: list of matched pair dicts
        matched_c_indices: set of matched Stage C indices
        jaccard_by_group: list of best Jaccard per Stage A group
        num_a: number of Stage A candidates
        num_c: number of Stage C groups

    Returns:
        tuple of (coverage, mean_jaccard, stage_a_only, stage_c_only)
    """
    # All Stage A node IDs
    all_a_nodes = set()
    for s in a_sets:
        all_a_nodes |= s

    # All Stage C node IDs
    all_c_nodes = set()
    for s in c_sets:
        all_c_nodes |= s

    # Coverage: fraction of Stage A nodes also in Stage C
    if all_a_nodes:
        coverage = len(all_a_nodes & all_c_nodes) / len(all_a_nodes)
    else:
        coverage = 1.0

    # Mean Jaccard
    mean_jaccard = (sum(jaccard_by_group) / len(jaccard_by_group)
                    if jaccard_by_group else 0.0)

    # Unmatched groups
    matched_a_indices = {p['stage_a_idx'] for p in matched_pairs}
    stage_a_only = [i for i in range(num_a) if i not in matched_a_indices]
    stage_c_only = [i for i in range(num_c) if i not in matched_c_indices]

    return coverage, mean_jaccard, stage_a_only, stage_c_only


def _build_comparison_report(stage_a_candidates, stage_c_groups, matched_pairs,
                             coverage, mean_jaccard, jaccard_by_group,
                             stage_a_only, stage_c_only):
    """Assemble the final comparison report dict.

    Computes pattern accuracy from matched pairs and builds the result.

    Args:
        stage_a_candidates: original Stage A candidate list
        stage_c_groups: original Stage C group list
        matched_pairs: list of matched pair dicts
        coverage: float coverage metric
        mean_jaccard: float mean Jaccard similarity
        jaccard_by_group: list of per-group Jaccard scores
        stage_a_only: list of unmatched Stage A indices
        stage_c_only: list of unmatched Stage C indices

    Returns:
        dict: final comparison report
    """
    # Pattern accuracy: for matched pairs, check if Stage C pattern
    # is compatible with Stage A method
    pattern_counts = {}  # pattern_key -> {'matched': int, 'total': int}
    for a_idx in range(len(stage_a_candidates)):
        a_key = _stage_a_pattern_key(stage_a_candidates[a_idx])
        if a_key not in pattern_counts:
            pattern_counts[a_key] = {'matched': 0, 'total': 0}
        pattern_counts[a_key]['total'] += 1

        # Check if this Stage A group was matched and pattern is compatible
        pair = next((p for p in matched_pairs if p['stage_a_idx'] == a_idx), None)
        if pair:
            c_pattern = stage_c_groups[pair['stage_c_idx']].get('pattern', '')
            expected = _STAGE_A_TO_C_PATTERN_MAP.get(a_key, [])
            if c_pattern in expected:
                pattern_counts[a_key]['matched'] += 1

    return {
        'coverage': coverage,
        'jaccard_by_group': jaccard_by_group,
        'mean_jaccard': mean_jaccard,
        'stage_a_only': stage_a_only,
        'stage_c_only': stage_c_only,
        'matched_pairs': matched_pairs,
        'pattern_accuracy': pattern_counts,
    }


def _aggregate_section_metrics(section_results):
    """Aggregate per-section results into overall summary metrics.

    Args:
        section_results: list of per-section result dicts with 'source', 'coverage'

    Returns:
        dict with 'sections', 'overall_coverage', 'stage_a_sections',
        'stage_c_sections', 'total_sections'
    """
    total_sections = len(section_results)
    stage_a_count = sum(1 for s in section_results if s['source'] == 'stage_a')
    stage_c_count = sum(1 for s in section_results if s['source'] == 'stage_c')
    total_coverage_sum = sum(s['coverage'] for s in section_results)
    overall_coverage = (total_coverage_sum / total_sections) if total_sections > 0 else 1.0

    return {
        'sections': section_results,
        'overall_coverage': overall_coverage,
        'stage_a_sections': stage_a_count,
        'stage_c_sections': stage_c_count,
        'total_sections': total_sections,
    }

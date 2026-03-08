"""Grouping comparison, deduplication, and validation for figma-prepare."""

from collections import defaultdict

from .constants import (
    COMPARE_MATCH_THRESHOLD,
    DIVIDER_MAX_HEIGHT,
    LOOSE_ELEMENT_MAX_HEIGHT,
    METHOD_PRIORITY,
    STAGE_A_ONLY_DETECTORS,
    STAGE_C_COVERABLE_DETECTORS,
    STAGE_C_COVERAGE_THRESHOLD,
    UNNAMED_RE,
    _STAGE_A_TO_C_PATTERN_MAP,
)
from .geometry import get_bbox


def deduplicate_candidates(candidates, root_id=''):
    """Remove duplicate/overlapping grouping candidates (Issue 7+9+22+236).

    Rules:
    - Rule 1: If same node appears in both lower and higher-priority method,
      trim the overlapping node from the lower-priority candidate.
      Only remove the candidate entirely if all its nodes are claimed (Issue 236).
    - Rule 2: If a parent node already has a semantic (non-auto-generated) name,
      skip proximity/spacing (exception: root-level parents are exempt)
    """
    # Index: node_id -> list of candidate indices
    node_to_candidates = defaultdict(list)
    for i, c in enumerate(candidates):
        for nid in c.get('node_ids', []):
            node_to_candidates[nid].append(i)

    # Rule 1: trim overlapping nodes from lower-priority candidates (Issue 236)
    nodes_to_trim = defaultdict(set)  # candidate_index -> set of node_ids to trim
    for nid, indices in node_to_candidates.items():
        if len(indices) < 2:
            continue
        methods = {i: candidates[i].get('method', '') for i in indices}
        max_priority = max(METHOD_PRIORITY.get(m, 0) for m in methods.values())
        for i, m in methods.items():
            if METHOD_PRIORITY.get(m, 0) < max_priority:
                nodes_to_trim[i].add(nid)

    # Rule 2: skip proximity/spacing candidates where parent already has semantic name
    # Exception: root-level (artboard) parents are exempt
    remove_by_rule2 = set()
    for i, c in enumerate(candidates):
        if c.get('parent_id') == root_id:
            continue  # exempt root-level candidates
        parent_name = c.get('parent_name', '')
        if parent_name and not UNNAMED_RE.match(parent_name):
            if c.get('method') in ('proximity', 'spacing'):
                remove_by_rule2.add(i)

    # Build result: apply trims and removals
    result = []
    for i, c in enumerate(candidates):
        if i in remove_by_rule2:
            continue
        if i in nodes_to_trim:
            trim_set = nodes_to_trim[i]
            original_ids = c.get('node_ids', [])
            original_names = c.get('node_names', [])
            remaining_ids = []
            remaining_names = []
            for j, nid in enumerate(original_ids):
                if nid not in trim_set:
                    remaining_ids.append(nid)
                    if j < len(original_names):
                        remaining_names.append(original_names[j])
            if not remaining_ids:
                continue  # fully subsumed by higher-priority — remove
            c = dict(c)  # shallow copy to avoid mutating original
            c['node_ids'] = remaining_ids
            if original_names:
                c['node_names'] = remaining_names
            c['count'] = len(remaining_ids)
        result.append(c)

    return result


def absorb_stage_c_dividers(groups, node_lookup=None):
    """Post-process Stage C groups: absorb single-element divider groups into
    the nearest sibling group (Issue 253).

    When Claude generates Stage C nested grouping, thin divider lines
    (VECTOR/LINE/RECTANGLE with height <= DIVIDER_MAX_HEIGHT) are often
    placed in their own single-element groups. For coding purposes, these
    should be absorbed into adjacent list-item groups so that figma-implement
    can render them as border-bottom or similar CSS.

    Algorithm (order-based — no coordinate data required):
    1. Identify divider groups by name pattern ('divider') or node type+size
    2. Absorb into the nearest preceding non-divider group (border-bottom)
    3. If no preceding group, absorb into the nearest following group
    4. Mark divider group for removal

    Groups in Stage C YAML are already sorted by Y-coordinate, so group order
    reliably indicates spatial adjacency.

    Args:
        groups: list of group dicts with 'node_ids', 'pattern', 'name'
        node_lookup: optional dict mapping node_id -> node dict (with type, bbox).
                     Used for type-based detection when name doesn't contain 'divider'.
                     If None, detection falls back to name-only.

    Returns:
        list of groups with dividers absorbed (divider groups removed)
    """
    if not groups or len(groups) < 2:
        return groups

    if node_lookup is None:
        node_lookup = {}

    # Identify divider groups
    divider_indices = []
    for i, g in enumerate(groups):
        nids = g.get('node_ids', [])
        name = g.get('name', '').lower()

        # Name-based detection: group named 'divider*' with single element
        if len(nids) == 1 and 'divider' in name:
            divider_indices.append(i)
            continue

        # Type-based detection: single LINE/VECTOR or thin RECTANGLE
        if len(nids) != 1:
            continue
        node = node_lookup.get(nids[0])
        if not node:
            continue
        bb = get_bbox(node)
        node_type = node.get('type', '')
        is_divider = (
            node_type in ('LINE', 'VECTOR')
            or (node_type == 'RECTANGLE' and bb['h'] <= DIVIDER_MAX_HEIGHT)
        ) and bb['h'] <= LOOSE_ELEMENT_MAX_HEIGHT
        if is_divider:
            divider_indices.append(i)

    if not divider_indices:
        return groups

    # Absorb each divider into nearest preceding non-divider group
    # (border-bottom semantics). Fallback to following if no preceding.
    absorbed = set()
    merge_map = {}  # divider_index -> target_index
    non_divider_indices = [i for i in range(len(groups)) if i not in divider_indices]

    for di in divider_indices:
        if not non_divider_indices:
            break
        # Find nearest preceding non-divider group
        preceding = [ni for ni in non_divider_indices if ni < di]
        following = [ni for ni in non_divider_indices if ni > di]
        if preceding:
            merge_map[di] = preceding[-1]  # closest preceding
        elif following:
            merge_map[di] = following[0]   # closest following
        absorbed.add(di)

    # Apply merges
    result_groups = list(groups)  # shallow copy
    for di, ti in merge_map.items():
        target = result_groups[ti]
        divider_nids = result_groups[di].get('node_ids', [])
        merged = dict(target)
        merged['node_ids'] = list(target.get('node_ids', [])) + divider_nids
        result_groups[ti] = merged

    # Remove absorbed divider groups
    return [g for i, g in enumerate(result_groups) if i not in absorbed]


def validate_column_consistency(groups, node_lookup):
    """Post-validate that no group mixes left and right column elements (Issue 256).

    Checks each group's node_ids: if any have x < midpoint and others x >= midpoint,
    the group is split into left and right sub-groups.

    Args:
        groups: list of group dicts with 'node_ids', 'pattern', 'name'
        node_lookup: dict mapping node_id -> node dict (with absoluteBoundingBox)

    Returns:
        list of groups with cross-column groups split into separate L/R groups
    """
    if not groups or not node_lookup:
        return groups

    # Collect all X positions to find midpoint
    all_x = []
    all_right = []
    for g in groups:
        for nid in g.get('node_ids', []):
            node = node_lookup.get(nid)
            if node and node.get('visible') != False:
                bb = get_bbox(node)
                all_x.append(bb['x'])
                all_right.append(bb['x'] + bb['w'])

    if len(all_x) < 2:
        return groups

    x_min = min(all_x)
    x_max = max(all_right)
    x_span = x_max - x_min
    if x_span <= 0:
        return groups

    midpoint = x_min + x_span / 2

    # Check if two-column layout exists
    left_count = sum(1 for xr in all_right if xr <= midpoint + x_span * 0.1)
    right_count = sum(1 for xp in all_x if xp >= midpoint - x_span * 0.1)
    if left_count < 1 or right_count < 1:
        return groups  # Not a two-column layout

    result = []
    for g in groups:
        nids = g.get('node_ids', [])
        left_nids = []
        right_nids = []
        full_nids = []

        for nid in nids:
            node = node_lookup.get(nid)
            if not node or node.get('visible') == False:
                left_nids.append(nid)  # fallback
                continue
            bb = get_bbox(node)
            right_edge = bb['x'] + bb['w']
            if bb['w'] >= x_span * 0.8:
                full_nids.append(nid)  # Full-width element
            elif right_edge <= midpoint:
                left_nids.append(nid)
            elif bb['x'] >= midpoint:
                right_nids.append(nid)
            else:
                left_nids.append(nid)  # Spanning element, assign to left

        if left_nids and right_nids:
            # Cross-column detected — split
            # Assign full-width to left group (typically dividers)
            left_group = dict(g)
            left_group['name'] = g['name'] + '-left'
            left_group['node_ids'] = left_nids + full_nids
            result.append(left_group)

            right_group = dict(g)
            right_group['name'] = g['name'] + '-right'
            right_group['node_ids'] = right_nids
            result.append(right_group)
        else:
            result.append(g)

    return result


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

    # For each Stage A group, find best-matching Stage C group by Jaccard
    jaccard_by_group = []
    matched_pairs = []
    matched_c_indices = set()
    match_threshold = COMPARE_MATCH_THRESHOLD

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
        if best_jaccard >= match_threshold and best_c_idx >= 0:
            matched_pairs.append({
                'stage_a_idx': a_idx,
                'stage_c_idx': best_c_idx,
                'jaccard': best_jaccard,
            })
            matched_c_indices.add(best_c_idx)

    # Mean Jaccard
    mean_jaccard = (sum(jaccard_by_group) / len(jaccard_by_group)
                    if jaccard_by_group else 0.0)

    # Unmatched groups
    matched_a_indices = {p['stage_a_idx'] for p in matched_pairs}
    stage_a_only = [i for i in range(len(stage_a_candidates))
                    if i not in matched_a_indices]
    stage_c_only = [i for i in range(len(stage_c_groups))
                    if i not in matched_c_indices]

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


def compare_grouping_by_section(stage_a_candidates, stage_c_sections):
    """Compare Stage A and Stage C results section-by-section.

    Groups Stage A candidates by parent_id, matches them against Stage C
    sections, and decides per-section whether to adopt Stage C or fall back
    to Stage A based on STAGE_C_COVERAGE_THRESHOLD.

    Args:
        stage_a_candidates: List of Stage A grouping candidates (with parent_id field)
        stage_c_sections: List of dicts with 'section_id' and 'groups' keys

    Returns:
        Dict with per-section results and overall summary:
        {
            'sections': [
                {
                    'section_id': '2:8320',
                    'source': 'stage_c' | 'stage_a',
                    'coverage': 0.95,
                    'mean_jaccard': 0.82,
                    'candidates': [...]  # adopted candidates for this section
                }
            ],
            'overall_coverage': 0.88,
            'stage_a_sections': int,
            'stage_c_sections': int,
            'total_sections': int
        }
    """
    if not stage_a_candidates and not stage_c_sections:
        return {
            'sections': [],
            'overall_coverage': 1.0,
            'stage_a_sections': 0,
            'stage_c_sections': 0,
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
    stage_a_count = 0
    stage_c_count = 0
    total_coverage_sum = 0.0

    for sid in all_section_ids:
        a_cands = a_by_parent.get(sid, [])
        c_groups = c_by_section.get(sid, [])

        result = compare_grouping_results(a_cands, c_groups)
        coverage = result['coverage']
        mean_jaccard = result['mean_jaccard']

        # Decision: adopt Stage C if coverage >= threshold, else fall back to Stage A
        if coverage >= STAGE_C_COVERAGE_THRESHOLD:
            source = 'stage_c'
            candidates = c_groups
            stage_c_count += 1
        else:
            source = 'stage_a'
            candidates = a_cands
            stage_a_count += 1

        total_coverage_sum += coverage

        sections.append({
            'section_id': sid,
            'source': source,
            'coverage': coverage,
            'mean_jaccard': mean_jaccard,
            'candidates': candidates,
        })

    total_sections = len(all_section_ids)
    overall_coverage = (total_coverage_sum / total_sections) if total_sections > 0 else 1.0

    return {
        'sections': sections,
        'overall_coverage': overall_coverage,
        'stage_a_sections': stage_a_count,
        'stage_c_sections': stage_c_count,
        'total_sections': total_sections,
    }

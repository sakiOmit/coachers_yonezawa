"""Deduplication and divider absorption for grouping candidates."""

from collections import defaultdict

from .constants import (
    DIVIDER_MAX_HEIGHT,
    LOOSE_ELEMENT_MAX_HEIGHT,
    METHOD_PRIORITY,
    UNNAMED_RE,
)
from .geometry import get_bbox


def _should_absorb_into_higher(lower_group, higher_group, trim_loss_ratio=0.3):
    """Decide if a lower-priority group should be absorbed into a higher-priority one.

    When trimming would remove > 30% of the lower group's nodes, it's better
    to absorb the remaining nodes into the higher-priority group rather than
    leave them as orphans.

    Only applies to small groups (<=6 nodes) as an additional safeguard.
    The caller (deduplicate_candidates) further restricts absorption to
    low-priority methods (proximity/spacing) only.

    Args:
        lower_group: The lower-priority candidate dict.
        higher_group: The higher-priority candidate dict.
        trim_loss_ratio: Threshold for triggering absorption (default 0.3 = 30%).

    Returns:
        bool: True if lower group should be absorbed (not just trimmed).
    """
    lower_ids = set(lower_group.get('node_ids', []))
    higher_ids = set(higher_group.get('node_ids', []))

    if not lower_ids:
        return False

    overlap = lower_ids & higher_ids
    remaining = lower_ids - higher_ids

    # If trimming removes > 30% of nodes AND remaining is < 3 nodes → absorb
    # But only if the original group was small enough that the remainder is
    # truly orphaned (not a fragment of a large heterogeneous group).
    loss = len(overlap) / len(lower_ids)
    if loss > trim_loss_ratio and len(remaining) < 3 and len(lower_ids) <= 6:
        return True

    return False


def deduplicate_candidates(candidates, root_id=''):
    """Remove duplicate/overlapping grouping candidates (Issue 7+9+22+236).

    Rules:
    - Rule 1: If same node appears in both lower and higher-priority method,
      trim the overlapping node from the lower-priority candidate.
      Only remove the candidate entirely if all its nodes are claimed (Issue 236).
      If trimming leaves < 3 nodes (fragmented group), absorb the remainder
      into the higher-priority group instead of leaving orphans.
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
    # First pass: compute trimmed candidates and collect absorption info
    trimmed_candidates = []  # (index, candidate_or_None, original_ids, remaining_ids)
    for i, c in enumerate(candidates):
        if i in remove_by_rule2:
            trimmed_candidates.append((i, None, set(), set()))
            continue
        if i in nodes_to_trim:
            trim_set = nodes_to_trim[i]
            original_ids = set(c.get('node_ids', []))
            original_id_list = c.get('node_ids', [])
            original_names = c.get('node_names', [])
            remaining_ids = []
            remaining_names = []
            for j, nid in enumerate(original_id_list):
                if nid not in trim_set:
                    remaining_ids.append(nid)
                    if j < len(original_names):
                        remaining_names.append(original_names[j])
            if not remaining_ids:
                trimmed_candidates.append((i, None, original_ids, set()))
                continue  # fully subsumed by higher-priority — remove
            c = dict(c)  # shallow copy to avoid mutating original
            c['node_ids'] = remaining_ids
            if original_names:
                c['node_names'] = remaining_names
            c['count'] = len(remaining_ids)
            trimmed_candidates.append((i, c, original_ids, set(remaining_ids)))
        else:
            trimmed_candidates.append((i, c, set(c.get('node_ids', [])), set(c.get('node_ids', []))))

    # Second pass: merge-aware absorption for fragmented groups
    # Build index of higher-priority candidates for absorption lookup
    absorption_targets = {}  # lower_index -> higher_candidate_index_in_trimmed
    absorbed_indices = set()
    for ti, (i, cand, original_ids, remaining_ids) in enumerate(trimmed_candidates):
        if cand is None:
            continue
        if i not in nodes_to_trim:
            continue
        # Check if remaining group is too small and should be absorbed.
        # Only for low-priority methods (proximity/spacing) which are prone
        # to fragmentation. Higher-level methods (heading-content, pattern,
        # consecutive) have intentional groupings that shouldn't be absorbed.
        method = cand.get('method', '')
        if 0 < len(remaining_ids) < 3 and method in ('proximity', 'spacing'):
            # Find which higher-priority group took our nodes
            trimmed_away = original_ids - remaining_ids
            best_higher_ti = None
            best_overlap = 0
            for hti, (hi, hcand, _, _) in enumerate(trimmed_candidates):
                if hcand is None or hti == ti:
                    continue
                higher_ids = set(hcand.get('node_ids', []))
                overlap = len(trimmed_away & higher_ids)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_higher_ti = hti

            if best_higher_ti is not None:
                # Absorb remaining nodes into the higher group
                _, hcand, h_orig, h_rem = trimmed_candidates[best_higher_ti]
                if hcand is not None:
                    hcand_copy = dict(hcand)
                    higher_node_ids = set(hcand_copy.get('node_ids', []))
                    merged_ids = higher_node_ids | remaining_ids
                    hcand_copy['node_ids'] = list(merged_ids)
                    hcand_copy['count'] = len(merged_ids)
                    trimmed_candidates[best_higher_ti] = (
                        trimmed_candidates[best_higher_ti][0],
                        hcand_copy,
                        h_orig,
                        merged_ids,
                    )
                    # Mark lower group for removal
                    trimmed_candidates[ti] = (i, None, original_ids, set())
                    absorbed_indices.add(ti)

    # Build final result
    result = []
    for ti, (i, cand, _, _) in enumerate(trimmed_candidates):
        if cand is not None:
            result.append(cand)

    return result


def _is_divider_candidate(group, node_lookup):
    """Check if a group is a single-element divider (Issue 253).

    A group is a divider candidate if it has exactly one node and either:
    - Its name contains 'divider', or
    - The node is a LINE/VECTOR, or a thin RECTANGLE (height <= DIVIDER_MAX_HEIGHT)
      with height <= LOOSE_ELEMENT_MAX_HEIGHT.

    Args:
        group: group dict with 'node_ids', 'name'
        node_lookup: dict mapping node_id -> node dict (with type, bbox)

    Returns:
        bool: True if the group is a divider candidate
    """
    nids = group.get('node_ids', [])
    if len(nids) != 1:
        return False

    name = group.get('name', '').lower()
    # Name-based detection: group named 'divider*' with single element
    if 'divider' in name:
        return True

    # Type-based detection: single LINE/VECTOR or thin RECTANGLE
    node = node_lookup.get(nids[0])
    if not node:
        return False
    bb = get_bbox(node)
    node_type = node.get('type', '')
    return (
        (node_type in ('LINE', 'VECTOR')
         or (node_type == 'RECTANGLE' and bb['h'] <= DIVIDER_MAX_HEIGHT))
        and bb['h'] <= LOOSE_ELEMENT_MAX_HEIGHT
    )


def _find_adjacent_list_item(divider_idx, non_divider_indices):
    """Find the nearest non-divider group to absorb a divider into (Issue 253).

    Prefers the nearest preceding non-divider group (border-bottom semantics).
    Falls back to the nearest following group if no preceding exists.

    Args:
        divider_idx: index of the divider group
        non_divider_indices: list of indices of non-divider groups

    Returns:
        int or None: index of the target group to absorb into, or None
    """
    if not non_divider_indices:
        return None
    # Find nearest preceding non-divider group
    preceding = [ni for ni in non_divider_indices if ni < divider_idx]
    following = [ni for ni in non_divider_indices if ni > divider_idx]
    if preceding:
        return preceding[-1]  # closest preceding
    elif following:
        return following[0]   # closest following
    return None


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
    divider_indices = [
        i for i, g in enumerate(groups)
        if _is_divider_candidate(g, node_lookup)
    ]

    if not divider_indices:
        return groups

    # Absorb each divider into nearest preceding non-divider group
    # (border-bottom semantics). Fallback to following if no preceding.
    absorbed = set()
    merge_map = {}  # divider_index -> target_index
    non_divider_indices = [i for i in range(len(groups)) if i not in divider_indices]

    for di in divider_indices:
        target = _find_adjacent_list_item(di, non_divider_indices)
        if target is not None:
            merge_map[di] = target
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

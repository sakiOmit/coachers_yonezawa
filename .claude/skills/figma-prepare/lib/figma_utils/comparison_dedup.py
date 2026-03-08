"""Deduplication and divider absorption for grouping candidates."""

from collections import defaultdict

from .constants import (
    DIVIDER_MAX_HEIGHT,
    LOOSE_ELEMENT_MAX_HEIGHT,
    METHOD_PRIORITY,
    UNNAMED_RE,
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

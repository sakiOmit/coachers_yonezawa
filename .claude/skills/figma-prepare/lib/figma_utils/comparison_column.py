"""Column consistency validation for two-column layouts (Issue 256)."""

from .geometry import get_bbox


def _compute_col_for_nodes(node_ids, node_lookup, midpoint, x_span):
    """Classify node IDs into left, right, and full-width columns (Issue 256).

    Args:
        node_ids: list of node ID strings
        node_lookup: dict mapping node_id -> node dict (with absoluteBoundingBox)
        midpoint: X midpoint of the two-column layout
        x_span: total X span of all nodes

    Returns:
        tuple of (left_nids, right_nids, full_nids)
    """
    left_nids = []
    right_nids = []
    full_nids = []

    for nid in node_ids:
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

    return left_nids, right_nids, full_nids


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
        left_nids, right_nids, full_nids = _compute_col_for_nodes(
            nids, node_lookup, midpoint, x_span
        )

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

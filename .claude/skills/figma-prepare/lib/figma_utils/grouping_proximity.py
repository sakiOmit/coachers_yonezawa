"""Proximity-based grouping detection for figma-prepare Phase 2.

Contains UnionFind data structure and proximity/spatial-gap splitting logic.
Extracted from grouping_engine.py for modularity.
"""

import statistics
from collections import defaultdict

from .constants import (
    GRID_SNAP,
    PROXIMITY_GAP,
    REPEATED_PATTERN_MIN,
    ROW_TOLERANCE,
    SPATIAL_GAP_THRESHOLD,
    SPATIAL_SPLIT_MIN_NON_LEAF,
)
from .geometry import get_bbox, snap
from .scoring import compute_grouping_score

__all__ = [
    "UnionFind",
    "compute_adaptive_gap",
    "detect_proximity_groups",
]


# ---------------------------------------------------------------------------
# UnionFind (proximity grouping helper)
# ---------------------------------------------------------------------------

class UnionFind:
    """Weighted quick-union with path compression."""

    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py:
            return
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1

    def groups(self):
        groups = defaultdict(list)
        for i in range(len(self.parent)):
            groups[self.find(i)].append(i)
        return {k: v for k, v in groups.items() if len(v) >= 2}


# ---------------------------------------------------------------------------
# Adaptive proximity gap
# ---------------------------------------------------------------------------

def compute_adaptive_gap(children, default_gap=None):
    """Compute adaptive proximity gap based on actual inter-sibling spacing.

    Instead of using a fixed 24px gap for all designs, analyze the actual
    spacing between sibling elements and use median * 0.8 as the gap threshold.

    Args:
        children: List of visible sibling nodes with absoluteBoundingBox.
        default_gap: Fallback gap if spacing can't be computed.
                     Defaults to PROXIMITY_GAP constant.

    Returns:
        int: Adaptive gap value in pixels (snapped to GRID_SNAP).
    """
    if default_gap is None:
        default_gap = PROXIMITY_GAP

    if len(children) < 3:
        return default_gap

    bboxes = [get_bbox(c) for c in children]

    # Sort by Y position first (most layouts are vertical at section level)
    sorted_bbs = sorted(bboxes, key=lambda b: (b['y'], b['x']))

    gaps = []
    for i in range(len(sorted_bbs) - 1):
        a = sorted_bbs[i]
        b = sorted_bbs[i + 1]
        # Vertical gap
        v_gap = b['y'] - (a['y'] + a['h'])
        if v_gap > 0:
            gaps.append(v_gap)
        # Horizontal gap (for horizontal layouts)
        h_gap = b['x'] - (a['x'] + a['w'])
        if h_gap > 0:
            gaps.append(h_gap)

    if len(gaps) < 2:
        return default_gap

    # Use median * 0.8 (conservative: slightly smaller than typical gap)
    median_gap = statistics.median(gaps)

    # Don't go below 8px or above 200px
    adaptive = max(8, min(200, int(median_gap * 0.8)))

    # Snap to GRID_SNAP
    adaptive = snap(adaptive, GRID_SNAP)

    return adaptive


# ---------------------------------------------------------------------------
# Proximity detector
# ---------------------------------------------------------------------------

def detect_proximity_groups(children, gap=None):
    """Detect groups of nearby elements using Union-Find with scoring.

    Args:
        children: List of visible sibling nodes.
        gap: Proximity gap threshold in px. If None, uses adaptive computation.
    """
    n = len(children)
    if n < 2:
        return []

    if gap is None:
        gap = compute_adaptive_gap(children)

    bboxes = [get_bbox(c) for c in children]
    uf = UnionFind(n)
    for i in range(n):
        for j in range(i + 1, n):
            score = compute_grouping_score(bboxes[i], bboxes[j], gap)
            if score > 0.5:
                uf.union(i, j)

    # Pre-compute all pairwise scores for group score calculation
    pairwise_scores = {}
    for i in range(n):
        for j in range(i + 1, n):
            pairwise_scores[(i, j)] = compute_grouping_score(bboxes[i], bboxes[j], gap)

    result = []
    # Issue 127: Use sequential counter instead of UF internal root index
    for group_idx, (root, indices) in enumerate(uf.groups().items(), 1):
        if len(indices) >= 2:
            group_nodes = [children[i] for i in indices]
            # Compute group score as mean of pairwise scores within the group
            group_scores = []
            for a in range(len(indices)):
                for b in range(a + 1, len(indices)):
                    key = (min(indices[a], indices[b]), max(indices[a], indices[b]))
                    group_scores.append(pairwise_scores.get(key, 0.0))
            mean_score = sum(group_scores) / len(group_scores) if group_scores else 0.0
            result.append({
                'method': 'proximity',
                'score': round(mean_score, 4),
                'node_ids': [n.get('id', '') for n in group_nodes],
                'node_names': [n.get('name', '') for n in group_nodes],
                'count': len(indices),
                'suggested_name': f'group-{group_idx}',
            })
    return result


def _split_by_spatial_gap(nodes, gap_threshold=SPATIAL_GAP_THRESHOLD):
    """Split a group of nodes into sub-groups by large spatial gaps (Issue 87, 88).

    Sorts by primary axis (Y for vertical spread, X for horizontal) and
    splits where consecutive gap exceeds threshold.

    For leaf nodes: always attempt splitting (Issue 87).
    For non-leaf nodes: only split if group is large (6+) to catch
    multi-section card grids (Issue 88).
    """
    if len(nodes) <= REPEATED_PATTERN_MIN:
        return [nodes]
    all_leaf = all(len(n.get('children', [])) == 0 for n in nodes)
    # Issue 88/206: Non-leaf elements are often structurally cohesive (e.g. a
    # few card frames belonging to one section). With 5 or fewer non-leaf nodes,
    # splitting risks breaking a single logical group. At 6+ nodes, different
    # sections' card groups may have been merged, so spatial-gap splitting
    # becomes worthwhile to separate them.
    if not all_leaf and len(nodes) < SPATIAL_SPLIT_MIN_NON_LEAF:
        return [nodes]

    bboxes = [get_bbox(n) for n in nodes]
    # Determine primary axis for splitting
    # For grid-like layouts (multiple rows of items), use Y to split by rows
    xs = [b['x'] for b in bboxes]
    ys = [b['y'] for b in bboxes]

    # Detect rows by Y coordinate (Issue 88: grid-aware splitting)
    # Issue 131: Use shared ROW_TOLERANCE constant
    y_rows = set(round(y / ROW_TOLERANCE) for y in ys)
    is_grid = len(y_rows) >= 2  # multiple Y rows → grid layout

    if is_grid:
        # Grid: sort by Y (row), then X within row → split by row gaps
        sorted_pairs = sorted(zip(bboxes, nodes), key=lambda p: (round(p[0]['y'] / ROW_TOLERANCE), p[0]['x']))

        def gap_fn(a, b):
            # Only count gap when moving to a new row
            if round(a['y'] / ROW_TOLERANCE) == round(b['y'] / ROW_TOLERANCE):
                return 0  # same row
            return b['y'] - (a['y'] + a['h'])
    else:
        x_range = max(xs) - min(xs) if xs else 0
        y_range = max(ys) - min(ys) if ys else 0
        if y_range >= x_range:
            sorted_pairs = sorted(zip(bboxes, nodes), key=lambda p: p[0]['y'])

            def gap_fn(a, b):
                return b['y'] - (a['y'] + a['h'])
        else:
            sorted_pairs = sorted(zip(bboxes, nodes), key=lambda p: p[0]['x'])

            def gap_fn(a, b):
                return b['x'] - (a['x'] + a['w'])

    groups = [[sorted_pairs[0][1]]]
    for i in range(1, len(sorted_pairs)):
        g = gap_fn(sorted_pairs[i - 1][0], sorted_pairs[i][0])
        if g > gap_threshold:
            groups.append([])
        groups[-1].append(sorted_pairs[i][1])
    return groups

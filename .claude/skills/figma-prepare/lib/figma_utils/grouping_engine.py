"""Grouping candidate detection engine for figma-prepare Phase 2.

Extracted from detect-grouping-candidates.sh (Issue: shell-to-python extraction).
All functions previously embedded in the shell heredoc now live here.

Public entry point: ``detect_grouping_candidates()``

Submodules (extracted for modularity):
  grouping_proximity  - UnionFind, proximity detection, spatial-gap splitting
  grouping_semantic   - Card/navigation/grid detection
  grouping_zones      - Header/footer and vertical zone detection
  grouping_walker     - Tree walking and node protection
"""

import json
import sys

from .constants import (
    JACCARD_THRESHOLD,
    REPEATED_PATTERN_MIN,
    STAGE_A_ONLY_DETECTORS,
)
from .comparison import deduplicate_candidates
from .detection import find_absorbable_elements
from .geometry import resolve_absolute_coords, yaml_str
from .metadata import get_root_node, load_metadata
from .scoring import structure_hash, structure_similarity

# Re-export from submodules for backward compatibility
from .grouping_proximity import (  # noqa: F401
    UnionFind,
    _split_by_spatial_gap,
    compute_adaptive_gap,
    detect_proximity_groups,
)
from .grouping_semantic import (  # noqa: F401
    detect_semantic_groups,
    detect_variant_groups,
    is_card_like,
    is_grid_like,
    is_navigation_like,
)
from .grouping_zones import (  # noqa: F401
    detect_header_footer_groups,
    detect_vertical_zone_groups,
    infer_zone_semantic_name,
)
from .grouping_walker import (  # noqa: F401
    _is_protected_node,
    walk_and_detect,
)

__all__ = [
    "ALL_DETECTOR_METHODS",
    "UnionFind",
    "compute_adaptive_gap",
    "detect_grouping_candidates",
    "detect_header_footer_groups",
    "detect_pattern_groups",
    "detect_proximity_groups",
    "detect_semantic_groups",
    "detect_spacing_groups",
    "detect_variant_groups",
    "detect_vertical_zone_groups",
    "infer_zone_semantic_name",
    "is_card_like",
    "is_grid_like",
    "is_navigation_like",
    "walk_and_detect",
]


# ---------------------------------------------------------------------------
# Pattern / spacing detectors (remain here as entry-point-adjacent logic)
# ---------------------------------------------------------------------------

def detect_pattern_groups(children):
    """Detect repeated patterns using fuzzy structure hash matching."""
    hashes = [(structure_hash(c), c) for c in children]

    # Greedy clustering by Jaccard similarity
    clusters = []  # list of (representative_hash, [nodes], [similarities])
    for h, child in hashes:
        matched = False
        for cluster in clusters:
            sim = structure_similarity(cluster[0], h)
            if sim >= JACCARD_THRESHOLD:
                cluster[1].append(child)
                cluster[2].append(sim)
                matched = True
                break
        if not matched:
            clusters.append((h, [child], []))

    result = []
    for rep_hash, nodes, similarities in clusters:
        if len(nodes) >= REPEATED_PATTERN_MIN:
            # Compute pattern score as min Jaccard similarity within cluster
            # First node has implicit similarity 1.0 with itself
            min_jaccard = min(similarities) if similarities else 1.0
            # Issue 87: For leaf nodes (no children), split by spatial proximity
            # to avoid grouping distant TEXT elements (e.g. nav labels + content text)
            sub_groups = _split_by_spatial_gap(nodes)
            for sg in sub_groups:
                if len(sg) < REPEATED_PATTERN_MIN:
                    continue
                node_hashes = set(structure_hash(n) for n in sg)
                is_fuzzy = len(node_hashes) > 1
                result.append({
                    'method': 'pattern',
                    'score': round(min_jaccard, 4),
                    'structure_hash': rep_hash,
                    'node_ids': [n.get('id', '') for n in sg],
                    'node_names': [n.get('name', '') for n in sg],
                    'count': len(sg),
                    'suggested_name': 'list-items',
                    'suggested_wrapper': 'list-container',
                    'fuzzy_match': is_fuzzy,
                })
    return result


def detect_spacing_groups(children):
    """Detect groups of regularly-spaced elements."""
    import statistics as _stats

    from .scoring import detect_regular_spacing

    if len(children) < 3:
        return []

    from .geometry import get_bbox
    bboxes = [get_bbox(c) for c in children]
    if not detect_regular_spacing(bboxes):
        return []

    # Compute spacing score as max(0, 1.0 - cv)
    # Replicate axis detection from detect_regular_spacing
    xs = [b['x'] for b in bboxes]
    ys = [b['y'] for b in bboxes]
    x_range = max(xs) - min(xs) if xs else 0
    y_range = max(ys) - min(ys) if ys else 0
    axis = 'x' if x_range > y_range else 'y'
    if axis == 'x':
        sorted_bb = sorted(bboxes, key=lambda b: b['x'])
        gaps = [sorted_bb[i+1]['x'] - (sorted_bb[i]['x'] + sorted_bb[i]['w'])
                for i in range(len(sorted_bb) - 1)]
    else:
        sorted_bb = sorted(bboxes, key=lambda b: b['y'])
        gaps = [sorted_bb[i+1]['y'] - (sorted_bb[i]['y'] + sorted_bb[i]['h'])
                for i in range(len(sorted_bb) - 1)]
    gaps = [g for g in gaps if g >= 0]
    if len(gaps) >= 2:
        mean_gap = _stats.mean(gaps)
        if mean_gap > 0:
            cv = _stats.stdev(gaps) / mean_gap
            spacing_score = max(0.0, 1.0 - cv)
        else:
            spacing_score = 1.0  # Perfect edge-to-edge
    else:
        spacing_score = 1.0  # Single gap or no gaps = perfectly regular

    return [{
        'method': 'spacing',
        'score': round(spacing_score, 4),
        'node_ids': [c.get('id', '') for c in children],
        'node_names': [c.get('name', '') for c in children],
        'count': len(children),
        'suggested_name': 'list-regular',
        'suggested_wrapper': 'list-container',
    }]


# ---------------------------------------------------------------------------
# YAML output helpers
# ---------------------------------------------------------------------------

def _write_yaml_output(candidates, output_file, root_skipped=0, disabled=None):
    """Write grouping plan YAML file."""
    with open(output_file, 'w') as f:
        f.write('# Figma Grouping Plan\n')
        f.write(f'# Total candidates: {len(candidates)}\n')
        if root_skipped:
            f.write(f'# Root-level candidates skipped: {root_skipped}\n')
        f.write('# Generated by /figma-prepare Phase 2\n')
        f.write('# Review before applying with --apply\n\n')
        f.write('candidates:\n')
        for i, c in enumerate(candidates):
            f.write(f'  - index: {i}\n')
            f.write(f'    method: {yaml_str(c["method"])}\n')
            if 'score' in c:
                f.write(f'    score: {c["score"]}\n')
            f.write(f'    parent: {yaml_str(c.get("parent_name", ""))}\n')
            if 'node_ids' in c:
                f.write(f'    node_ids: {json.dumps(c["node_ids"])}\n')
                f.write(f'    count: {c["count"]}\n')
            if 'suggested_name' in c:
                f.write(f'    suggested_name: {yaml_str(c["suggested_name"])}\n')
            if 'structure_hash' in c:
                f.write(f'    structure_hash: {yaml_str(c["structure_hash"])}\n')
            if 'suggested_wrapper' in c:
                f.write(f'    suggested_wrapper: {yaml_str(c["suggested_wrapper"])}\n')
            if c.get('fuzzy_match'):
                f.write('    fuzzy_match: true\n')
            if 'semantic_type' in c:
                f.write(f'    semantic_type: {yaml_str(c["semantic_type"])}\n')
            if 'bg_node_ids' in c:
                f.write(f'    bg_node_ids: {json.dumps(c["bg_node_ids"])}\n')
            if 'row_count' in c:
                f.write(f'    row_count: {c["row_count"]}\n')
            if 'tuple_size' in c:
                f.write(f'    tuple_size: {c["tuple_size"]}\n')
            if 'repetitions' in c:
                f.write(f'    repetitions: {c["repetitions"]}\n')


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

ALL_DETECTOR_METHODS = {
    'proximity', 'pattern', 'spacing', 'semantic', 'zone', 'tuple',
    'consecutive', 'heading-content', 'highlight', 'bg-content',
    'table', 'horizontal-bar', 'header-footer',
}


def detect_grouping_candidates(metadata_path, output_file='', skip_root='', disable_detectors=''):
    """Run full grouping candidate detection pipeline.

    This is the main entry point, replacing the inline Python in the shell script.

    Args:
        metadata_path: Path to Figma metadata JSON file.
        output_file: If non-empty, write YAML output to this path.
        skip_root: If truthy string, filter out root-level candidates.
        disable_detectors: Comma-separated list of detector names to disable.

    Returns:
        dict: Result JSON with 'total', 'candidates' (or 'output'), 'status'.
    """
    # Parse disabled detectors
    disabled = set(d.strip() for d in disable_detectors.split(',') if d.strip()) if disable_detectors else set()

    # Validate detector names
    unknown = disabled - ALL_DETECTOR_METHODS
    if unknown:
        print(json.dumps({'warning': f'Unknown detector names ignored: {sorted(unknown)}'}), file=sys.stderr)
        disabled = disabled & ALL_DETECTOR_METHODS

    # Guard Stage A-only detectors from being disabled
    forced_a = disabled & STAGE_A_ONLY_DETECTORS
    if forced_a:
        print(json.dumps({'warning': f'Stage A-only detectors cannot be disabled: {sorted(forced_a)}. Ignoring.'}), file=sys.stderr)
        disabled = disabled - STAGE_A_ONLY_DETECTORS

    data = load_metadata(metadata_path)
    root = get_root_node(data)
    resolve_absolute_coords(root)
    candidates = walk_and_detect(root, disabled=disabled)
    candidates = deduplicate_candidates(candidates, root_id=root.get('id', ''))

    # Issue 167: Absorb loose elements into nearest existing group (post-dedup)
    root_children = root.get('children', [])
    if root_children and candidates:
        # Build set of indices already in root-level groups
        root_id_str = root.get('id', '')
        child_id_to_idx = {ch.get('id', ''): idx for idx, ch in enumerate(root_children)}
        grouped_indices = set()
        root_candidates = [c for c in candidates if c.get('parent_id') == root_id_str]
        for cand in root_candidates:
            for nid in cand.get('node_ids', []):
                if nid in child_id_to_idx:
                    grouped_indices.add(child_id_to_idx[nid])

        absorptions = find_absorbable_elements(root_children, grouped_indices, candidate_groups=root_candidates)
        for ab in absorptions:
            elem = root_children[ab['element_idx']]
            elem_id = elem.get('id', '')
            # Find which candidate contains the target group member
            target_child = root_children[ab['target_group_idx']]
            target_id = target_child.get('id', '')
            for cand in root_candidates:
                if target_id in cand.get('node_ids', []):
                    cand['node_ids'].append(elem_id)
                    cand['count'] = len(cand['node_ids'])
                    break

    # Issue 178: Filter out root-level candidates when --skip-root is set
    root_skipped = 0
    if skip_root:
        root_name = root.get('name', '')
        before_count = len(candidates)
        candidates = [c for c in candidates if c.get('parent_name', '') != root_name]
        root_skipped = before_count - len(candidates)

    if output_file:
        _write_yaml_output(candidates, output_file, root_skipped, disabled)
        result = {
            'total': len(candidates),
            'output': output_file,
            'status': 'dry-run',
        }
        if root_skipped:
            result['root_skipped'] = root_skipped
        if disabled:
            result['disabled_detectors'] = sorted(disabled)
        return result
    else:
        result = {
            'total': len(candidates),
            'candidates': candidates,
            'status': 'dry-run',
        }
        if root_skipped:
            result['root_skipped'] = root_skipped
        if disabled:
            result['disabled_detectors'] = sorted(disabled)
        return result

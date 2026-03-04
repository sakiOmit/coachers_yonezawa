#!/usr/bin/env bash
# Phase 2: Detect Grouping Candidates
#
# Usage: bash detect-grouping-candidates.sh <metadata.json> [--output grouping-plan.yaml]
# Input: Figma get_metadata output (JSON)
# Output: JSON/YAML with grouping candidates
# Exit: 0=success, 1=error

set -euo pipefail

if [[ $# -lt 1 ]] || [[ ! -f "$1" ]]; then
  echo '{"error": "Usage: detect-grouping-candidates.sh <metadata.json> [--output file.yaml]"}' >&2
  exit 1
fi

OUTPUT_FILE=""
if [[ "${2:-}" == "--output" ]] && [[ -n "${3:-}" ]]; then
  OUTPUT_FILE="$3"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 -c "
import json, sys, os
from collections import defaultdict
sys.setrecursionlimit(3000)  # Guard against deeply nested Figma files (Issue 48)
sys.path.insert(0, os.path.join(sys.argv[1], 'lib'))
from figma_utils import (resolve_absolute_coords, get_bbox, get_root_node, UNNAMED_RE, yaml_str,
    compute_grouping_score, structure_similarity, detect_regular_spacing)

PROXIMITY_GAP = 24  # px
REPEATED_PATTERN_MIN = 3
JACCARD_THRESHOLD = 0.7

def structure_hash(node):
    \"\"\"Calculate structure hash from child types and count.\"\"\"
    children = node.get('children', [])
    if not children:
        return node.get('type', 'UNKNOWN')
    child_types = sorted(c.get('type', '') for c in children)
    return f\"{node.get('type', '')}:[{','.join(child_types)}]\"

class UnionFind:
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

def detect_proximity_groups(children):
    \"\"\"Detect groups of nearby elements using Union-Find with scoring.\"\"\"
    n = len(children)
    if n < 2:
        return []

    bboxes = [get_bbox(c) for c in children]
    uf = UnionFind(n)
    for i in range(n):
        for j in range(i + 1, n):
            score = compute_grouping_score(bboxes[i], bboxes[j], PROXIMITY_GAP)
            if score > 0.5:
                uf.union(i, j)

    result = []
    for root, indices in uf.groups().items():
        if len(indices) >= 2:
            group_nodes = [children[i] for i in indices]
            result.append({
                'method': 'proximity',
                'node_ids': [n.get('id', '') for n in group_nodes],
                'node_names': [n.get('name', '') for n in group_nodes],
                'count': len(indices),
                'suggested_name': f'group-proximity-{root}',
            })
    return result

def detect_pattern_groups(children):
    \"\"\"Detect repeated patterns using fuzzy structure hash matching.\"\"\"
    hashes = [(structure_hash(c), c) for c in children]

    # Greedy clustering by Jaccard similarity
    clusters = []  # list of (representative_hash, [nodes])
    for h, child in hashes:
        matched = False
        for cluster in clusters:
            if structure_similarity(cluster[0], h) >= JACCARD_THRESHOLD:
                cluster[1].append(child)
                matched = True
                break
        if not matched:
            clusters.append((h, [child]))

    result = []
    for rep_hash, nodes in clusters:
        if len(nodes) >= REPEATED_PATTERN_MIN:
            # Check if all hashes are identical (exact match) or fuzzy
            node_hashes = set(structure_hash(n) for n in nodes)
            is_fuzzy = len(node_hashes) > 1
            result.append({
                'method': 'pattern',
                'structure_hash': rep_hash,
                'node_ids': [n.get('id', '') for n in nodes],
                'node_names': [n.get('name', '') for n in nodes],
                'count': len(nodes),
                'suggested_name': 'list-items',
                'suggested_wrapper': 'list-container',
                'fuzzy_match': is_fuzzy,
            })
    return result

def detect_spacing_groups(children):
    \"\"\"Detect groups of regularly-spaced elements.\"\"\"
    if len(children) < 3:
        return []

    bboxes = [get_bbox(c) for c in children]
    if not detect_regular_spacing(bboxes):
        return []

    return [{
        'method': 'spacing',
        'node_ids': [c.get('id', '') for c in children],
        'node_names': [c.get('name', '') for c in children],
        'count': len(children),
        'suggested_name': 'list-regular',
        'suggested_wrapper': 'list-container',
    }]

def is_card_like(node):
    \"\"\"Detect card-like structure: FRAME/COMPONENT/INSTANCE with 2-6 children including IMAGE+TEXT.\"\"\"
    if node.get('type') not in ('FRAME', 'COMPONENT', 'INSTANCE'):
        return False
    children = node.get('children', [])
    if not (2 <= len(children) <= 6):
        return False
    types = [c.get('type', '') for c in children]
    has_image = 'RECTANGLE' in types or 'IMAGE' in types
    has_text = 'TEXT' in types
    # Also check one level down for text
    if not has_text:
        for c in children:
            if c.get('type') in ('FRAME', 'GROUP'):
                sub_types = [sc.get('type', '') for sc in c.get('children', [])]
                if 'TEXT' in sub_types:
                    has_text = True
                    break
    return has_image and has_text

def is_navigation_like(children):
    \"\"\"Detect navigation-like pattern: 4+ horizontal text-sized elements.\"\"\"
    if len(children) < 4:
        return False
    bboxes = [get_bbox(c) for c in children]
    xs = [b['x'] for b in bboxes]
    ys = [b['y'] for b in bboxes]
    x_range = max(xs) - min(xs) if xs else 0
    y_range = max(ys) - min(ys) if ys else 0
    if x_range <= y_range:
        return False  # not horizontal
    # Check all elements are narrow (text-like)
    return all(b['w'] < 200 for b in bboxes)

def is_grid_like(children):
    \"\"\"Detect grid-like pattern: 2+ rows x 2+ columns of similar-sized elements.\"\"\"
    if len(children) < 4:
        return False
    bboxes = [get_bbox(c) for c in children]

    # Group by Y position (row detection)
    row_tolerance = 20
    rows = defaultdict(list)
    for b in bboxes:
        row_key = round(b['y'] / row_tolerance)
        rows[row_key].append(b)

    if len(rows) < 2:
        return False

    # Check each row has 2+ elements
    if not all(len(r) >= 2 for r in rows.values()):
        return False

    # Check size similarity (20% threshold)
    widths = [b['w'] for b in bboxes]
    heights = [b['h'] for b in bboxes]
    if max(widths) <= 0 or max(heights) <= 0:
        return False
    w_ratio = (max(widths) - min(widths)) / max(widths)
    h_ratio = (max(heights) - min(heights)) / max(heights)
    return w_ratio <= 0.20 and h_ratio <= 0.20

def detect_semantic_groups(children):
    \"\"\"Structural semantic detection (fills-independent, Issue 29/30 safe).\"\"\"
    result = []

    # Card detection: find 3+ card-like siblings
    cards = [c for c in children if is_card_like(c)]
    if len(cards) >= 3:
        result.append({
            'method': 'semantic',
            'semantic_type': 'card-list',
            'node_ids': [c.get('id', '') for c in cards],
            'node_names': [c.get('name', '') for c in cards],
            'count': len(cards),
            'suggested_name': 'card-list',
            'suggested_wrapper': 'card-container',
        })

    # Navigation detection
    if is_navigation_like(children):
        result.append({
            'method': 'semantic',
            'semantic_type': 'navigation',
            'node_ids': [c.get('id', '') for c in children],
            'node_names': [c.get('name', '') for c in children],
            'count': len(children),
            'suggested_name': 'nav-items',
            'suggested_wrapper': 'nav-container',
        })

    # Grid detection
    if is_grid_like(children):
        result.append({
            'method': 'semantic',
            'semantic_type': 'grid',
            'node_ids': [c.get('id', '') for c in children],
            'node_names': [c.get('name', '') for c in children],
            'count': len(children),
            'suggested_name': 'grid-items',
            'suggested_wrapper': 'grid-container',
        })

    return result

def walk_and_detect(node, all_candidates=None):
    \"\"\"Walk tree and detect grouping candidates at each level.\"\"\"
    if all_candidates is None:
        all_candidates = []

    children = node.get('children', [])
    if not children:
        return all_candidates

    parent_id = node.get('id', '')
    parent_name = node.get('name', '')

    # Detect at this level (all Stage A methods)
    semantic = detect_semantic_groups(children)
    patterns = detect_pattern_groups(children)
    spacing = detect_spacing_groups(children)
    proximity = detect_proximity_groups(children)

    for g in semantic + patterns + spacing + proximity:
        g['parent_id'] = parent_id
        g['parent_name'] = parent_name
        all_candidates.append(g)

    # Recurse
    for child in children:
        walk_and_detect(child, all_candidates)

    return all_candidates

# Method priority for deduplication: higher = better quality
METHOD_PRIORITY = {'semantic': 3, 'pattern': 2, 'spacing': 1, 'proximity': 0}

def deduplicate_candidates(candidates, root_id=''):
    \"\"\"Remove duplicate/overlapping grouping candidates (Issue 7+9+22).

    Rules:
    - If same node_ids appear in both lower and higher-quality method, keep higher-quality
    - If a parent node already has a semantic (non-auto-generated) name, skip proximity
      (exception: root-level parents are exempt)
    - Merge candidates that share >50% of their node_ids
    \"\"\"
    # Index: node_id -> list of candidate indices
    node_to_candidates = defaultdict(list)
    for i, c in enumerate(candidates):
        for nid in c.get('node_ids', []):
            node_to_candidates[nid].append(i)

    # Mark candidates for removal
    remove = set()

    # Rule 1: higher-quality methods > lower-quality when same nodes overlap
    for nid, indices in node_to_candidates.items():
        if len(indices) < 2:
            continue
        methods = {i: candidates[i].get('method', '') for i in indices}
        max_priority = max(METHOD_PRIORITY.get(m, 0) for m in methods.values())
        for i, m in methods.items():
            if METHOD_PRIORITY.get(m, 0) < max_priority:
                remove.add(i)

    # Rule 2: skip proximity/spacing candidates where parent already has semantic name
    # Exception: root-level (artboard) parents are exempt
    for i, c in enumerate(candidates):
        if c.get('parent_id') == root_id:
            continue  # exempt root-level candidates
        parent_name = c.get('parent_name', '')
        if parent_name and not UNNAMED_RE.match(parent_name):
            if c.get('method') in ('proximity', 'spacing'):
                remove.add(i)

    return [c for i, c in enumerate(candidates) if i not in remove]

try:
    with open(sys.argv[2], 'r') as f:
        data = json.load(f)

    root = get_root_node(data)
    resolve_absolute_coords(root)
    candidates = walk_and_detect(root)
    candidates = deduplicate_candidates(candidates, root_id=root.get('id', ''))

    output_file = sys.argv[3] if len(sys.argv) > 3 else ''

    if output_file:
        with open(output_file, 'w') as f:
            f.write('# Figma Grouping Plan\\n')
            f.write(f'# Total candidates: {len(candidates)}\\n')
            f.write('# Generated by /figma-prepare Phase 2\\n')
            f.write('# Review before applying with --apply\\n\\n')
            f.write('candidates:\\n')
            for i, c in enumerate(candidates):
                f.write(f'  - index: {i}\\n')
                f.write(f'    method: {yaml_str(c[\"method\"])}\\n')
                f.write(f'    parent: {yaml_str(c.get(\"parent_name\", \"\"))}\\n')
                if 'node_ids' in c:
                    f.write(f'    node_ids: {json.dumps(c[\"node_ids\"])}\\n')
                    f.write(f'    count: {c[\"count\"]}\\n')
                if 'suggested_name' in c:
                    f.write(f'    suggested_name: {yaml_str(c[\"suggested_name\"])}\\n')
                if 'structure_hash' in c:
                    f.write(f'    structure_hash: {yaml_str(c[\"structure_hash\"])}\\n')
                if 'suggested_wrapper' in c:
                    f.write(f'    suggested_wrapper: {yaml_str(c[\"suggested_wrapper\"])}\\n')
                if c.get('fuzzy_match'):
                    f.write(f'    fuzzy_match: true\\n')
                if 'semantic_type' in c:
                    f.write(f'    semantic_type: {yaml_str(c[\"semantic_type\"])}\\n')
        print(json.dumps({
            'total': len(candidates),
            'output': output_file,
            'status': 'dry-run'
        }, indent=2))
    else:
        print(json.dumps({
            'total': len(candidates),
            'candidates': candidates,
            'status': 'dry-run'
        }, indent=2, ensure_ascii=False))

except Exception as e:
    print(json.dumps({'error': str(e)}), file=sys.stderr)
    sys.exit(1)
" "${SCRIPT_DIR}/.." "$1" "$OUTPUT_FILE"

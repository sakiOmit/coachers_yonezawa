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
import json, sys, math, os
from collections import defaultdict
sys.path.insert(0, os.path.join(sys.argv[1], 'lib'))
from figma_utils import resolve_absolute_coords, get_bbox, get_root_node, UNNAMED_RE, yaml_str

PROXIMITY_GAP = 24  # px
REPEATED_PATTERN_MIN = 3

def distance_between(a, b):
    \"\"\"Calculate minimum distance between two bounding boxes.\"\"\"
    a_bb = get_bbox(a)
    b_bb = get_bbox(b)

    # Horizontal distance
    if a_bb['x'] + a_bb['w'] < b_bb['x']:
        dx = b_bb['x'] - (a_bb['x'] + a_bb['w'])
    elif b_bb['x'] + b_bb['w'] < a_bb['x']:
        dx = a_bb['x'] - (b_bb['x'] + b_bb['w'])
    else:
        dx = 0

    # Vertical distance
    if a_bb['y'] + a_bb['h'] < b_bb['y']:
        dy = b_bb['y'] - (a_bb['y'] + a_bb['h'])
    elif b_bb['y'] + b_bb['h'] < a_bb['y']:
        dy = a_bb['y'] - (b_bb['y'] + b_bb['h'])
    else:
        dy = 0

    return math.sqrt(dx * dx + dy * dy)

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
    \"\"\"Detect groups of nearby elements using Union-Find.\"\"\"
    n = len(children)
    if n < 2:
        return []

    uf = UnionFind(n)
    for i in range(n):
        for j in range(i + 1, n):
            dist = distance_between(children[i], children[j])
            if dist <= PROXIMITY_GAP:
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
    \"\"\"Detect repeated patterns (same structure hash).\"\"\"
    hash_map = defaultdict(list)
    for child in children:
        h = structure_hash(child)
        hash_map[h].append(child)

    result = []
    for h, nodes in hash_map.items():
        if len(nodes) >= REPEATED_PATTERN_MIN:
            result.append({
                'method': 'pattern',
                'structure_hash': h,
                'node_ids': [n.get('id', '') for n in nodes],
                'node_names': [n.get('name', '') for n in nodes],
                'count': len(nodes),
                'suggested_name': 'list-items',
                'suggested_wrapper': 'list-container',
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

    # Detect at this level (proximity + pattern only; semantic understanding delegated to Stage B)
    proximity = detect_proximity_groups(children)
    patterns = detect_pattern_groups(children)

    for g in proximity + patterns:
        g['parent_id'] = parent_id
        g['parent_name'] = parent_name
        all_candidates.append(g)

    # Recurse
    for child in children:
        walk_and_detect(child, all_candidates)

    return all_candidates

def deduplicate_candidates(candidates, root_id=''):
    \"\"\"Remove duplicate/overlapping grouping candidates (Issue 7+9+22).

    Rules:
    - If same node_ids appear in both proximity and higher-quality method, keep higher-quality
    - If a parent node already has a semantic (non-auto-generated) name, skip proximity
      (exception: root-level parents are exempt)
    - Merge candidates that share >50% of their node_ids
    \"\"\"
    # Index: node_id → list of candidate indices
    node_to_candidates = defaultdict(list)
    for i, c in enumerate(candidates):
        for nid in c.get('node_ids', []):
            node_to_candidates[nid].append(i)

    # Mark candidates for removal
    remove = set()

    # Rule 1: higher-quality methods > proximity when same nodes overlap
    PRIORITY_METHODS = {'pattern'}
    for nid, indices in node_to_candidates.items():
        if len(indices) < 2:
            continue
        methods = {i: candidates[i].get('method', '') for i in indices}
        has_priority = any(m in PRIORITY_METHODS for m in methods.values())
        if has_priority:
            for i, m in methods.items():
                if m == 'proximity':
                    remove.add(i)

    # Rule 2: skip proximity candidates where parent already has semantic name
    # Exception: root-level (artboard) parents are exempt — their children
    # still need grouping even though the artboard itself is named
    for i, c in enumerate(candidates):
        if c.get('parent_id') == root_id:
            continue  # exempt root-level candidates
        parent_name = c.get('parent_name', '')
        if parent_name and not UNNAMED_RE.match(parent_name):
            # Parent is already semantically named — lower priority
            # Only remove if it's a proximity candidate (less reliable)
            if c.get('method') == 'proximity':
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

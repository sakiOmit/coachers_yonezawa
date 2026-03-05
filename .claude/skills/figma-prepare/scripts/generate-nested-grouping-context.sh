#!/usr/bin/env bash
# Phase 2 Stage C: Generate Nested Grouping Context
#
# For each leaf section in sectioning-plan.yaml, generates an enriched children
# table and a fully-populated prompt for Claude (Haiku) nested grouping inference.
#
# This script does NOT call Claude. It produces context JSON that the SKILL.md
# workflow level uses to invoke Claude, mirroring the Stage B design pattern.
#
# Issue 194 Phase 3: Stage C parallel execution alongside Stage A.
#
# Usage:
#   bash generate-nested-grouping-context.sh <metadata.json> <sectioning-plan.yaml> \
#     [--output nested-context.json]
#
# Exit: 0=success, 1=error

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo '{"error": "Usage: generate-nested-grouping-context.sh <metadata.json> <sectioning-plan.yaml> [--output nested-context.json]"}' >&2
  exit 1
fi

METADATA_FILE="$1"
PLAN_FILE="$2"
OUTPUT_FILE=""

if [[ ! -f "$METADATA_FILE" ]]; then
  echo "{\"error\": \"Metadata file not found: $METADATA_FILE\"}" >&2
  exit 1
fi

if [[ ! -f "$PLAN_FILE" ]]; then
  echo "{\"error\": \"Sectioning plan file not found: $PLAN_FILE\"}" >&2
  exit 1
fi

# Parse optional flags
shift 2
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      OUTPUT_FILE="${2:-}"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$(dirname "$SCRIPT_DIR")"
TEMPLATE_FILE="$SKILLS_DIR/references/nested-grouping-prompt-template.md"

if [[ ! -f "$TEMPLATE_FILE" ]]; then
  echo "{\"error\": \"Prompt template not found: $TEMPLATE_FILE\"}" >&2
  exit 1
fi

python3 -c "
import json, sys, os, re
sys.setrecursionlimit(3000)
sys.path.insert(0, os.path.join(sys.argv[1], 'lib'))
from figma_utils import (resolve_absolute_coords, get_bbox, get_root_node,
    find_node_by_id, generate_enriched_table, GRANDCHILD_THRESHOLD)

METADATA_FILE = sys.argv[2]
PLAN_FILE = sys.argv[3]
OUTPUT_FILE = sys.argv[4]
TEMPLATE_FILE = sys.argv[5]

# --- Load prompt template ---
# Extract the prompt body between the first pair of triple backticks in the
# '## Prompt Template' section. The template uses fenced code blocks.
with open(TEMPLATE_FILE, 'r') as f:
    template_content = f.read()

# Find the prompt body: first fenced code block after '## Prompt Template'
# Use chr(96) to avoid backtick issues in bash embedding
fence = chr(96) * 3
pattern = r'## Prompt Template.*?\n' + re.escape(fence) + r'\n(.*?)\n' + re.escape(fence)
prompt_section_match = re.search(pattern, template_content, re.DOTALL)
if not prompt_section_match:
    print(json.dumps({'error': 'Could not extract prompt template body'}), file=sys.stderr)
    sys.exit(1)
prompt_template = prompt_section_match.group(1)

# --- Load metadata ---
with open(METADATA_FILE, 'r') as f:
    data = json.load(f)

root = get_root_node(data)
resolve_absolute_coords(root)
page_bbox = get_bbox(root)
page_width = page_bbox['w']
page_height = page_bbox['h']

# --- Load sectioning plan (YAML) ---
# Minimal YAML parser for the specific structure we expect.
# sectioning-plan.yaml is simple enough to parse without PyYAML.
import importlib
yaml_available = False
try:
    yaml = importlib.import_module('yaml')
    yaml_available = True
except ImportError:
    pass

with open(PLAN_FILE, 'r') as f:
    plan_text = f.read()

if yaml_available:
    plan = yaml.safe_load(plan_text)
else:
    # Fallback: try JSON (sectioning-plan may also be saved as JSON)
    try:
        plan = json.loads(plan_text)
    except json.JSONDecodeError:
        print(json.dumps({'error': 'Cannot parse sectioning plan. Install PyYAML or use JSON format.'}), file=sys.stderr)
        sys.exit(1)

# --- Collect leaf sections (no subsections) ---
def collect_leaf_sections(sections, depth=0):
    \"\"\"Recursively collect leaf sections (those without subsections).\"\"\"
    leaves = []
    for section in sections:
        if 'subsections' in section and section['subsections']:
            leaves.extend(collect_leaf_sections(section['subsections'], depth + 1))
        else:
            leaves.append(section)
    return leaves

sections_list = plan.get('sections', [])
leaf_sections = collect_leaf_sections(sections_list)

# --- Determine children for each section ---
# Each leaf section has node_ids which are IDs of elements within the section.
# Strategy:
#   - If node_ids count <= 5 AND each has children -> use grandchildren (children of each node)
#   - Otherwise -> use the node_ids themselves as the children table entries

def get_section_children(section):
    \"\"\"Get the children to include in the enriched table for a section.

    Returns (children_list, section_node) where section_node is used for
    bbox when the section is a single wrapper node.
    \"\"\"
    node_ids = section.get('node_ids', [])
    if not node_ids:
        return [], None

    # Resolve all nodes
    nodes = []
    for nid in node_ids:
        node = find_node_by_id(root, nid)
        if node:
            nodes.append(node)

    if not nodes:
        return [], None

    # Determine strategy: if few nodes and each has children, use grandchildren
    if len(nodes) <= GRANDCHILD_THRESHOLD:
        has_children_count = sum(1 for n in nodes if n.get('children'))
        if has_children_count == len(nodes) and len(nodes) > 0:
            # Use grandchildren (children of each node)
            grandchildren = []
            for n in nodes:
                grandchildren.extend(n.get('children', []))
            if grandchildren:
                return grandchildren, None

    # Default: use the nodes themselves
    return nodes, None

# --- Build section contexts ---
section_contexts = []

for section in leaf_sections:
    section_name = section.get('name', 'unknown')
    node_ids = section.get('node_ids', [])

    if not node_ids:
        continue

    children, _ = get_section_children(section)
    if not children:
        continue

    # Sort by Y ascending
    children_sorted = sorted(children, key=lambda c: get_bbox(c).get('y', 0))

    # Compute section bbox from children
    if len(node_ids) == 1:
        # Single wrapper node: use its bbox
        wrapper = find_node_by_id(root, node_ids[0])
        if wrapper:
            sb = get_bbox(wrapper)
            section_width = sb['w']
            section_height = sb['h']
        else:
            section_width = page_width
            section_height = 0
    else:
        # Multiple nodes: compute bounding box
        min_x = min(get_bbox(c)['x'] for c in children_sorted)
        min_y = min(get_bbox(c)['y'] for c in children_sorted)
        max_x = max(get_bbox(c)['x'] + get_bbox(c)['w'] for c in children_sorted)
        max_y = max(get_bbox(c)['y'] + get_bbox(c)['h'] for c in children_sorted)
        section_width = max_x - min_x
        section_height = max_y - min_y

    # Determine section_id: first node_id or single wrapper
    section_id = node_ids[0] if len(node_ids) == 1 else node_ids[0]

    # Generate enriched table
    enriched_table = generate_enriched_table(
        children_sorted,
        page_width=section_width if section_width > 0 else page_width,
        page_height=section_height if section_height > 0 else page_height,
    )

    total_children = len(children_sorted)

    # Build prompt by substituting variables
    prompt = prompt_template
    prompt = prompt.replace('{section_name}', str(section_name))
    prompt = prompt.replace('{section_id}', str(section_id))
    prompt = prompt.replace('{section_width}', str(int(section_width)))
    prompt = prompt.replace('{section_height}', str(int(section_height)))
    prompt = prompt.replace('{total_children}', str(total_children))
    prompt = prompt.replace('{enriched_children_table}', enriched_table)

    section_contexts.append({
        'section_name': section_name,
        'section_id': section_id,
        'section_width': int(section_width),
        'section_height': int(section_height),
        'total_children': total_children,
        'enriched_children_table': enriched_table,
        'prompt': prompt,
    })

# --- Output ---
result = {
    'sections': section_contexts,
    'total_sections': len(section_contexts),
    'model': 'haiku',
}

if OUTPUT_FILE:
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(json.dumps({
        'status': 'ok',
        'output': OUTPUT_FILE,
        'total_sections': len(section_contexts),
        'model': 'haiku',
    }, indent=2))
else:
    print(json.dumps(result, indent=2, ensure_ascii=False))

" "$SKILLS_DIR" "$METADATA_FILE" "$PLAN_FILE" "$OUTPUT_FILE" "$TEMPLATE_FILE"

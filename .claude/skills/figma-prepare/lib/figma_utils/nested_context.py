"""Nested grouping context generation for Stage C.

Extracts Python logic from generate-nested-grouping-context.sh.
Handles both plan mode (sectioning-plan.yaml) and groups mode
(nested-grouping-result.json with --groups/--depth).

Used by generate-nested-grouping-context.sh as a thin shell wrapper.
"""

import json
import re
import sys

from .constants import GRANDCHILD_THRESHOLD, MAX_STAGE_C_DEPTH
from .geometry import filter_visible_children, get_bbox, resolve_absolute_coords, sort_by_y
from .metadata import find_node_by_id, get_root_node, load_metadata
from .enrichment import generate_enriched_table

__all__ = [
    'generate_nested_context',
    'load_prompt_template',
    'collect_leaf_sections',
]


# ---------------------------------------------------------------------------
# Prompt template loading
# ---------------------------------------------------------------------------

def load_prompt_template(template_file):
    """Load and extract the prompt body from nested-grouping-prompt-template.md.

    Extracts the content between the first pair of triple backticks in the
    '## Prompt Template' section.

    Returns the prompt template string.
    Raises SystemExit on failure.
    """
    with open(template_file, 'r') as f:
        template_content = f.read()

    fence = chr(96) * 3
    pattern = r'## Prompt Template.*?\n' + re.escape(fence) + r'\n(.*?)\n' + re.escape(fence)
    match = re.search(pattern, template_content, re.DOTALL)
    if not match:
        print(json.dumps({'error': 'Could not extract prompt template body'}), file=sys.stderr)
        sys.exit(1)
    return match.group(1)


# ---------------------------------------------------------------------------
# YAML/JSON file loading helper
# ---------------------------------------------------------------------------

def _load_yaml_or_json(file_path, file_label="file"):
    """Load a file as YAML (if available) or JSON.

    Returns parsed data. Raises SystemExit on parse failure.
    """
    import importlib
    yaml_available = False
    try:
        yaml = importlib.import_module('yaml')
        yaml_available = True
    except ImportError:
        yaml = None

    with open(file_path, 'r') as f:
        text = f.read()

    try:
        if yaml_available:
            try:
                return yaml.safe_load(text)
            except Exception:
                return json.loads(text)
        else:
            return json.loads(text)
    except (json.JSONDecodeError, ValueError) as e:
        print(json.dumps({'error': f'Cannot parse {file_label}: {e}'}), file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Leaf section collection (plan mode)
# ---------------------------------------------------------------------------

def collect_leaf_sections(sections, depth=0):
    """Recursively collect leaf sections (those without subsections)."""
    leaves = []
    for section in sections:
        if 'subsections' in section and section['subsections']:
            leaves.extend(collect_leaf_sections(section['subsections'], depth + 1))
        else:
            leaves.append(section)
    return leaves


# ---------------------------------------------------------------------------
# Prompt building helper
# ---------------------------------------------------------------------------

def _build_prompt(prompt_template, section_name, section_id, section_width,
                  section_height, total_children, enriched_table):
    """Substitute variables into the prompt template."""
    prompt = prompt_template
    prompt = prompt.replace('{section_name}', str(section_name))
    prompt = prompt.replace('{section_id}', str(section_id))
    prompt = prompt.replace('{section_width}', str(int(section_width)))
    prompt = prompt.replace('{section_height}', str(int(section_height)))
    prompt = prompt.replace('{total_children}', str(total_children))
    prompt = prompt.replace('{enriched_children_table}', enriched_table)
    return prompt


# ---------------------------------------------------------------------------
# Groups mode (Issue 225)
# ---------------------------------------------------------------------------

def _load_and_validate_groups(groups_file, depth):
    """Load groups file and validate structure.

    Returns (groups_list, depth_skip_result) where depth_skip_result is
    a result dict if depth exceeds MAX_STAGE_C_DEPTH, or None otherwise.
    """
    if depth >= MAX_STAGE_C_DEPTH:
        return [], {
            'sections': [],
            'total_sections': 0,
            'depth': depth,
            'model': 'haiku',
            'skipped_reason': f'depth {depth} >= MAX_STAGE_C_DEPTH ({MAX_STAGE_C_DEPTH})',
        }

    groups_data = _load_yaml_or_json(groups_file, "groups file")

    if not isinstance(groups_data, dict):
        print(json.dumps({
            'error': f'groups file must contain a JSON object, got {type(groups_data).__name__}'
        }), file=sys.stderr)
        sys.exit(1)

    groups_list = groups_data.get('groups', [])
    if not groups_list and 'sections' in groups_data:
        for sec in groups_data['sections']:
            for g in sec.get('groups', []):
                groups_list.append(g)

    return groups_list, None


def _resolve_group_siblings(root, group, skipped_groups):
    """Resolve node_ids to sibling nodes for a single group.

    Returns list of resolved sibling nodes (sorted by Y), or empty list
    if the group should be skipped. Appends skip reasons to skipped_groups.
    """
    group_pattern = group.get('pattern', '')
    group_name = group.get('name', 'unknown')
    group_node_ids = group.get('node_ids', [])

    # Skip groups with pattern 'single' AND fewer than 3 node_ids (Issue 255)
    if group_pattern == 'single' and len(group_node_ids) < 3:
        skipped_groups.append({'name': group_name, 'reason': 'pattern=single, children<3'})
        return []

    if not group_node_ids:
        skipped_groups.append({'name': group_name, 'reason': 'no node_ids'})
        return []

    # Issue 257: Treat group's node_ids as siblings to sub-group
    sibling_nodes = []
    for nid in group_node_ids:
        if not isinstance(nid, str):
            skipped_groups.append({
                'name': group_name,
                'reason': f'node_id {repr(nid)} is not a string'
            })
            continue
        node = find_node_by_id(root, nid)
        if not node:
            skipped_groups.append({
                'name': group_name,
                'node_id': nid,
                'reason': 'node not found'
            })
            continue
        sibling_nodes.append(node)

    if len(sibling_nodes) < 2:
        skipped_groups.append({
            'name': group_name,
            'reason': f'too few sibling nodes ({len(sibling_nodes)})'
        })
        return []

    return sort_by_y(sibling_nodes)


def _build_group_context(sibling_nodes_sorted, group, page_width, page_height,
                         prompt_template, depth):
    """Build a section context entry for a single group.

    Returns the section context dict.
    """
    group_name = group.get('name', 'unknown')
    group_node_ids = group.get('node_ids', [])

    bboxes = [get_bbox(n) for n in sibling_nodes_sorted]
    min_x = min(b['x'] for b in bboxes)
    min_y = min(b['y'] for b in bboxes)
    max_right = max(b['x'] + b['w'] for b in bboxes)
    max_bottom = max(b['y'] + b['h'] for b in bboxes)
    section_width = max_right - min_x
    section_height = max_bottom - min_y

    section_id = group_node_ids[0]

    enriched_table = generate_enriched_table(
        sibling_nodes_sorted,
        page_width=section_width if section_width > 0 else page_width,
        page_height=section_height if section_height > 0 else page_height,
        root_x=min_x,
        root_y=min_y,
    )

    total_children = len(sibling_nodes_sorted)

    prompt = _build_prompt(
        prompt_template, group_name, section_id,
        section_width, section_height, total_children, enriched_table,
    )

    return {
        'section_name': group_name,
        'section_id': section_id,
        'parent_group': group_name,
        'depth': depth,
        'section_width': int(section_width),
        'section_height': int(section_height),
        'total_children': total_children,
        'enriched_children_table': enriched_table,
        'prompt': prompt,
    }


def _process_groups_mode(root, page_width, page_height, groups_file,
                         prompt_template, depth):
    """Process --groups mode: generate context from nested-grouping-result groups.

    Returns the result dict.
    """
    groups_list, skip_result = _load_and_validate_groups(groups_file, depth)
    if skip_result is not None:
        return skip_result

    section_contexts = []
    skipped_groups = []

    for group in groups_list:
        sibling_nodes_sorted = _resolve_group_siblings(root, group, skipped_groups)
        if not sibling_nodes_sorted:
            continue

        context = _build_group_context(
            sibling_nodes_sorted, group, page_width, page_height,
            prompt_template, depth,
        )
        section_contexts.append(context)

    return {
        'sections': section_contexts,
        'total_sections': len(section_contexts),
        'depth': depth,
        'model': 'haiku',
        'skipped_groups': skipped_groups,
        'skipped_count': len(skipped_groups),
    }


# ---------------------------------------------------------------------------
# Plan mode (original behavior)
# ---------------------------------------------------------------------------

def _get_section_children(root, section):
    """Get the children to include in the enriched table for a section.

    Returns (children_list, section_node).
    """
    node_ids = section.get('node_ids', [])
    if not node_ids:
        return [], None

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
            grandchildren = []
            for n in nodes:
                grandchildren.extend(
                    filter_visible_children(n)
                )
            if grandchildren:
                return grandchildren, None

    return nodes, None


def _compute_section_bbox(root, node_ids, children_sorted, page_width, page_bbox):
    """Compute bounding box for a plan section.

    Returns (section_width, section_height, section_root_x, section_root_y).
    """
    if len(node_ids) == 1:
        wrapper = find_node_by_id(root, node_ids[0])
        if wrapper:
            sb = get_bbox(wrapper)
            return sb['w'], sb['h'], sb['x'], sb['y']
        return page_width, 0, page_bbox['x'], page_bbox.get('y', 0)

    min_x = min(get_bbox(c)['x'] for c in children_sorted)
    min_y = min(get_bbox(c)['y'] for c in children_sorted)
    max_x = max(get_bbox(c)['x'] + get_bbox(c)['w'] for c in children_sorted)
    max_y = max(get_bbox(c)['y'] + get_bbox(c)['h'] for c in children_sorted)
    return max_x - min_x, max_y - min_y, min_x, min_y


def _process_plan_mode(root, page_width, page_height, page_bbox,
                       plan_file, prompt_template):
    """Process plan mode: generate context from sectioning-plan.yaml.

    Returns the result dict.
    """
    plan = _load_yaml_or_json(plan_file, "sectioning plan")

    sections_list = plan.get('sections', [])
    leaf_sections = collect_leaf_sections(sections_list)

    section_contexts = []

    for section in leaf_sections:
        section_name = section.get('name', 'unknown')
        node_ids = section.get('node_ids', [])

        if not node_ids:
            continue

        children, _ = _get_section_children(root, section)
        if not children:
            continue

        children_sorted = sorted(
            children, key=lambda c: get_bbox(c).get('y', 0)
        )

        section_width, section_height, section_root_x, section_root_y = \
            _compute_section_bbox(root, node_ids, children_sorted, page_width, page_bbox)

        section_id = node_ids[0]

        enriched_table = generate_enriched_table(
            children_sorted,
            page_width=section_width if section_width > 0 else page_width,
            page_height=section_height if section_height > 0 else page_height,
            root_x=section_root_x,
            root_y=section_root_y,
        )

        total_children = len(children_sorted)

        prompt = _build_prompt(
            prompt_template, section_name, section_id,
            section_width, section_height, total_children, enriched_table,
        )

        section_contexts.append({
            'section_name': section_name,
            'section_id': section_id,
            'section_width': int(section_width),
            'section_height': int(section_height),
            'total_children': total_children,
            'enriched_children_table': enriched_table,
            'prompt': prompt,
        })

    return {
        'sections': section_contexts,
        'total_sections': len(section_contexts),
        'model': 'haiku',
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_nested_context(metadata_file, template_file,
                            plan_file='', groups_file='',
                            output_file='', depth=0):
    """Generate nested grouping context for Stage C.

    Args:
        metadata_file: Path to Figma metadata JSON file.
        template_file: Path to nested-grouping-prompt-template.md.
        plan_file: Path to sectioning-plan.yaml (plan mode).
        groups_file: Path to nested-grouping-result.json (groups mode).
        output_file: Optional output file path for result JSON.
        depth: Recursion depth (groups mode only).

    Prints JSON result to stdout.
    """
    sys.setrecursionlimit(3000)

    prompt_template = load_prompt_template(template_file)

    # Load metadata
    data = load_metadata(metadata_file)
    root = get_root_node(data)
    resolve_absolute_coords(root)
    page_bbox = get_bbox(root)
    page_width = page_bbox['w']
    page_height = page_bbox['h']

    use_groups_mode = bool(groups_file)

    if use_groups_mode:
        result = _process_groups_mode(
            root, page_width, page_height,
            groups_file, prompt_template, depth,
        )
    else:
        result = _process_plan_mode(
            root, page_width, page_height, page_bbox,
            plan_file, prompt_template,
        )

    # Output
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        summary = {
            'status': 'ok',
            'output': output_file,
            'total_sections': result['total_sections'],
            'model': 'haiku',
        }
        if 'depth' in result:
            summary['depth'] = result['depth']
        if 'skipped_count' in result:
            summary['skipped_count'] = result['skipped_count']
        if 'skipped_reason' in result:
            summary['skipped_reason'] = result['skipped_reason']
        print(json.dumps(summary, indent=2))
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))

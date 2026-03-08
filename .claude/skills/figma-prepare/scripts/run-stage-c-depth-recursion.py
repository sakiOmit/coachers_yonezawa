#!/usr/bin/env python3
"""
Stage C Depth Recursion - Heuristic sub-grouping within nested-grouping-plan.yaml.

Recursively sub-groups within each group's sibling nodes using enriched table
metadata (Col column, spatial proximity, pattern recognition). No LLM calls
needed — fully deterministic.

Usage:
  python3 run-stage-c-depth-recursion.py \
    --metadata .claude/cache/figma/prepare-metadata-{nodeId}.json \
    --plan .claude/cache/figma/nested-grouping-plan.yaml \
    [--max-depth 10] [--dry-run]

Output:
  Updates --plan in-place with sub_groups added at each depth level.
  Prints summary to stderr.

Exit codes:
  0 = success (sub_groups added)
  1 = error
  2 = no changes (already converged or no recursion targets)
"""

import sys
import os
import argparse

# Add lib to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(SKILLS_DIR, 'lib'))

from figma_utils import (
    load_metadata, get_root_node, resolve_absolute_coords,
    get_bbox, find_node_by_id,
    parse_plan_yaml, write_plan_yaml,
    heuristic_sub_group, collect_recursion_targets,
)


def run_depth_recursion(metadata_file, plan_file, max_depth=10, dry_run=False):
    """Main recursion loop: sub-group until convergence."""
    # Load metadata
    data = load_metadata(metadata_file)
    root = get_root_node(data)
    resolve_absolute_coords(root)
    page_bbox = get_bbox(root)
    page_width = page_bbox['w']
    page_height = page_bbox['h']

    # Load plan
    plan = parse_plan_yaml(plan_file)
    if not plan or 'sections' not in plan:
        print('ERROR: Invalid plan file', file=sys.stderr)
        return 1

    total_sub_groups_added = 0

    for depth in range(1, max_depth + 1):
        depth_added = 0

        # Collect all groups that need recursion (across all sections, all depths)
        targets = collect_recursion_targets(plan)

        if not targets:
            print(f'  Depth {depth}: no recursion targets → converged', file=sys.stderr)
            break

        print(f'  Depth {depth}: {len(targets)} recursion target(s)', file=sys.stderr)

        for target_group, section_name in targets:
            node_ids = target_group.get('node_ids', [])

            # Resolve sibling nodes
            sibling_nodes = []
            for nid in node_ids:
                node = find_node_by_id(root, nid)
                if node:
                    sibling_nodes.append(node)

            if len(sibling_nodes) < 3:
                continue

            # Apply heuristic sub-grouping
            sub_groups = heuristic_sub_group(
                target_group, sibling_nodes, root, page_width, page_height
            )

            if sub_groups:
                target_group['sub_groups'] = sub_groups
                depth_added += len(sub_groups)
                print(
                    f'    {target_group["name"]}: {len(sub_groups)} sub-group(s) '
                    f'({", ".join(sg["name"] for sg in sub_groups)})',
                    file=sys.stderr,
                )

        total_sub_groups_added += depth_added

        if depth_added == 0:
            print(f'  Depth {depth}: no sub-groups produced → converged', file=sys.stderr)
            break

    if total_sub_groups_added == 0:
        print('No sub-groups to add.', file=sys.stderr)
        return 2

    if not dry_run:
        write_plan_yaml(plan, plan_file)
        print(
            f'Updated {plan_file}: {total_sub_groups_added} sub-group(s) added.',
            file=sys.stderr,
        )
    else:
        print(
            f'[dry-run] Would add {total_sub_groups_added} sub-group(s).',
            file=sys.stderr,
        )
        # Print to stdout for inspection
        write_plan_yaml(plan, '/dev/stdout')

    return 0


def main():
    parser = argparse.ArgumentParser(description='Stage C depth recursion')
    parser.add_argument('--metadata', required=True, help='Metadata JSON file')
    parser.add_argument('--plan', required=True, help='Nested grouping plan YAML')
    parser.add_argument('--max-depth', type=int, default=10, help='Safety upper bound')
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing')
    args = parser.parse_args()

    if not os.path.isfile(args.metadata):
        print(f'ERROR: Metadata file not found: {args.metadata}', file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(args.plan):
        print(f'ERROR: Plan file not found: {args.plan}', file=sys.stderr)
        sys.exit(1)

    sys.exit(run_depth_recursion(args.metadata, args.plan, args.max_depth, args.dry_run))


if __name__ == '__main__':
    main()

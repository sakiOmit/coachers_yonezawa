"""Stage C depth recursion utilities.

YAML I/O for nested-grouping-plan, enriched table parsing,
and heuristic sub-grouping strategies (heading, column, spatial, Y-band).

Used by run-stage-c-depth-recursion.py and potentially other Stage C tooling.

Split into submodules:
  stage_c_yaml       - parse_plan_yaml, write_plan_yaml, _write_group_yaml, parse_enriched_table
  stage_c_strategies  - heuristic_sub_group, _try_heading_split, _try_column_split,
                        _try_spatial_split, _try_yband_split
"""

# Re-export from submodules for backward compatibility
from .stage_c_yaml import (  # noqa: F401
    parse_plan_yaml,
    write_plan_yaml,
    _write_group_yaml,
    parse_enriched_table,
)
from .stage_c_strategies import (  # noqa: F401
    heuristic_sub_group,
    _try_heading_split,
    _try_column_split,
    _try_spatial_split,
    _try_yband_split,
)

__all__ = [
    'parse_plan_yaml',
    'write_plan_yaml',
    'parse_enriched_table',
    'heuristic_sub_group',
    'collect_recursion_targets',
]


# ---------------------------------------------------------------------------
# Recursion target collection
# ---------------------------------------------------------------------------

def collect_recursion_targets(plan):
    """Collect all groups needing recursion (no existing sub_groups, 3+ node_ids,
    pattern != single or node_ids >= 3)."""
    targets = []
    for section in plan.get('sections', []):
        _collect_from_groups(section.get('groups', []), section['section_name'], targets)
    return targets


def _collect_from_groups(groups, section_name, targets):
    """Recursively collect groups that need sub-grouping."""
    for g in groups:
        # Skip if already has sub_groups
        if g.get('sub_groups'):
            # Recurse into existing sub_groups to find deeper targets
            _collect_from_groups(g['sub_groups'], section_name, targets)
            continue

        node_ids = g.get('node_ids', [])
        pattern = g.get('pattern', 'single')

        # Recursion criteria: need at least 3 node_ids to meaningfully split
        if len(node_ids) >= 3:
            targets.append((g, section_name))

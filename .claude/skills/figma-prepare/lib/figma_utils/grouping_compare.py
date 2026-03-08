"""Compare Stage A (rule-based) and Stage C (Haiku inference) grouping results.

Extracted from compare-grouping.sh (Issue refactor).
Provides YAML parsing and report generation for grouping comparison.
"""

import json

from .comparison import compare_grouping_results, _stage_a_pattern_key  # noqa: F401

__all__ = [
    "format_report",
    "parse_stage_a_yaml",
    "parse_stage_c_yaml",
    "run_comparison",
]


def parse_stage_a_yaml(filepath):
    """Parse the YAML output from detect-grouping-candidates.sh."""
    candidates = []
    current = None
    with open(filepath, 'r') as f:
        for line in f:
            line = line.rstrip()
            if line.startswith('#') or not line.strip():
                continue
            if line.strip().startswith('- index:'):
                if current is not None:
                    candidates.append(current)
                current = {}
            elif current is not None and ':' in line:
                stripped = line.strip()
                key, _, val = stripped.partition(':')
                key = key.strip()
                val = val.strip()
                # Remove YAML quotes
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                if key == 'node_ids':
                    try:
                        current[key] = json.loads(val)
                    except json.JSONDecodeError:
                        current[key] = []
                elif key == 'bg_node_ids':
                    try:
                        current[key] = json.loads(val)
                    except json.JSONDecodeError:
                        current[key] = []
                elif key == 'count':
                    try:
                        current[key] = int(val)
                    except ValueError:
                        current[key] = 0
                elif key in ('fuzzy_match',):
                    current[key] = val.lower() == 'true'
                elif key in ('tuple_size', 'repetitions', 'row_count'):
                    try:
                        current[key] = int(val)
                    except ValueError:
                        current[key] = 0
                else:
                    current[key] = val
    if current is not None:
        candidates.append(current)
    return candidates


def parse_stage_c_yaml(filepath):
    """Parse the YAML output from Haiku nested grouping."""
    groups = []
    current = None
    with open(filepath, 'r') as f:
        for line in f:
            line = line.rstrip()
            if line.startswith('#') or not line.strip():
                continue
            stripped = line.strip()
            if stripped.startswith('- name:'):
                if current is not None:
                    groups.append(current)
                current = {'name': stripped.split(':', 1)[1].strip().strip('"')}
            elif current is not None and ':' in stripped:
                key, _, val = stripped.partition(':')
                key = key.strip()
                val = val.strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                if key == 'node_ids':
                    try:
                        current[key] = json.loads(val)
                    except json.JSONDecodeError:
                        current[key] = []
                else:
                    current[key] = val
    if current is not None:
        groups.append(current)
    return groups


def run_comparison(stage_a_file, stage_c_file, section_filter=''):
    """Run full comparison and return (result, stage_a_candidates, stage_c_groups, report_text).

    Args:
        stage_a_file: Path to Stage A grouping-plan.yaml
        stage_c_file: Path to Stage C nested-grouping-result.yaml
        section_filter: Optional section name filter

    Returns:
        Tuple of (result_dict, stage_a_candidates, stage_c_groups, report_text)
    """
    stage_a_candidates = parse_stage_a_yaml(stage_a_file)
    stage_c_groups = parse_stage_c_yaml(stage_c_file)

    # Apply section filter if specified
    if section_filter:
        stage_a_candidates = [c for c in stage_a_candidates
                              if section_filter.lower() in c.get('parent', '').lower()
                              or section_filter.lower() in c.get('suggested_name', '').lower()]
        stage_c_groups = [g for g in stage_c_groups
                          if section_filter.lower() in g.get('name', '').lower()]

    # Run comparison
    result = compare_grouping_results(stage_a_candidates, stage_c_groups)

    # Build report
    report = format_report(result, stage_a_candidates, stage_c_groups)

    return result, stage_a_candidates, stage_c_groups, report


def format_report(result, stage_a_candidates, stage_c_groups):
    """Format comparison result as human-readable report text.

    Args:
        result: Output from compare_grouping_results()
        stage_a_candidates: Parsed Stage A candidates
        stage_c_groups: Parsed Stage C groups

    Returns:
        Report string
    """
    lines = []
    lines.append('=== Grouping Comparison Report ===')
    lines.append('')

    # Coverage
    all_a_nodes = set()
    for c in stage_a_candidates:
        all_a_nodes.update(c.get('node_ids', []))
    all_c_nodes = set()
    for g in stage_c_groups:
        all_c_nodes.update(g.get('node_ids', []))
    covered = len(all_a_nodes & all_c_nodes)
    lines.append(f'Coverage: {result["coverage"]*100:.0f}% ({covered}/{len(all_a_nodes)} nodes)')
    lines.append(f'Mean Jaccard: {result["mean_jaccard"]:.2f}')
    lines.append('')

    # Pattern Accuracy
    if result['pattern_accuracy']:
        lines.append('Pattern Accuracy:')
        for pat_key, counts in sorted(result['pattern_accuracy'].items()):
            m = counts['matched']
            t = counts['total']
            pct = f'{100*m//t}%' if t > 0 else 'N/A'
            status = ''
            if t > 0 and m < t:
                status = '  <-- Stage C missed some'
            lines.append(f'  {pat_key:20s} {m}/{t} ({pct}){status}')
        lines.append('')

    # Matched pairs detail
    if result['matched_pairs']:
        lines.append('Matched Pairs:')
        for pair in result['matched_pairs']:
            a_idx = pair['stage_a_idx']
            c_idx = pair['stage_c_idx']
            a_name = stage_a_candidates[a_idx].get('suggested_name', f'group-{a_idx}')
            c_name = stage_c_groups[c_idx].get('name', f'group-{c_idx}')
            j = pair['jaccard']
            lines.append(f'  [{a_name}] <-> [{c_name}]  Jaccard={j:.2f}')
        lines.append('')

    # Stage A only
    if result['stage_a_only']:
        lines.append('Stage A only (not matched by Stage C):')
        for idx in result['stage_a_only']:
            c = stage_a_candidates[idx]
            name = c.get('suggested_name', '?')
            method = c.get('method', '?')
            count = c.get('count', 0)
            lines.append(f'  [{name}] (method={method}, {count} nodes)')
        lines.append('')

    # Stage C only
    if result['stage_c_only']:
        lines.append('Stage C only (no Stage A counterpart):')
        for idx in result['stage_c_only']:
            g = stage_c_groups[idx]
            name = g.get('name', '?')
            pattern = g.get('pattern', '?')
            count = len(g.get('node_ids', []))
            lines.append(f'  [{name}] (pattern={pattern}, {count} nodes)')
        lines.append('')

    # Migration recommendation
    lines.append('=== Migration Recommendation ===')
    cov = result['coverage']
    mj = result['mean_jaccard']
    if cov >= 0.8 and mj >= 0.7:
        lines.append(f'RECOMMEND: Stage C is sufficient (coverage={cov*100:.0f}%, jaccard={mj:.2f}).')
        lines.append('  -> Stage A detectors can be removed for matched pattern types.')
    elif cov >= 0.6:
        lines.append(f'CAUTION: Stage C is partial (coverage={cov*100:.0f}%, jaccard={mj:.2f}).')
        lines.append('  -> Use Stage C as supplement. Maintain Stage A.')
    else:
        lines.append(f'INSUFFICIENT: Stage C coverage too low (coverage={cov*100:.0f}%, jaccard={mj:.2f}).')
        lines.append('  -> Maintain Stage A. Improve Stage C prompts.')

    # JSON output for programmatic use
    lines.append('')
    lines.append('--- JSON ---')
    lines.append(json.dumps(result, indent=2))

    return '\n'.join(lines)
